from __future__ import annotations

import asyncio
import logging

import httpx

from wizard_bot.config import get_settings
from wizard_bot.handlers.campaigns import render_campaign_view, render_campaigns, search_campaign
from wizard_bot.handlers.create_link import handle_wizard_input
from wizard_bot.handlers.menu import handle_callback
from wizard_bot.handlers.ops_tools import parse_import_payload, run_sb_call, summarize_import_result
from wizard_bot.handlers.start import show_main
from wizard_bot.http.socialbridge_client import SocialBridgeClient
from wizard_bot.http.telegram_client import TelegramClient
from wizard_bot.nav import routes
from wizard_bot.nav.stack import push_route
from wizard_bot.security.admin_guard import UNAUTHORIZED_TEXT, extract_user_id, is_admin
from wizard_bot.storage.locks import ChatLock
from wizard_bot.storage.redis import get_redis, import_last_file_key, unauthorized_notice_key
from wizard_bot.ui.clean_chat import ChatCleaner
from wizard_bot.ui.messenger import Messenger
from wizard_bot.ui.panel import PanelManager
from wizard_bot.ui.registry import register_message
from wizard_bot.wizard.state import load_session, save_session

logger = logging.getLogger(__name__)


async def _handle_document_message(chat_id: int, message: dict, panel, redis, telegram, sb_client) -> bool:
    session = await load_session(redis, chat_id)
    if session.get("awaiting_document") != "import_content_map":
        return False

    async with ChatLock(redis, chat_id, ttl_ms=12000) as lock:
        if not lock.acquired:
            return True

        session = await load_session(redis, chat_id)
        if session.get("awaiting_document") != "import_content_map":
            return True

        document = message.get("document") if isinstance(message.get("document"), dict) else None
        if not document:
            await panel.render(
                chat_id=chat_id,
                text="Restore / Import\n\nPlease send a JSON document file.",
                keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]},
            )
            return True

        file_id = str(document.get("file_id") or "")
        if not file_id:
            return True

        dedupe_key = import_last_file_key(chat_id)
        last_file_id = await redis.get(dedupe_key)
        if last_file_id == file_id:
            return True

        file_path, file_error = await run_sb_call(lambda: telegram.get_file(file_id), "Unable to read Telegram file")
        if file_error or not isinstance(file_path, str):
            await panel.render(chat_id=chat_id, text=f"Restore / Import\n\n⚠️ {file_error or 'Invalid file path'}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
            return True

        content, content_error = await run_sb_call(lambda: telegram.download_file(file_path), "Unable to download file")
        if content_error or not isinstance(content, (bytes, bytearray)):
            await panel.render(chat_id=chat_id, text=f"Restore / Import\n\n⚠️ {content_error or 'Invalid file bytes'}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
            return True

        try:
            items = parse_import_payload(bytes(content))
        except ValueError as exc:
            await panel.render(chat_id=chat_id, text=f"Restore / Import\n\n⚠️ {exc}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
            return True

        result, import_error = await run_sb_call(lambda: sb_client.import_content_map(items), "Import failed")
        if import_error:
            await panel.render(chat_id=chat_id, text=f"Restore / Import\n\n⚠️ {import_error}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
            return True

        await redis.set(dedupe_key, file_id, ex=60)
        session["awaiting_document"] = None
        await save_session(redis, chat_id, session)
        await panel.render(
            chat_id=chat_id,
            text=summarize_import_result(result if isinstance(result, dict) else {}),
            keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}, {"text": "Home", "callback_data": "act:clean"}]]},
        )
        return True


async def process_update(update: dict, *, settings, redis, telegram, panel, cleaner, messenger, sb_client) -> None:
    user_id = extract_user_id(update)

    msg = update.get("message")
    cb = update.get("callback_query")
    chat_id = None
    if isinstance(msg, dict):
        chat_id = msg.get("chat", {}).get("id")
    elif isinstance(cb, dict):
        chat_id = cb.get("message", {}).get("chat", {}).get("id")

    if not is_admin(user_id, set(settings.WIZARD_ADMIN_IDS)):
        if cb:
            await telegram.answer_callback_query(cb["id"], text="Not allowed")
            return
        if msg and chat_id is not None:
            key = unauthorized_notice_key(chat_id)
            if not await redis.get(key):
                await messenger.send_text(chat_id=chat_id, text=UNAUTHORIZED_TEXT, register=True)
                await redis.set(key, "1", ex=24 * 3600)
        return

    if msg:
        message = msg
        chat_id = message["chat"]["id"]
        message_id = message.get("message_id")
        text = message.get("text", "")
        if text.startswith("/start"):
            await show_main(panel, redis, chat_id)
            return

        # Register user's incoming message so Home button can delete it
        if message_id:
            await register_message(redis, chat_id, message_id)

        if await _handle_document_message(chat_id, message, panel, redis, telegram, sb_client):
            return

        # Handle campaign search input
        session = await load_session(redis, chat_id)
        if session.get("awaiting_input") == "campaign_search":
            session["awaiting_input"] = None
            campaign = await search_campaign(sb_client, text)
            if campaign:
                session["campaign_view"] = campaign
                await save_session(redis, chat_id, session)
                await push_route(redis, chat_id, routes.CAMPAIGN_VIEW, routes.CAMPAIGNS_LIST)
                await render_campaign_view(panel, redis, chat_id, settings)
            else:
                await save_session(redis, chat_id, session)
                await render_campaigns(
                    panel,
                    sb_client,
                    redis,
                    chat_id,
                    int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
                    offset=int(session.get("campaigns_offset") or 0),
                    error_msg=f"Not found: '{text}'",
                )
            return

        consumed = await handle_wizard_input(chat_id, text, panel, redis, telegram)
        if not consumed:
            await panel.render(chat_id=chat_id, text="Use /start to open Campaign Wizard.", keyboard={"inline_keyboard": []})
        return

    if cb:
        callback_query = cb
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query.get("data", "")
        async with ChatLock(redis, chat_id) as lock:
            if not lock.acquired:
                await telegram.answer_callback_query(callback_query["id"], text="Please wait…")
                return
            if data == "act:clean":
                await cleaner.clean(chat_id)
                await panel.render(chat_id=chat_id, text="✅ Cleaned", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
            else:
                await handle_callback(data, chat_id, panel, redis, telegram, messenger, sb_client, settings)
        await telegram.answer_callback_query(callback_query["id"])


async def runner() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    redis = get_redis()
    telegram = TelegramClient(settings.WIZARD_BOT_TOKEN)
    sb_client = SocialBridgeClient(settings.SOCIALBRIDGE_ADMIN_BASE_URL, settings.SOCIALBRIDGE_ADMIN_TOKEN)
    panel = PanelManager(redis, telegram)
    cleaner = ChatCleaner(redis, telegram)
    messenger = Messenger(redis, telegram)

    offset = None
    _retry_delay = 1.0
    logger.info("wizard bot started")
    try:
        while True:
            try:
                updates = await telegram.get_updates(offset=offset, timeout=settings.WIZARD_POLL_TIMEOUT_SECONDS)
                _retry_delay = 1.0  # reset on success
            except (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                logger.warning("Telegram poll error (%s), retrying in %.0fs", exc, _retry_delay)
                await asyncio.sleep(_retry_delay)
                _retry_delay = min(_retry_delay * 2, 30.0)
                continue
            except httpx.TimeoutException:
                # long-poll timeout is normal — just retry immediately
                continue
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    await process_update(
                        update,
                        settings=settings,
                        redis=redis,
                        telegram=telegram,
                        panel=panel,
                        cleaner=cleaner,
                        messenger=messenger,
                        sb_client=sb_client,
                    )
                except Exception:
                    logger.exception("failed processing update")
    finally:
        await telegram.close()
        await sb_client.close()
        await redis.aclose()


def run() -> None:
    asyncio.run(runner())

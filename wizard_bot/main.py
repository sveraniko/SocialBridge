from __future__ import annotations

import asyncio
import logging

from wizard_bot.config import get_settings
from wizard_bot.handlers.create_link import handle_wizard_input
from wizard_bot.handlers.menu import handle_callback
from wizard_bot.handlers.start import show_main
from wizard_bot.http.socialbridge_client import SocialBridgeClient
from wizard_bot.http.telegram_client import TelegramClient
from wizard_bot.security.admin_guard import UNAUTHORIZED_TEXT, extract_user_id, is_admin
from wizard_bot.storage.locks import ChatLock
from wizard_bot.storage.redis import get_redis, unauthorized_notice_key
from wizard_bot.ui.clean_chat import ChatCleaner
from wizard_bot.ui.panel import PanelManager
from wizard_bot.ui.registry import register_message

logger = logging.getLogger(__name__)


async def process_update(update: dict, *, settings, redis, telegram, panel, cleaner, sb_client) -> None:
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
                sent = await telegram.send_message(chat_id=chat_id, text=UNAUTHORIZED_TEXT)
                if sent.get("message_id"):
                    await register_message(redis, chat_id, int(sent["message_id"]))
                await redis.set(key, "1", ex=24 * 3600)
        return

    if msg:
        message = msg
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        if text.startswith("/start"):
            await show_main(panel, redis, chat_id)
        else:
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
                await show_main(panel, redis, chat_id)
            else:
                await handle_callback(data, chat_id, panel, redis, sb_client, settings)
        await telegram.answer_callback_query(callback_query["id"])


async def runner() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    redis = get_redis()
    telegram = TelegramClient(settings.WIZARD_BOT_TOKEN)
    sb_client = SocialBridgeClient(settings.SOCIALBRIDGE_ADMIN_BASE_URL, settings.SOCIALBRIDGE_ADMIN_TOKEN)
    panel = PanelManager(redis, telegram)
    cleaner = ChatCleaner(redis, telegram)

    offset = None
    logger.info("wizard bot started")
    try:
        while True:
            updates = await telegram.get_updates(offset=offset, timeout=settings.WIZARD_POLL_TIMEOUT_SECONDS)
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

from __future__ import annotations

import json
from datetime import UTC, datetime

from wizard_bot.handlers.campaigns import render_campaign_view, render_campaigns, search_campaign, select_campaign
from wizard_bot.handlers.create_link import go_back, handle_wizard_callback, start_create
from wizard_bot.handlers.ops_tools import build_status_text, count_recent_dynamic, run_sb_call
from wizard_bot.handlers.start import show_main
from wizard_bot.nav import routes
from wizard_bot.nav.stack import pop_route, push_route
from wizard_bot.ui.keyboards import search_prompt_keyboard
from wizard_bot.wizard.state import load_session, save_session


async def _render_status(panel, chat_id: int, sb_client, settings) -> None:
    _, health_error = await run_sb_call(lambda: sb_client.health(), "health check failed")
    _, ready_error = await run_sb_call(lambda: sb_client.ready(), "ready check failed")
    campaigns_payload, _ = await run_sb_call(
        lambda: sb_client.list_content_map(limit=settings.WIZARD_CAMPAIGNS_PAGE_LIMIT, offset=0, is_active=None),
        "campaign list failed",
    )
    export_items, _ = await run_sb_call(
        lambda: sb_client.export_content_map(channel="generic", is_active=True),
        "export failed",
    )

    total_campaigns = 0
    if isinstance(campaigns_payload, dict):
        total_campaigns = int(campaigns_payload.get("total", 0))

    dynamic_count = count_recent_dynamic(export_items if isinstance(export_items, list) else [])
    dynamic_limit = getattr(settings, "DYNAMIC_MAPPING_MAX_PER_DAY", None) or "limit configured on server"
    text = build_status_text(
        health_ok=health_error is None,
        ready_ok=ready_error is None,
        total_campaigns=total_campaigns,
        dynamic_24h_count=dynamic_count,
        dynamic_limit=str(dynamic_limit),
    )
    await panel.render(chat_id=chat_id, text=text, keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}, {"text": "Home", "callback_data": "act:clean"}]]})


async def _send_backup(chat_id: int, panel, messenger, sb_client) -> None:
    items, error = await run_sb_call(lambda: sb_client.export_content_map(), "Failed to export content map")
    if error:
        await panel.render(chat_id=chat_id, text=f"Backup / Export\n\n⚠️ {error}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}]]})
        return
    payload = items if isinstance(items, list) else []
    filename = f"content_map_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M')}.json"
    await messenger.send_document(
        chat_id=chat_id,
        filename=filename,
        bytes_or_file=(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")),
        caption="SocialBridge content_map backup",
        register=True,
    )
    await panel.render(chat_id=chat_id, text=f"Backup sent as {filename}", keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}, {"text": "Home", "callback_data": "act:clean"}]]})


async def handle_callback(data: str, chat_id: int, panel, redis, telegram, messenger, sb_client, settings) -> None:
    if data == "nav:CREATE_LINK":
        await push_route(redis, chat_id, routes.CREATE_LINK, routes.MAIN)
        await start_create(panel, redis, chat_id)
        return

    if await handle_wizard_callback(data, chat_id, panel, redis, sb_client, settings):
        return

    if data == f"nav:{routes.CAMPAIGNS_LIST}":
        await push_route(redis, chat_id, routes.CAMPAIGNS_LIST, routes.MAIN)
        await render_campaigns(panel, sb_client, redis, chat_id, settings.WIZARD_CAMPAIGNS_PAGE_LIMIT, offset=0)
        return

    if data.startswith("camp:page:"):
        offset = int(data.split(":")[-1])
        await render_campaigns(panel, sb_client, redis, chat_id, settings.WIZARD_CAMPAIGNS_PAGE_LIMIT, offset=max(0, offset))
        return

    if data == "camp:search":
        session = await load_session(redis, chat_id)
        session["awaiting_input"] = "campaign_search"
        await save_session(redis, chat_id, session)
        await panel.render(
            chat_id=chat_id,
            text="🔍 Search\n\nEnter slug or product code:",
            keyboard=search_prompt_keyboard(),
        )
        return

    if data == "camp:search:cancel":
        session = await load_session(redis, chat_id)
        session.pop("awaiting_input", None)
        await save_session(redis, chat_id, session)
        await render_campaigns(
            panel,
            sb_client,
            redis,
            chat_id,
            int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
            offset=int(session.get("campaigns_offset") or 0),
        )
        return

    if data == "camp:back_to_list":
        session = await load_session(redis, chat_id)
        session.pop("campaign_view", None)
        session.pop("delete_confirm", None)
        await save_session(redis, chat_id, session)
        await render_campaigns(
            panel,
            sb_client,
            redis,
            chat_id,
            int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
            offset=int(session.get("campaigns_offset") or 0),
        )
        return
    if data.startswith("camp:view:"):
        key = data.split(":", 2)[-1]
        session = await load_session(redis, chat_id)
        items = session.get("campaigns_items") if isinstance(session.get("campaigns_items"), list) else []
        campaign = select_campaign(items, key)
        if campaign is None:
            await render_campaigns(
                panel,
                sb_client,
                redis,
                chat_id,
                int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
                offset=int(session.get("campaigns_offset") or 0),
            )
            session = await load_session(redis, chat_id)
            campaign = select_campaign(session.get("campaigns_items") or [], key)
        if campaign is None:
            await panel.render(chat_id=chat_id, text="Campaign not found on this page.", keyboard={"inline_keyboard": [[{"text": "Back", "callback_data": "act:back"}]]})
            return
        session["campaign_view"] = campaign
        await save_session(redis, chat_id, session)
        await push_route(redis, chat_id, routes.CAMPAIGN_VIEW, routes.CAMPAIGNS_LIST)
        await render_campaign_view(panel, redis, chat_id, settings)
        return

    if data in {"camp:disable", "camp:enable", "camp:preview", "camp:delete", "camp:delete:confirm"}:
        session = await load_session(redis, chat_id)
        campaign = session.get("campaign_view") if isinstance(session.get("campaign_view"), dict) else None
        if not campaign:
            await panel.render(chat_id=chat_id, text="Campaign context expired.", keyboard={"inline_keyboard": [[{"text": "Back", "callback_data": "act:back"}]]})
            return
        channel = str(campaign.get("channel") or settings.WIZARD_DEFAULT_CHANNEL)
        content_ref = str(campaign.get("content_ref") or "")
        error_msg = None

        if data == "camp:disable":
            session.pop("delete_confirm", None)  # reset delete confirm on any other action
            _, error = await run_sb_call(lambda: sb_client.disable_content_map(channel=channel, content_ref=content_ref), "Failed to disable")
            if error is None:
                campaign["is_active"] = False
                error_msg = "Campaign disabled"
            else:
                error_msg = error
        elif data == "camp:enable":
            session.pop("delete_confirm", None)
            item, error = await run_sb_call(
                lambda: sb_client.upsert_content_map(
                    channel=channel,
                    content_ref=content_ref,
                    start_param=campaign.get("start_param"),
                    slug=campaign.get("slug"),
                    meta=campaign.get("meta") if isinstance(campaign.get("meta"), dict) else {},
                    is_active=True,
                ),
                "Failed to enable",
            )
            if error is None and isinstance(item, dict):
                campaign.update(item)
                campaign["is_active"] = True
                error_msg = "Campaign enabled"
            else:
                error_msg = error
        elif data == "camp:delete":
            # First click - show confirm button
            session["delete_confirm"] = True
            session["campaign_view"] = campaign
            await save_session(redis, chat_id, session)
            await render_campaign_view(panel, redis, chat_id, settings, error_msg="Click 'Confirm Delete' to permanently remove")
            return
        elif data == "camp:delete:confirm":
            # Second click - actually delete
            _, error = await run_sb_call(lambda: sb_client.delete_content_map(channel=channel, content_ref=content_ref), "Failed to delete")
            if error is None:
                session["campaign_view"] = None
                session.pop("delete_confirm", None)
                await save_session(redis, chat_id, session)
                await render_campaigns(
                    panel,
                    sb_client,
                    redis,
                    chat_id,
                    int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
                    offset=int(session.get("campaigns_offset") or 0),
                    error_msg="Campaign deleted",
                )
                return
            error_msg = error
            session.pop("delete_confirm", None)
        else:  # camp:preview
            session.pop("delete_confirm", None)
            result, error = await run_sb_call(
                lambda: sb_client.resolve_preview(channel=channel, content_ref=content_ref, text="preview"),
                "Resolve preview failed",
            )
            if error is None and isinstance(result, dict):
                error_msg = f"Preview: {result.get('result')} | start_param={result.get('start_param') or 'NULL'}"
            else:
                error_msg = error

        session["campaign_view"] = campaign
        await save_session(redis, chat_id, session)
        await render_campaign_view(panel, redis, chat_id, settings, error_msg=error_msg)
        return

    if data == "ops:export":
        await _send_backup(chat_id, panel, messenger, sb_client)
        return

    if data == "ops:import":
        session = await load_session(redis, chat_id)
        session["awaiting_document"] = "import_content_map"
        await save_session(redis, chat_id, session)
        await panel.render(
            chat_id=chat_id,
            text="Restore / Import\n\nSend JSON document (array or {\"items\": [...]}) to import content_map.",
            keyboard={"inline_keyboard": [[{"text": "Main Menu", "callback_data": "nav:MAIN"}, {"text": "Home", "callback_data": "act:clean"}]]},
        )
        return

    if data == "ops:status":
        await _render_status(panel, chat_id, sb_client, settings)
        return

    if data == "act:back":
        if await go_back(panel, redis, chat_id):
            return
        route = await pop_route(redis, chat_id, routes.MAIN)
        if route == routes.MAIN:
            await show_main(panel, redis, chat_id)
            return
        if route == routes.CAMPAIGNS_LIST:
            session = await load_session(redis, chat_id)
            await render_campaigns(
                panel,
                sb_client,
                redis,
                chat_id,
                int(session.get("campaigns_limit") or settings.WIZARD_CAMPAIGNS_PAGE_LIMIT),
                offset=int(session.get("campaigns_offset") or 0),
            )
            return

    if data == f"nav:{routes.MAIN}":
        await show_main(panel, redis, chat_id)

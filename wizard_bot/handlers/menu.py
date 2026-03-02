from __future__ import annotations

import json
from datetime import UTC, datetime

from wizard_bot.handlers.campaigns import render_campaign_view, render_campaigns, search_campaign, select_campaign
from wizard_bot.handlers.create_link import go_back, handle_wizard_callback, start_create
from wizard_bot.handlers.ops_tools import build_status_text, count_recent_dynamic, run_sb_call
from wizard_bot.handlers.start import show_main
from wizard_bot.nav import routes
from wizard_bot.nav.stack import pop_route, push_route
from wizard_bot.ui.keyboards import analytics_keyboard, search_prompt_keyboard
from wizard_bot.ui.manychat import build_manychat_snippet
from wizard_bot.ui.manychat_sections import (
    ManyChatContext,
    render_section,
    get_section_keyboard,
    is_token_placeholder,
)
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


def _format_overview_text(payload: dict, title: str = "Analytics") -> str:
    by_result = payload.get("resolves_by_result") if isinstance(payload.get("resolves_by_result"), dict) else {}
    ctr = float(payload.get("ctr_bridge") or 0.0) * 100
    return "\n".join(
        [
            f"{title} ({int(payload.get('hours', 24))}h)",
            "",
            f"• resolves_total: {int(payload.get('resolves_total', 0))}",
            f"• hit: {int(by_result.get('hit', 0))}",
            f"• fallback_payload: {int(by_result.get('fallback_payload', 0))}",
            f"• fallback_catalog: {int(by_result.get('fallback_catalog', 0))}",
            f"• clicks_total: {int(payload.get('clicks_total', 0))}",
            f"• ctr_bridge: {ctr:.1f}%",
            f"• redirect_miss_total: {int(payload.get('redirect_miss_total', 0))}",
        ]
    )


def _format_top_text(payload: dict) -> str:
    click_rows = payload.get("top_campaigns_by_clicks") if isinstance(payload.get("top_campaigns_by_clicks"), list) else []
    resolve_rows = payload.get("top_campaigns_by_resolves") if isinstance(payload.get("top_campaigns_by_resolves"), list) else []
    lines = [f"Analytics Top ({int(payload.get('hours', 24))}h)", "", "By clicks:"]
    if not click_rows:
        lines.append("• no data")
    else:
        for row in click_rows[:10]:
            if isinstance(row, dict):
                lines.append(f"• {row.get('content_ref')}: {int(row.get('clicks_total', 0))}")

    lines.extend(["", "By resolves:"])
    if not resolve_rows:
        lines.append("• no data")
    else:
        for row in resolve_rows[:10]:
            if isinstance(row, dict):
                lines.append(f"• {row.get('content_ref')}: {int(row.get('resolves_total', 0))}")
    return "\n".join(lines)


async def handle_callback(data: str, chat_id: int, panel, redis, telegram, messenger, sb_client, settings) -> None:
    if data == "nav:CREATE_LINK":
        await push_route(redis, chat_id, routes.CREATE_LINK, routes.MAIN)
        await start_create(panel, redis, chat_id)
        return

    if await handle_wizard_callback(data, chat_id, panel, redis, sb_client, settings):
        return

    if data == "nav:ANALYTICS":
        await push_route(redis, chat_id, routes.ANALYTICS, routes.MAIN)
        session = await load_session(redis, chat_id)
        session["analytics_hours"] = 24
        session.pop("analytics_campaign", None)
        await save_session(redis, chat_id, session)
        payload, error = await run_sb_call(lambda: sb_client.stats_overview(hours=24), "analytics overview failed")
        text = _format_overview_text(payload) if error is None and isinstance(payload, dict) else f"Analytics\n\n⚠️ {error or 'failed to load analytics'}"
        await panel.render(chat_id=chat_id, text=text, keyboard=analytics_keyboard(hours=24, back_callback="act:back"))
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
    if data == "camp:view:analytics_back":
        session = await load_session(redis, chat_id)
        session.pop("analytics_campaign", None)
        await save_session(redis, chat_id, session)
        await render_campaign_view(panel, redis, chat_id, settings)
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
        preview, _ = await run_sb_call(
            lambda: sb_client.resolve_preview(
                channel=str(campaign.get("channel") or settings.WIZARD_DEFAULT_CHANNEL),
                content_ref=str(campaign.get("content_ref") or ""),
                text="preview",
            ),
            "Resolve preview failed",
        )
        if isinstance(preview, dict):
            campaign["url"] = preview.get("url")
            campaign["tg_url"] = preview.get("tg_url")
        session["campaign_view"] = campaign
        await save_session(redis, chat_id, session)
        await push_route(redis, chat_id, routes.CAMPAIGN_VIEW, routes.CAMPAIGNS_LIST)
        await render_campaign_view(panel, redis, chat_id, settings)
        return

    if data in {"camp:disable", "camp:enable", "camp:preview", "camp:delete", "camp:delete:confirm", "camp:manychat", "camp:analytics"}:
        session = await load_session(redis, chat_id)
        campaign = session.get("campaign_view") if isinstance(session.get("campaign_view"), dict) else None
        if not campaign:
            await panel.render(chat_id=chat_id, text="Campaign context expired.", keyboard={"inline_keyboard": [[{"text": "Back", "callback_data": "act:back"}]]})
            return
        channel = str(campaign.get("channel") or settings.WIZARD_DEFAULT_CHANNEL)
        content_ref = str(campaign.get("content_ref") or "")
        error_msg = None

        if data == "camp:manychat":
            mode = ""
            kind = ""
            if isinstance(campaign.get("meta"), dict):
                mode = str(campaign.get("meta", {}).get("mode") or "")
                kind = str(campaign.get("meta", {}).get("kind") or "")
            # Compute tg_url with fallback
            _tg_url = campaign.get("tg_url")
            if not _tg_url and campaign.get("start_param") and getattr(settings, "WIZARD_SIS_BOT_USERNAME", ""):
                _tg_url = f"https://t.me/{settings.WIZARD_SIS_BOT_USERNAME}?start={campaign.get('start_param')}"
            
            # Build context for compact UI
            ctx = ManyChatContext(
                slug=str(campaign.get("slug") or "campaign"),
                channel=channel or settings.WIZARD_DEFAULT_CHANNEL,
                content_ref=content_ref,
                url=str(campaign.get("url") or f"{settings.WIZARD_PUBLIC_BASE_URL}/t/{campaign.get('slug') or 'catalog'}"),
                tg_url=str(_tg_url or "-"),
                mc_resolve_url=settings.WIZARD_MC_RESOLVE_URL,
                mc_token=settings.WIZARD_MC_TOKEN,
                mode=mode,
                kind=kind or "product",
                start_param=str(campaign.get("start_param") or ""),
                keyword_product=getattr(settings, "WIZARD_KEYWORD_PRODUCT", "BUY"),
                keyword_look=getattr(settings, "WIZARD_KEYWORD_LOOK", "LOOK"),
                keyword_catalog=getattr(settings, "WIZARD_KEYWORD_CATALOG", "CAT"),
            )
            
            # Store context in session for section navigation
            session["manychat_ctx"] = {
                "slug": ctx.slug,
                "channel": ctx.channel,
                "content_ref": ctx.content_ref,
                "url": ctx.url,
                "tg_url": ctx.tg_url,
                "mc_resolve_url": ctx.mc_resolve_url,
                "mc_token": ctx.mc_token,
                "mode": ctx.mode,
                "kind": ctx.kind,
                "start_param": ctx.start_param,
                "keyword_product": ctx.keyword_product,
                "keyword_look": ctx.keyword_look,
                "keyword_catalog": ctx.keyword_catalog,
            }
            await save_session(redis, chat_id, session)
            
            # Render compact summary
            text = render_section(ctx, "pack")
            keyboard = get_section_keyboard(ctx, "pack", ctx.slug)
            await panel.render(chat_id=chat_id, text=text, keyboard=keyboard)
            return

        if data == "camp:analytics":
            session["analytics_campaign"] = content_ref
            await save_session(redis, chat_id, session)
            payload, error = await run_sb_call(
                lambda: sb_client.stats_campaign(content_ref=content_ref, hours=24),
                "campaign analytics failed",
            )
            text = _format_overview_text(payload, title=f"Campaign Analytics\n{content_ref}") if error is None and isinstance(payload, dict) else f"Campaign Analytics\n\n⚠️ {error or 'failed to load campaign analytics'}"
            await panel.render(
                chat_id=chat_id,
                text=text,
                keyboard=analytics_keyboard(hours=24, back_callback="camp:view:analytics_back"),
            )
            return

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
                campaign["url"] = result.get("url")
                campaign["tg_url"] = result.get("tg_url")
                error_msg = f"Preview: {result.get('result')} | start_param={result.get('start_param') or 'NULL'}"
            else:
                error_msg = error

        session["campaign_view"] = campaign
        await save_session(redis, chat_id, session)
        await render_campaign_view(panel, redis, chat_id, settings, error_msg=error_msg)
        return

    if data == "camp:snippet:back":
        await render_campaign_view(panel, redis, chat_id, settings)
        return

    # ManyChat section navigation: mc:<section>:<slug>
    if data.startswith("mc:"):
        parts = data.split(":")
        if len(parts) >= 3:
            section = parts[1]
            # slug may contain colons, so rejoin the rest
            slug = ":".join(parts[2:])
            
            session = await load_session(redis, chat_id)
            ctx_data = session.get("manychat_ctx")
            if not ctx_data or not isinstance(ctx_data, dict):
                await panel.render(
                    chat_id=chat_id,
                    text="Session expired. Go back to campaign.",
                    keyboard={"inline_keyboard": [[{"text": "Back", "callback_data": "camp:snippet:back"}]]},
                )
                return
            
            # Rebuild context from session
            ctx = ManyChatContext(
                slug=ctx_data.get("slug", slug),
                channel=ctx_data.get("channel", "ig"),
                content_ref=ctx_data.get("content_ref", ""),
                url=ctx_data.get("url", ""),
                tg_url=ctx_data.get("tg_url", ""),
                mc_resolve_url=ctx_data.get("mc_resolve_url", ""),
                mc_token=ctx_data.get("mc_token", ""),
                mode=ctx_data.get("mode", ""),
                kind=ctx_data.get("kind", "product"),
                start_param=ctx_data.get("start_param", ""),
                keyword_product=ctx_data.get("keyword_product", "BUY"),
                keyword_look=ctx_data.get("keyword_look", "LOOK"),
                keyword_catalog=ctx_data.get("keyword_catalog", "CAT"),
            )
            
            text = render_section(ctx, section)  # type: ignore
            keyboard = get_section_keyboard(ctx, section, ctx.slug)  # type: ignore
            await panel.render(chat_id=chat_id, text=text, keyboard=keyboard)
            return

    if data.startswith("analytics:hours:"):
        hours = int(data.split(":")[-1])
        session = await load_session(redis, chat_id)
        session["analytics_hours"] = hours
        await save_session(redis, chat_id, session)
        back_callback = "camp:view:analytics_back" if session.get("analytics_campaign") else "act:back"
        if session.get("analytics_campaign"):
            content_ref = str(session.get("analytics_campaign"))
            payload, error = await run_sb_call(
                lambda: sb_client.stats_campaign(content_ref=content_ref, hours=hours),
                "campaign analytics failed",
            )
            text = _format_overview_text(payload, title=f"Campaign Analytics\n{content_ref}") if error is None and isinstance(payload, dict) else f"Campaign Analytics\n\n⚠️ {error or 'failed to load campaign analytics'}"
        else:
            payload, error = await run_sb_call(lambda: sb_client.stats_overview(hours=hours), "analytics overview failed")
            text = _format_overview_text(payload) if error is None and isinstance(payload, dict) else f"Analytics\n\n⚠️ {error or 'failed to load analytics'}"
        await panel.render(chat_id=chat_id, text=text, keyboard=analytics_keyboard(hours=hours, back_callback=back_callback))
        return

    if data == "analytics:top":
        session = await load_session(redis, chat_id)
        back_callback = "camp:view:analytics_back" if session.get("analytics_campaign") else "act:back"
        hours = int(session.get("analytics_hours") or 24)
        payload, error = await run_sb_call(lambda: sb_client.stats_top(hours=hours, limit=20), "analytics top failed")
        text = _format_top_text(payload) if error is None and isinstance(payload, dict) else f"Analytics Top\n\n⚠️ {error or 'failed to load analytics top'}"
        await panel.render(chat_id=chat_id, text=text, keyboard=analytics_keyboard(hours=hours, back_callback=back_callback))
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

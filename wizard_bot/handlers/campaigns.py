from __future__ import annotations

from wizard_bot.ui.keyboards import campaign_view_keyboard, campaigns_keyboard
from wizard_bot.wizard.state import load_session, save_session


async def render_campaigns(panel, sb_client, redis, chat_id: int, limit: int, offset: int = 0, error_msg: str | None = None) -> None:
    payload = await sb_client.list_content_map(limit=limit, offset=offset, is_active=None)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    total = int(payload.get("total", len(items))) if isinstance(payload, dict) else len(items)

    session = await load_session(redis, chat_id)
    session["campaigns_items"] = items
    session["campaigns_offset"] = offset
    session["campaigns_limit"] = limit
    session.pop("delete_confirm", None)  # reset delete confirm state
    await save_session(redis, chat_id, session)

    if not items:
        text = "Campaigns\n\nNo campaigns found."
    else:
        lines = ["Campaigns", ""]
        for item in items:
            slug = item.get("slug") or "-"
            is_active = item.get("is_active", False)
            status_emoji = "✅" if is_active else "❌"
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            start_param = item.get("start_param")
            code_display = start_param or "Catalog"
            lines.append(f"{status_emoji} {slug} ({code_display})")
        lines.append("")
        lines.append(f"Showing {offset + 1}-{offset + len(items)} of {total}")
        text = "\n".join(lines)
    if error_msg:
        text = f"{text}\n\n⚠️ {error_msg}"
    await panel.render(chat_id=chat_id, text=text, keyboard=campaigns_keyboard(items, offset, limit, total))


async def render_campaign_view(panel, redis, chat_id: int, settings, error_msg: str | None = None) -> bool:
    session = await load_session(redis, chat_id)
    campaign = session.get("campaign_view")
    if not isinstance(campaign, dict):
        return False

    slug = campaign.get("slug") or "-"
    content_ref = campaign.get("content_ref") or "-"
    start_param = campaign.get("start_param")
    shortlink = f"{settings.WIZARD_PUBLIC_BASE_URL}/t/{slug}" if slug != "-" else "-"
    resolved_url = str(campaign.get("url") or shortlink)
    tg_url = str(campaign.get("tg_url") or "-")
    is_active = bool(campaign.get("is_active"))
    delete_confirm = bool(session.get("delete_confirm"))
    meta = campaign.get("meta") if isinstance(campaign.get("meta"), dict) else {}
    kind = meta.get("kind") or ""
    param_label = "product_code" if kind == "product" else "start_param"
    status_emoji = "✅" if is_active else "❌"
    lines = [
        f"Campaign View {status_emoji}",
        "",
        f"• slug: {slug}",
        f"• {param_label}: {start_param or 'Catalog'}",
        f"• channel: {campaign.get('channel') or '-'}",
        f"• content_ref: {content_ref}",
        f"• is_active: {is_active}",
        f"• url: {resolved_url}",
        f"• tg_url: {tg_url}",
    ]
    text = "\n".join(lines)
    if error_msg:
        text = f"{text}\n\n⚠️ {error_msg}"
    await panel.render(chat_id=chat_id, text=text, keyboard=campaign_view_keyboard(is_active=is_active, delete_confirm=delete_confirm))
    return True


def select_campaign(items: list[dict], key: str) -> dict | None:
    for item in items:
        slug = str(item.get("slug") or "")
        content_ref = str(item.get("content_ref") or "")
        if key == slug or key == content_ref:
            return item
    return None


async def search_campaign(sb_client, query: str) -> dict | None:
    """Search campaigns by slug or start_param (product code). Returns first match or None."""
    query_lower = query.lower().strip()
    if not query_lower:
        return None
    # Fetch all campaigns (reasonable limit)
    payload = await sb_client.list_content_map(limit=500, offset=0, is_active=None)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    for item in items:
        slug = str(item.get("slug") or "").lower()
        start_param = str(item.get("start_param") or "").lower()
        if query_lower == slug or query_lower == start_param:
            return item
    return None

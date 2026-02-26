from __future__ import annotations

from wizard_bot.ui.keyboards import campaign_view_keyboard, campaigns_keyboard
from wizard_bot.wizard.state import load_session, save_session


async def render_campaigns(panel, sb_client, redis, chat_id: int, limit: int, offset: int = 0) -> None:
    payload = await sb_client.list_content_map(limit=limit, offset=offset, is_active=None)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    total = int(payload.get("total", len(items))) if isinstance(payload, dict) else len(items)

    session = await load_session(redis, chat_id)
    session["campaigns_items"] = items
    session["campaigns_offset"] = offset
    session["campaigns_limit"] = limit
    await save_session(redis, chat_id, session)

    if not items:
        text = "Campaigns\n\nNo content mappings found."
    else:
        lines = ["Campaigns", ""]
        for item in items:
            slug = item.get("slug") or "-"
            channel = item.get("channel") or "-"
            lines.append(f"• {slug} ({channel})")
        lines.append("")
        lines.append(f"Showing {offset + 1}-{offset + len(items)} of {total}")
        text = "\n".join(lines)
    await panel.render(chat_id=chat_id, text=text, keyboard=campaigns_keyboard(items, offset, limit, total))


async def render_campaign_view(panel, redis, chat_id: int, settings) -> bool:
    session = await load_session(redis, chat_id)
    campaign = session.get("campaign_view")
    if not isinstance(campaign, dict):
        return False

    slug = campaign.get("slug") or "-"
    content_ref = campaign.get("content_ref") or "-"
    shortlink = f"{settings.WIZARD_PUBLIC_BASE_URL}/t/{slug}" if slug != "-" else "-"
    is_active = bool(campaign.get("is_active"))
    lines = [
        "Campaign View",
        "",
        f"• channel: {campaign.get('channel') or '-'}",
        f"• content_ref: {content_ref}",
        f"• start_param: {campaign.get('start_param') or 'Catalog'}",
        f"• slug: {slug}",
        f"• is_active: {is_active}",
        f"• shortlink: {shortlink}",
    ]
    await panel.render(chat_id=chat_id, text="\n".join(lines), keyboard=campaign_view_keyboard(is_active=is_active))
    return True


def select_campaign(items: list[dict], key: str) -> dict | None:
    for item in items:
        slug = str(item.get("slug") or "")
        content_ref = str(item.get("content_ref") or "")
        if key == slug or key == content_ref:
            return item
    return None

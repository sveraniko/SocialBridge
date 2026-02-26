from wizard_bot.ui.keyboards import campaigns_keyboard
from wizard_bot.utils.text import truncate


async def render_campaigns(panel, sb_client, chat_id: int, limit: int) -> None:
    campaigns = await sb_client.list_campaigns(limit=limit)
    if not campaigns:
        text = "Campaigns\n\nNo content mappings found."
    else:
        lines = ["Campaigns", ""]
        for item in campaigns:
            lines.append(f"• {truncate(item.get('content_ref', '-'), 45)} → {truncate(item.get('slug', '-'), 30)}")
        text = "\n".join(lines)
    await panel.render(chat_id=chat_id, text=text, keyboard=campaigns_keyboard())

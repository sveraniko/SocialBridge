from wizard_bot.ui.keyboards import (
    kind_keyboard,
    main_menu_keyboard,
    result_keyboard,
    slug_choice_keyboard,
    step_back_cancel_keyboard,
)
from wizard_bot.wizard.state import ensure_campaign_key

MODE_TEXT = {
    "0": "Direct shortlink only",
    "1": "Keyword BUY + code",
    "2": "Per-post comment-to-DM mapping",
}


async def render_step(panel, chat_id: int, data: dict) -> None:
    step = data.get("step", "mode")
    error = data.get("error")

    if step == "mode":
        text = "Create campaign/link\n\nStep 1/5: Choose mode."
        kb = {
            "inline_keyboard": [
                [{"text": "Mode 0 · Direct shortlink", "callback_data": "wiz:mode:0"}],
                [{"text": "Mode 1 · BUY + code", "callback_data": "wiz:mode:1"}],
                [{"text": "Mode 2 · Comment→DM mapping", "callback_data": "wiz:mode:2"}],
                [{"text": "Cancel", "callback_data": "nav:MAIN"}, {"text": "Clean Chat", "callback_data": "act:clean"}],
            ]
        }
    elif step == "kind":
        text = "Create campaign/link\n\nStep 2/5: Choose kind."
        kb = kind_keyboard()
    elif step == "start_param":
        prompt = "Enter start param"
        if data.get("kind") == "look":
            prompt += " (must start with LOOK_)."
        elif data.get("kind") == "product":
            prompt += " (example: DRESS001)."
        text = f"Create campaign/link\n\nStep 3/5: {prompt}\n\nSend one text message."
        kb = step_back_cancel_keyboard(skip=False)
    elif step == "slug_choice":
        text = "Create campaign/link\n\nStep 4/5: Slug auto or custom?"
        kb = slug_choice_keyboard()
    elif step == "slug_input":
        text = "Create campaign/link\n\nStep 4/5: Send custom slug text (lowercase)."
        kb = step_back_cancel_keyboard(skip=True)
    elif step == "confirm":
        key = ensure_campaign_key(data)
        lines = [
            "Create campaign/link",
            "",
            "Step 5/5: Confirm",
            f"• mode: {MODE_TEXT.get(str(data.get('mode')), '-')}",
            f"• kind: {data.get('kind', '-')}",
            f"• content_ref: campaign:{key}",
            f"• start_param: {data.get('start_param') or 'NULL'}",
            f"• slug: {data.get('slug') or 'auto'}",
        ]
        if str(data.get("mode")) == "1" and data.get("start_param"):
            lines.append(f"• note: BUY {data['start_param']}")
        text = "\n".join(lines)
        kb = {
            "inline_keyboard": [
                [{"text": "Create", "callback_data": "wiz:create"}],
                [{"text": "Back", "callback_data": "act:back"}, {"text": "Cancel", "callback_data": "nav:MAIN"}],
                [{"text": "Clean Chat", "callback_data": "act:clean"}],
            ]
        }
    elif step == "result":
        item = data.get("created_item") or {}
        shortlink = item.get("shortlink") or "-"
        key = ensure_campaign_key(data)
        lines = [
            "Campaign created ✅",
            f"Shortlink: {shortlink}",
            "",
        ]
        mode = str(data.get("mode"))
        if mode == "0":
            lines.append(f"Link for bio/story/pinned comment: {shortlink}")
        elif mode == "1":
            code = data.get("start_param") or "CODE"
            lines.extend([f"Комментируй: BUY {code}", f"BUY {code}"])
        else:
            lines.extend(
                [
                    "ManyChat snippet:",
                    "sb_channel=ig",
                    f"sb_content_ref=campaign:{key}",
                    'External Request body: {"channel":"{{sb_channel}}","content_ref":"{{sb_content_ref}}","text":"{{last_text_input}}"}',
                    "Map response: sb_last_url <- url, sb_reply_text <- reply_text",
                ]
            )
        status_line = data.get("result_status")
        if status_line:
            lines.extend(["", status_line])
        text = "\n".join(lines)
        kb = result_keyboard(bool(item.get("is_active", True)))
    else:
        text = "Campaign Wizard\n\nChoose an action:"
        kb = main_menu_keyboard()

    if error:
        text = f"{text}\n\n⚠️ {error}"
    await panel.render(chat_id=chat_id, text=text, keyboard=kb)

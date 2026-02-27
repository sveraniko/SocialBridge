from wizard_bot.ui.keyboards import (
    kind_keyboard,
    main_menu_keyboard,
    result_keyboard,
    slug_choice_keyboard,
    step_back_cancel_keyboard,
)
from wizard_bot.ui.manychat import build_manychat_snippet
from wizard_bot.wizard.state import ensure_campaign_key

MODE_TEXT = {
    "0": "Direct shortlink only",
    "1": "Keyword mode (by kind)",
    "2": "Per-post comment-to-DM mapping",
}


async def render_step(panel, chat_id: int, data: dict, settings=None) -> None:
    step = data.get("step", "mode")
    error = data.get("error")

    if step == "mode":
        text = "Create campaign/link\n\nStep 1/5: Choose mode."
        kb = {
            "inline_keyboard": [
                [{"text": "Mode 0 · Direct shortlink", "callback_data": "wiz:mode:0"}],
                [{"text": "Mode 1 · Keyword + code", "callback_data": "wiz:mode:1"}],
                [{"text": "Mode 2 · Comment→DM mapping", "callback_data": "wiz:mode:2"}],
                [{"text": "Cancel", "callback_data": "nav:MAIN"}, {"text": "Home", "callback_data": "act:clean"}],
            ]
        }
    elif step == "kind":
        text = "Create campaign/link\n\nStep 2/5: Choose kind."
        kb = kind_keyboard()
    elif step == "start_param":
        if data.get("kind") == "product":
            prompt = "Enter product code/start_param (example: BOIZMRJS)."
        elif data.get("kind") == "look":
            prompt = "Enter look code/start_param (example: LOOK_SPRING26 or SPRING26)."
        else:
            prompt = "Enter start param."
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
            f"• {'product code' if data.get('kind') == 'product' else 'look code' if data.get('kind') == 'look' else 'start_param'}: {data.get('start_param') or 'NULL'}",
            f"• slug: {data.get('slug') or 'auto'}",
        ]
        if str(data.get("mode")) == "1":
            keyword_product = getattr(settings, "WIZARD_KEYWORD_PRODUCT", "BUY") if settings else "BUY"
            keyword_look = getattr(settings, "WIZARD_KEYWORD_LOOK", "LOOK") if settings else "LOOK"
            keyword_catalog = getattr(settings, "WIZARD_KEYWORD_CATALOG", "CAT") if settings else "CAT"
            from wizard_bot.ui.manychat import mode1_trigger_text
            lines.append(
                f"• note: {mode1_trigger_text(data.get('kind'), data.get('start_param'), keyword_product, keyword_look, keyword_catalog)}"
            )
        text = "\n".join(lines)
        kb = {
            "inline_keyboard": [
                [{"text": "Create", "callback_data": "wiz:create"}],
                [{"text": "Back", "callback_data": "act:back"}, {"text": "Cancel", "callback_data": "nav:MAIN"}],
                [{"text": "Home", "callback_data": "act:clean"}],
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
            keyword_product = getattr(settings, "WIZARD_KEYWORD_PRODUCT", "BUY") if settings else "BUY"
            keyword_look = getattr(settings, "WIZARD_KEYWORD_LOOK", "LOOK") if settings else "LOOK"
            keyword_catalog = getattr(settings, "WIZARD_KEYWORD_CATALOG", "CAT") if settings else "CAT"
            from wizard_bot.ui.manychat import mode1_trigger_text
            trigger = mode1_trigger_text(data.get("kind"), data.get("start_param"), keyword_product, keyword_look, keyword_catalog)
            lines.extend([f"Комментируй: {trigger}", trigger])
        else:
            lines.append("Post-specific campaign mapping (comment→DM).")
            # Compute tg_url with fallback
            _tg_url = item.get("tg_url")
            if not _tg_url and data.get("start_param") and getattr(settings, "WIZARD_SIS_BOT_USERNAME", ""):
                _tg_url = f"https://t.me/{settings.WIZARD_SIS_BOT_USERNAME}?start={data.get('start_param')}"
            lines.extend(
                build_manychat_snippet(
                    channel="ig",
                    content_ref=f"campaign:{key}",
                    url=shortlink,
                    tg_url=str(_tg_url or "-"),
                    mc_resolve_url=getattr(settings, "WIZARD_MC_RESOLVE_URL", "https://your-domain.com/v1/mc/resolve"),
                    mc_token=getattr(settings, "WIZARD_MC_TOKEN", "<YOUR_MC_TOKEN>"),
                    mode=mode,
                    kind=data.get("kind"),
                    start_param=data.get("start_param"),
                    keyword_product=getattr(settings, "WIZARD_KEYWORD_PRODUCT", "BUY"),
                    keyword_look=getattr(settings, "WIZARD_KEYWORD_LOOK", "LOOK"),
                    keyword_catalog=getattr(settings, "WIZARD_KEYWORD_CATALOG", "CAT"),
                ).splitlines()
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

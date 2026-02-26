from wizard_bot.handlers.ops_tools import run_sb_call
from wizard_bot.wizard.panels import render_step
from wizard_bot.wizard.state import apply_back, apply_step, ensure_campaign_key, load_session, reset_session, save_session
from wizard_bot.wizard.validators import validate_slug, validate_start_param


async def start_create(panel, redis, chat_id: int) -> None:
    data = await reset_session(redis, chat_id)
    await render_step(panel, chat_id, data)


async def handle_wizard_callback(data: str, chat_id: int, panel, redis, sb_client, settings) -> bool:
    if not data.startswith("wiz:"):
        return False
    session = await load_session(redis, chat_id)

    if data.startswith("wiz:mode:"):
        session["mode"] = data.split(":")[-1]
        apply_step(session, "kind")
    elif data.startswith("wiz:kind:"):
        session["kind"] = data.split(":")[-1]
        if session["kind"] == "catalog":
            session["start_param"] = None
            apply_step(session, "slug_choice")
        else:
            apply_step(session, "start_param")
            session["awaiting_input"] = "start_param"
    elif data == "wiz:slug:auto":
        session["slug_mode"] = "auto"
        session["slug"] = None
        apply_step(session, "confirm")
    elif data == "wiz:slug:custom":
        session["slug_mode"] = "custom"
        apply_step(session, "slug_input")
        session["awaiting_input"] = "slug"
    elif data == "wiz:slug:skip":
        session["slug_mode"] = "auto"
        session["slug"] = None
        apply_step(session, "confirm")
    elif data == "wiz:create":
        key = ensure_campaign_key(session)
        content_ref = f"campaign:{key}"
        payload = {
            "mode": str(session.get("mode")),
            "kind": str(session.get("kind")),
            "wizard": True,
        }

        item, error = await run_sb_call(
            lambda: sb_client.upsert_content_map(
                channel=settings.WIZARD_DEFAULT_CHANNEL,
                content_ref=content_ref,
                start_param=session.get("start_param"),
                slug=session.get("slug"),
                meta=payload,
                is_active=True,
            ),
            "Failed to create campaign",
        )
        if error:
            session["error"] = error
        elif isinstance(item, dict):
            item["shortlink"] = f"{settings.WIZARD_PUBLIC_BASE_URL}/t/{item.get('slug', '-')}" if item.get("slug") else "-"
            session["created_item"] = item
            apply_step(session, "result")
    elif data == "wiz:disable":
        key = ensure_campaign_key(session)
        _, error = await run_sb_call(
            lambda: sb_client.disable_content_map(channel=settings.WIZARD_DEFAULT_CHANNEL, content_ref=f"campaign:{key}"),
            "Failed to disable campaign",
        )
        session["error"] = error or "Campaign disabled."
    elif data == "wiz:preview":
        key = ensure_campaign_key(session)
        result, error = await run_sb_call(
            lambda: sb_client.resolve_preview(
                channel=settings.WIZARD_DEFAULT_CHANNEL,
                content_ref=f"campaign:{key}",
                text="preview",
            ),
            "Failed to run resolve preview",
        )
        if error:
            session["error"] = error
        elif isinstance(result, dict):
            session["error"] = (
                f"Preview: result={result.get('result')} url={result.get('url')} start_param={result.get('start_param') or 'NULL'}"
            )
    await save_session(redis, chat_id, session)
    await render_step(panel, chat_id, session)
    return True


async def handle_wizard_input(chat_id: int, text: str, panel, redis, telegram) -> bool:
    session = await load_session(redis, chat_id)
    field = session.get("awaiting_input")
    if not field:
        return False
    if field == "start_param":
        ok, cleaned, error = validate_start_param(str(session.get("kind")), text)
        if not ok:
            session["error"] = error
        else:
            session["start_param"] = cleaned
            apply_step(session, "slug_choice")
    elif field == "slug":
        ok, cleaned, error = validate_slug(text)
        if not ok:
            session["error"] = error
        else:
            session["slug"] = cleaned
            apply_step(session, "confirm")
    await save_session(redis, chat_id, session)
    await render_step(panel, chat_id, session)
    return True


async def go_back(panel, redis, chat_id: int) -> bool:
    session = await load_session(redis, chat_id)
    step = session.get("step")
    if step not in {"mode", "kind", "start_param", "slug_choice", "slug_input", "confirm", "result"}:
        return False
    apply_back(session)
    if session.get("step") in {"start_param", "slug_input"}:
        session["awaiting_input"] = "start_param" if session["step"] == "start_param" else "slug"
    await save_session(redis, chat_id, session)
    await render_step(panel, chat_id, session)
    return True

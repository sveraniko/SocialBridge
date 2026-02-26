from app.domain.types import ResolveInput


def normalize(payload: dict) -> ResolveInput:
    mc = payload.get("mc") if isinstance(payload.get("mc"), dict) else {}
    content_ref = payload.get("content_ref")
    text = payload.get("text")
    payload_min = {
        "channel": payload.get("channel"),
        "content_ref": content_ref,
        "flow_id": mc.get("flow_id"),
        "trigger": mc.get("trigger"),
    }
    return ResolveInput(
        channel=str(payload.get("channel", "")),
        content_ref=content_ref if isinstance(content_ref, str) else None,
        text=text if isinstance(text, str) else None,
        mc_contact_id=str(mc.get("contact_id")) if mc.get("contact_id") else None,
        mc_flow_id=str(mc.get("flow_id")) if mc.get("flow_id") else None,
        mc_trigger=str(mc.get("trigger")) if mc.get("trigger") else None,
        payload_min=payload_min,
    )

from __future__ import annotations


def build_manychat_snippet(
    *,
    channel: str,
    content_ref: str,
    url: str,
    tg_url: str,
    mc_resolve_url: str,
    mc_token: str,
    mode: str | None = None,
    start_param: str | None = None,
) -> str:
    lines = [
        "ManyChat Snippet",
        "",
        f"sb_channel={channel}",
        f"sb_content_ref={content_ref}",
        "",
        f"External Request URL: {mc_resolve_url}",
        "Headers:",
        "- Content-Type: application/json",
        f"- X-MC-Token: {mc_token}",
        "",
        "Body template:",
        '{"channel":"{{sb_channel}}","content_ref":"{{sb_content_ref}}","text":"{{last_text_input}}"}',
        "",
        "Map response:",
        "- sb_last_url <- url",
        "- sb_tg_url <- tg_url",
        "- sb_reply_text <- reply_text",
        "",
        f"Preview url: {url}",
        f"Preview tg_url: {tg_url}",
    ]

    if str(mode) == "1":
        code = start_param or "CODE"
        lines.extend(["", f"Comment trigger: BUY {code}", f"BUY {code}"])

    return "\n".join(lines)


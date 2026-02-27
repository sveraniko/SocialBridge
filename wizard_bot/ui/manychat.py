from __future__ import annotations


def mode1_trigger_text(kind: str | None, start_param: str | None, keyword_product: str, keyword_look: str, keyword_catalog: str) -> str:
    kind_value = str(kind or "").lower()
    if kind_value == "catalog":
        return keyword_catalog
    code = start_param or "CODE"
    keyword = keyword_look if kind_value == "look" else keyword_product
    return f"{keyword} {code}"


def build_manychat_snippet(
    *,
    channel: str,
    content_ref: str,
    url: str,
    tg_url: str,
    mc_resolve_url: str = "https://your-domain.com/v1/mc/resolve",
    mc_token: str = "<YOUR_MC_TOKEN>",
    mode: str | None = None,
    kind: str | None = None,
    start_param: str | None = None,
    keyword_product: str = "BUY",
    keyword_look: str = "LOOK",
    keyword_catalog: str = "CAT",
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
        trigger = mode1_trigger_text(kind, start_param, keyword_product, keyword_look, keyword_catalog)
        lines.extend(["", f"Comment trigger: {trigger}", trigger])

    return "\n".join(lines)

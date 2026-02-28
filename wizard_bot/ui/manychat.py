from __future__ import annotations

# Default keyword values for comparison
DEFAULT_KEYWORD_PRODUCT = "BUY"
DEFAULT_KEYWORD_LOOK = "LOOK"
DEFAULT_KEYWORD_CATALOG = "CAT"


def mode1_trigger_text(kind: str | None, start_param: str | None, keyword_product: str, keyword_look: str, keyword_catalog: str) -> str:
    kind_value = str(kind or "").lower()
    if kind_value == "catalog":
        return keyword_catalog
    code = start_param or "CODE"
    keyword = keyword_look if kind_value == "look" else keyword_product
    return f"{keyword} {code}"


def _format_keyword_line(name: str, value: str, default: str) -> str:
    """Format keyword line showing value and whether it's overridden."""
    if value == default:
        return f"  {name}: {value} (default)"
    return f"  {name}: {value} (overridden, default: {default})"


def build_keyword_config_section(
    keyword_product: str,
    keyword_look: str,
    keyword_catalog: str,
) -> str:
    """Build keyword configuration info section for ManyChat setup."""
    lines = [
        "",
        "━━━ Keyword Configuration ━━━",
        _format_keyword_line("KEYWORD_PRODUCT", keyword_product, DEFAULT_KEYWORD_PRODUCT),
        _format_keyword_line("KEYWORD_LOOK", keyword_look, DEFAULT_KEYWORD_LOOK),
        _format_keyword_line("KEYWORD_CATALOG", keyword_catalog, DEFAULT_KEYWORD_CATALOG),
        "",
        "⚠️ Note: Deep link prefix 'LOOK_' is hardcoded in SIS.",
        "   Changing KEYWORD_LOOK affects user input only.",
    ]
    return "\n".join(lines)


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

    # Add keyword configuration section for all modes
    lines.append(build_keyword_config_section(keyword_product, keyword_look, keyword_catalog))

    return "\n".join(lines)

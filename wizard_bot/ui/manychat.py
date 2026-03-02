from __future__ import annotations

# Default keyword values for comparison
DEFAULT_KEYWORD_PRODUCT = "BUY"
DEFAULT_KEYWORD_LOOK = "LOOK"
DEFAULT_KEYWORD_CATALOG = "CAT"

# Token placeholder patterns that indicate misconfiguration
TOKEN_PLACEHOLDERS = ("change-me", "your_mc_token", "<set", "placeholder", "<your")


def mode1_trigger_text(
    kind: str | None,
    start_param: str | None,
    keyword_product: str,
    keyword_look: str,
    keyword_catalog: str,
) -> str:
    """Generate trigger text for Mode 1 (keyword DM)."""
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


def _is_token_placeholder(token: str) -> bool:
    """Check if token is a placeholder/unconfigured value."""
    token_lower = token.lower()
    return any(p in token_lower for p in TOKEN_PLACEHOLDERS)


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


def _build_section_header(title: str) -> str:
    """Build a section header with visual separator."""
    return f"\n{'━' * 40}\n📋 {title}\n{'━' * 40}"


def _build_custom_fields_section() -> str:
    """Section 1: Custom Fields to create in ManyChat."""
    return """\n1️⃣ CUSTOM FIELDS (create in ManyChat)
   Name             Type
   ─────────────────────
   sb_channel       Text
   sb_content_ref   Text
   sb_last_url      Text
   sb_tg_url        Text
   sb_reply_text    Text"""


def _build_request_section(
    mc_resolve_url: str,
    mc_token: str,
    body_template: str,
) -> str:
    """Section 3: External Request configuration."""
    lines = [
        "\n3️⃣ EXTERNAL REQUEST",
        f"   URL: {mc_resolve_url}",
        "",
        "   Headers:",
        "   ├─ Content-Type: application/json",
        f"   └─ X-MC-Token: {mc_token}",
        "",
        "   Body:",
        f"   {body_template}",
    ]
    return "\n".join(lines)


def _build_response_mapping_section() -> str:
    """Section 4: Response mapping (plain + JSONPath)."""
    return """\n4️⃣ MAP RESPONSE TO FIELDS
   Plain style (most UIs):
   ├─ sb_last_url    ←  url
   ├─ sb_tg_url      ←  tg_url
   └─ sb_reply_text  ←  reply_text

   JSONPath style (if required):
   ├─ sb_last_url    ←  $.url
   ├─ sb_tg_url      ←  $.tg_url
   └─ sb_reply_text  ←  $.reply_text

   💡 Use JSONPath if ManyChat mapping UI requires it."""


def _build_send_message_section(is_mode2: bool = False) -> str:
    """Section 5: Send Message example."""
    if is_mode2:
        return """\n5️⃣ SEND MESSAGE (example)
   Text: {{sb_reply_text}}
   Button: "Открыть товар" → {{sb_tg_url}}

   URL recommendations:
   ├─ DM: use sb_tg_url (direct Telegram link)
   └─ Public/tracking: use sb_last_url (branded shortlink)

   ⚠️ If user never started bot, they must press Start first."""
    return """\n5️⃣ SEND MESSAGE (example)
   Text: {{sb_reply_text}}
   Button: "Открыть товар" → {{sb_tg_url}}

   URL recommendations:
   ├─ DM: use sb_tg_url (direct Telegram link)
   └─ Public/tracking: use sb_last_url (branded shortlink)"""


def _build_template_a_mode2(
    channel: str,
    content_ref: str,
    mc_resolve_url: str,
    mc_token: str,
) -> str:
    """Template A: Post/Story/Comment triggers (Mode 2) - no text input."""
    body = '{"channel":"{{sb_channel}}","content_ref":"{{sb_content_ref}}","text":""}'
    lines = [
        _build_section_header("TEMPLATE A — Post/Story/Comment (Mode 2)"),
        "",
        "Use for: Post comments, Reel comments, Story replies",
        "Text input: NOT required (empty string)",
        _build_custom_fields_section(),
        "\n2️⃣ TRIGGER SETUP",
        "   Choose one:",
        "   • Post/Reel comment trigger",
        "   • Story reply trigger",
        "   • Instagram Comment Growth Tool",
        "",
        "   Pre-fill custom fields:",
        f"   ├─ sb_channel = {channel}",
        f"   └─ sb_content_ref = {content_ref}",
        _build_request_section(mc_resolve_url, mc_token, body),
        _build_response_mapping_section(),
        _build_send_message_section(is_mode2=True),
    ]
    return "\n".join(lines)


def _build_template_b_mode1(
    channel: str,
    content_ref: str,
    mc_resolve_url: str,
    mc_token: str,
    keyword_product: str,
    keyword_look: str,
    keyword_catalog: str,
    kind: str | None,
    start_param: str | None,
) -> str:
    """Template B: Keyword DM triggers (Mode 1) - requires INCOMING_TEXT."""
    body = '{"channel":"{{sb_channel}}","content_ref":"","text":"INCOMING_TEXT"}'
    trigger = mode1_trigger_text(kind, start_param, keyword_product, keyword_look, keyword_catalog)
    kind_value = str(kind or "").lower()
    
    lines = [
        _build_section_header("TEMPLATE B — Keyword DM (Mode 1)"),
        "",
        "Use for: Direct message keyword triggers",
        "Text input: REQUIRED (user's message)",
        _build_custom_fields_section(),
        "\n2️⃣ TRIGGER SETUP",
        "   Trigger type: Direct Message",
        "   Condition: message starts with keyword",
        "",
        "   Expected user input examples:",
    ]
    
    # Show keyword examples based on kind
    if kind_value == "catalog":
        lines.append(f"   └─ \"{keyword_catalog}\" (opens catalog)")
    elif kind_value == "look":
        lines.append(f"   └─ \"{keyword_look} {start_param or 'CODE'}\" (opens look)")
    else:
        lines.append(f"   └─ \"{keyword_product} {start_param or 'CODE'}\" (opens product)")
    
    lines.extend([
        "",
        f"   Pre-fill sb_channel = {channel}",
        "   (sb_content_ref left empty — resolved from text)",
        _build_request_section(mc_resolve_url, mc_token, body),
        "",
        "   ⚠️ IMPORTANT: Replace INCOMING_TEXT with ManyChat's",
        "      variable for incoming message text.",
        "      (Select from dropdown/autocomplete in ManyChat UI)",
        _build_response_mapping_section(),
        _build_send_message_section(is_mode2=False),
        "",
        "   Configured keywords:",
        f"   ├─ Product: {keyword_product}",
        f"   ├─ Look: {keyword_look}",
        f"   └─ Catalog: {keyword_catalog}",
    ])
    return "\n".join(lines)


def _build_mode0_section(url: str, tg_url: str) -> str:
    """Mode 0: Direct shortlink - ManyChat not required."""
    return f"""\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 MODE 0 — Direct Shortlink
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ManyChat NOT required for this mode.
Use shortlink directly in bio/story/pinned comment.

Shortlink: {url}
Telegram:  {tg_url}

💡 For tracking, prefer shortlink (sb_last_url).
   For direct bot access, use Telegram link (sb_tg_url).

(Template A shown below if ManyChat still needed)"""


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
    """Build mode-aware ManyChat integration snippet.
    
    Modes:
    - Mode 0: Direct shortlink (ManyChat optional)
    - Mode 1: Keyword DM (requires INCOMING_TEXT)
    - Mode 2: Post/Story/Comment (no text input)
    """
    mode_str = str(mode or "")
    kind_str = str(kind or "product").lower()
    
    # Header with mode/kind info
    lines = [
        f"🔧 ManyChat Integration Pack",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Mode: {mode_str or '—'} | Kind: {kind_str}",
        f"Channel: {channel} | Ref: {content_ref or '(dynamic)'}",
        "",
        f"Preview URLs:",
        f"├─ Shortlink: {url}",
        f"└─ Telegram:  {tg_url}",
    ]
    
    # Token warning if placeholder detected
    if _is_token_placeholder(mc_token):
        lines.extend([
            "",
            "⚠️ WARNING: WIZARD_MC_TOKEN not configured!",
            "   Set MC_TOKEN in .env before production.",
        ])
    
    # Mode-specific content
    if mode_str == "0":
        # Mode 0: Direct shortlink, ManyChat optional
        lines.append(_build_mode0_section(url, tg_url))
        # Still show Template A as optional
        lines.append(_build_template_a_mode2(channel, content_ref, mc_resolve_url, mc_token))
    
    elif mode_str == "1":
        # Mode 1: Keyword DM - show Template B (primary) + Template A (optional)
        lines.append(_build_template_b_mode1(
            channel, content_ref, mc_resolve_url, mc_token,
            keyword_product, keyword_look, keyword_catalog,
            kind, start_param,
        ))
        lines.extend([
            "",
            "─" * 40,
            "💡 Alternative: Use Template A if also using post triggers.",
        ])
        lines.append(_build_template_a_mode2(channel, content_ref, mc_resolve_url, mc_token))
    
    elif mode_str == "2":
        # Mode 2: Post/Story/Comment - show Template A (primary)
        lines.append(_build_template_a_mode2(channel, content_ref, mc_resolve_url, mc_token))
        lines.extend([
            "",
            "─" * 40,
            "💡 Alternative: Use Template B if also using keyword DM triggers.",
        ])
        lines.append(_build_template_b_mode1(
            channel, content_ref, mc_resolve_url, mc_token,
            keyword_product, keyword_look, keyword_catalog,
            kind, start_param,
        ))
    
    else:
        # Unknown mode - show both templates
        lines.extend([
            "",
            "Mode not specified. Showing both templates:",
        ])
        lines.append(_build_template_a_mode2(channel, content_ref, mc_resolve_url, mc_token))
        lines.append(_build_template_b_mode1(
            channel, content_ref, mc_resolve_url, mc_token,
            keyword_product, keyword_look, keyword_catalog,
            kind, start_param,
        ))
    
    # Keyword configuration section at the end
    lines.append(build_keyword_config_section(keyword_product, keyword_look, keyword_catalog))
    
    return "\n".join(lines)

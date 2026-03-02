"""Compact toggle-driven ManyChat Integration Pack UI.

Provides modular render functions for section-based navigation:
- render_pack_summary(ctx) - compact overview with section buttons
- render_template_a(ctx) - Mode 2: Post/Story/Comment
- render_template_b(ctx) - Mode 1: Keyword DM
- render_fields(ctx) - Custom Fields
- render_trigger(ctx) - Trigger Setup (mode-aware)
- render_request(ctx) - External Request
- render_mapping(ctx) - Response Mapping (plain + JSONPath)
- render_send(ctx) - Send Message example
- render_keywords(ctx) - Keywords/Notes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Section identifiers
Section = Literal["pack", "tpl_a", "tpl_b", "fields", "trigger", "request", "mapping", "send", "keywords"]

SECTIONS_ORDER: list[Section] = ["tpl_a", "tpl_b", "fields", "trigger", "request", "mapping", "send", "keywords"]

# Token placeholder patterns
TOKEN_PLACEHOLDERS = ("change-me", "your_mc_token", "<set", "placeholder", "<your", "")


@dataclass
class ManyChatContext:
    """Context for ManyChat pack rendering."""
    slug: str
    channel: str
    content_ref: str
    url: str
    tg_url: str
    mc_resolve_url: str
    mc_token: str
    mode: str  # "0", "1", "2", or ""
    kind: str  # "product", "look", "catalog"
    start_param: str
    keyword_product: str
    keyword_look: str
    keyword_catalog: str
    look_prefix: str = "LOOK_"
    resolve_require_keyword: bool = False


def is_token_placeholder(token: str) -> bool:
    """Check if token is a placeholder/unconfigured value."""
    if not token:
        return True
    token_lower = token.lower()
    return any(p in token_lower for p in TOKEN_PLACEHOLDERS if p)


def get_safe_token(mc_token: str) -> str:
    """Return safe token display (hide placeholder values)."""
    return "<SET_ME>" if is_token_placeholder(mc_token) else mc_token


# ============= Section Renderers =============

def render_pack_summary(ctx: ManyChatContext) -> str:
    """Compact summary with essential info."""
    token_status = "✅ configured" if not is_token_placeholder(ctx.mc_token) else "⚠️ placeholder"
    
    lines = [
        "🔧 ManyChat Integration Pack",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Mode: {ctx.mode or '—'} | Kind: {ctx.kind}",
        f"Channel: {ctx.channel}",
        f"Ref: {ctx.content_ref or '(dynamic)'}",
        "",
        f"🔗 {ctx.url}",
        f"📲 {ctx.tg_url}",
        "",
        f"Token: {token_status}",
    ]
    
    if is_token_placeholder(ctx.mc_token):
        lines.extend([
            "",
            "⚠️ Set MC_TOKEN in .env before production!",
        ])
    
    return "\n".join(lines)


def render_template_a(ctx: ManyChatContext) -> str:
    """Template A: Post/Story/Comment (Mode 2) - full instructions."""
    body = '{"channel":"{{sb_channel}}","content_ref":"{{sb_content_ref}}","text":""}'
    token = get_safe_token(ctx.mc_token)
    
    return f"""📋 TEMPLATE A — Post/Story/Comment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use for: Post comments, Reel comments, Story replies
Text input: NOT required (empty string)

FLOW:
1. Set sb_channel = {ctx.channel}
2. Set sb_content_ref = {ctx.content_ref}
3. External Request → resolve
4. Send Message with button

BODY (copy):
{body}

HEADERS:
• Content-Type: application/json
• X-MC-Token: {token}

URL: {ctx.mc_resolve_url}"""


def render_template_b(ctx: ManyChatContext) -> str:
    """Template B: Keyword DM (Mode 1) - full instructions."""
    body = '{"channel":"{{sb_channel}}","content_ref":"","text":"INCOMING_TEXT"}'
    token = get_safe_token(ctx.mc_token)
    
    # Build example based on kind
    if ctx.kind == "catalog":
        example = f'"{ctx.keyword_catalog}"'
    elif ctx.kind == "look":
        example = f'"{ctx.keyword_look} {ctx.start_param or "CODE"}"'
    else:
        example = f'"{ctx.keyword_product} {ctx.start_param or "CODE"}"'
    
    return f"""💬 TEMPLATE B — Keyword DM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use for: Direct message keyword triggers
Text input: REQUIRED (user's message)

TRIGGER:
• Type: Direct Message
• Condition: starts with keyword
• Example: {example}

FLOW:
1. Set sb_channel = {ctx.channel}
2. External Request → resolve
3. Send Message with button

BODY (copy):
{body}

⚠️ Replace INCOMING_TEXT with ManyChat's
   variable for incoming message text.
   (Select from dropdown in ManyChat UI)

HEADERS:
• Content-Type: application/json
• X-MC-Token: {token}

URL: {ctx.mc_resolve_url}"""


def render_fields(ctx: ManyChatContext) -> str:
    """Custom Fields section."""
    return """🧩 CUSTOM FIELDS
━━━━━━━━━━━━━━━━━
Create these in ManyChat (Type: Text):

┌─────────────────┬──────┐
│ Field           │ Type │
├─────────────────┼──────┤
│ sb_channel      │ Text │
│ sb_content_ref  │ Text │
│ sb_last_url     │ Text │
│ sb_tg_url       │ Text │
│ sb_reply_text   │ Text │
└─────────────────┴──────┘

All fields use "sb_" prefix for consistency."""


def render_trigger(ctx: ManyChatContext) -> str:
    """Trigger Setup section (mode-aware)."""
    if ctx.mode == "2":
        return f"""🧭 TRIGGER SETUP (Mode 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Choose trigger type:
• Post/Reel comment trigger
• Story reply trigger
• Instagram Comment Growth Tool

Pre-fill fields:
• sb_channel = {ctx.channel}
• sb_content_ref = {ctx.content_ref}"""
    
    elif ctx.mode == "1":
        # Build keyword example
        if ctx.kind == "catalog":
            kw_example = ctx.keyword_catalog
        elif ctx.kind == "look":
            kw_example = f"{ctx.keyword_look} {ctx.start_param or 'CODE'}"
        else:
            kw_example = f"{ctx.keyword_product} {ctx.start_param or 'CODE'}"
        
        return f"""🧭 TRIGGER SETUP (Mode 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trigger: Direct Message
Condition: message starts with keyword

User sends: "{kw_example}"

Pre-fill:
• sb_channel = {ctx.channel}
• sb_content_ref = (leave empty)"""
    
    else:
        return f"""🧭 TRIGGER SETUP
━━━━━━━━━━━━━━━━━
Mode 2 (Post/Story):
• Use comment or story reply trigger
• Pre-fill sb_channel = {ctx.channel}
• Pre-fill sb_content_ref = {ctx.content_ref}

Mode 1 (Keyword DM):
• Use Direct Message trigger
• Condition: starts with keyword
• Pre-fill sb_channel = {ctx.channel}"""


def render_request(ctx: ManyChatContext) -> str:
    """External Request section."""
    token = get_safe_token(ctx.mc_token)
    body_a = '{"channel":"{{sb_channel}}","content_ref":"{{sb_content_ref}}","text":""}'
    body_b = '{"channel":"{{sb_channel}}","content_ref":"","text":"INCOMING_TEXT"}'
    
    return f"""🌐 EXTERNAL REQUEST
━━━━━━━━━━━━━━━━━━━━━
URL: {ctx.mc_resolve_url}
Method: POST

HEADERS:
• Content-Type: application/json
• X-MC-Token: {token}

BODY (Mode 2 - Post/Story):
{body_a}

BODY (Mode 1 - Keyword DM):
{body_b}

⚠️ Mode 1: Replace INCOMING_TEXT with
   ManyChat's message variable."""


def render_mapping(ctx: ManyChatContext) -> str:
    """Response Mapping section."""
    return """🧾 MAP RESPONSE TO FIELDS
━━━━━━━━━━━━━━━━━━━━━━━━━━
Plain style (most UIs):
• sb_last_url    ←  url
• sb_tg_url      ←  tg_url
• sb_reply_text  ←  reply_text

JSONPath style (if required):
• sb_last_url    ←  $.url
• sb_tg_url      ←  $.tg_url
• sb_reply_text  ←  $.reply_text

💡 Use JSONPath if ManyChat mapping UI
   shows field picker dropdown."""


def render_send(ctx: ManyChatContext) -> str:
    """Send Message section."""
    return """✉️ SEND MESSAGE
━━━━━━━━━━━━━━━━
Text: {{sb_reply_text}}
Button: "Открыть товар" → {{sb_tg_url}}

URL RECOMMENDATIONS:
┌─────────────────┬────────────────┐
│ Use Case        │ Field          │
├─────────────────┼────────────────┤
│ DM button       │ sb_tg_url      │
│ Public/tracking │ sb_last_url    │
└─────────────────┴────────────────┘

⚠️ If user never started bot,
   they must press Start first."""


def render_keywords(ctx: ManyChatContext) -> str:
    """Keywords/Notes section."""
    def fmt(name: str, value: str, default: str) -> str:
        if value == default:
            return f"• {name}: {value} (default)"
        return f"• {name}: {value} (custom)"
    
    return f"""⚙️ KEYWORDS & NOTES
━━━━━━━━━━━━━━━━━━━━━
Configured keywords:
{fmt("KEYWORD_PRODUCT", ctx.keyword_product, "BUY")}
{fmt("KEYWORD_LOOK", ctx.keyword_look, "LOOK")}
{fmt("KEYWORD_CATALOG", ctx.keyword_catalog, "CAT")}

⚠️ IMPORTANT:
LOOK payload prefix in SIS is configurable via WIZARD_LOOK_PREFIX.
Changing KEYWORD_LOOK affects user input only.

Strict mode (require keyword): {ctx.resolve_require_keyword}
LOOK prefix: {ctx.look_prefix}

URL: {ctx.url}
TG:  {ctx.tg_url}"""


# ============= Keyboards =============

def build_pack_keyboard(ctx: ManyChatContext, slug: str) -> dict:
    """Build keyboard for pack summary with section buttons."""
    mode = ctx.mode
    
    # Template A/B labels based on mode relevance
    tpl_a_label = "📋 Template A" if mode != "1" else "📋 Template A (opt)"
    tpl_b_label = "💬 Template B" if mode != "2" else "💬 Template B (opt)"
    
    return {
        "inline_keyboard": [
            [
                {"text": tpl_a_label, "callback_data": f"mc:tpl_a:{slug}"},
                {"text": tpl_b_label, "callback_data": f"mc:tpl_b:{slug}"},
            ],
            [
                {"text": "🧩 Fields", "callback_data": f"mc:fields:{slug}"},
                {"text": "🌐 Request", "callback_data": f"mc:request:{slug}"},
            ],
            [
                {"text": "🧭 Trigger", "callback_data": f"mc:trigger:{slug}"},
                {"text": "🧾 Mapping", "callback_data": f"mc:mapping:{slug}"},
            ],
            [
                {"text": "✉️ Send Msg", "callback_data": f"mc:send:{slug}"},
                {"text": "⚙️ Keywords", "callback_data": f"mc:keywords:{slug}"},
            ],
            [
                {"text": "◀ Back", "callback_data": "camp:snippet:back"},
                {"text": "🏠 Home", "callback_data": "act:clean"},
            ],
        ]
    }


def build_section_keyboard(slug: str, current: Section) -> dict:
    """Build keyboard for section view with back + prev/next."""
    idx = SECTIONS_ORDER.index(current) if current in SECTIONS_ORDER else -1
    
    nav_row = []
    if idx > 0:
        prev_section = SECTIONS_ORDER[idx - 1]
        nav_row.append({"text": "⬅ Prev", "callback_data": f"mc:{prev_section}:{slug}"})
    
    if idx < len(SECTIONS_ORDER) - 1:
        next_section = SECTIONS_ORDER[idx + 1]
        nav_row.append({"text": "Next ➡", "callback_data": f"mc:{next_section}:{slug}"})
    
    rows = []
    if nav_row:
        rows.append(nav_row)
    
    rows.append([
        {"text": "◀ Back to Pack", "callback_data": f"mc:pack:{slug}"},
        {"text": "🏠 Home", "callback_data": "act:clean"},
    ])
    
    return {"inline_keyboard": rows}


# ============= Section Dispatcher =============

SECTION_RENDERERS = {
    "pack": render_pack_summary,
    "tpl_a": render_template_a,
    "tpl_b": render_template_b,
    "fields": render_fields,
    "trigger": render_trigger,
    "request": render_request,
    "mapping": render_mapping,
    "send": render_send,
    "keywords": render_keywords,
}


def render_section(ctx: ManyChatContext, section: Section) -> str:
    """Render any section by name."""
    renderer = SECTION_RENDERERS.get(section, render_pack_summary)
    return renderer(ctx)


def get_section_keyboard(ctx: ManyChatContext, section: Section, slug: str) -> dict:
    """Get appropriate keyboard for section."""
    if section == "pack":
        return build_pack_keyboard(ctx, slug)
    return build_section_keyboard(slug, section)

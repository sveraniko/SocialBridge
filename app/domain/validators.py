import re

SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
# Telegram start param only allows: A-Za-z0-9_- (no colon, no #)
START_PARAM_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
PRODUCT_CODE_RE = re.compile(r"^(?=.*\d)[A-Za-z0-9_-]{1,64}$")


def is_valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.fullmatch(slug))


def is_valid_start_param(value: str) -> bool:
    return bool(START_PARAM_RE.fullmatch(value))


def parse_start_param_from_text(text: str | None) -> str | None:
    if not text:
        return None
    # Safe chars only: A-Za-z0-9_-
    for token in re.findall(r"[A-Za-z0-9_\-]+", text):
        if token.startswith("LOOK_") and is_valid_start_param(token):
            return token
        if token.startswith("prod_") and is_valid_start_param(token):
            return token
        if PRODUCT_CODE_RE.fullmatch(token):
            return token
    return None


def parse_keyword_payload(
    text: str | None,
    *,
    keyword_product: str,
    keyword_look: str,
    keyword_catalog: str,
    case_sensitive: bool = False,
) -> tuple[str | None, str]:
    if not text:
        return None, "fallback_catalog"

    raw = text.strip()
    if not raw:
        return None, "fallback_catalog"
    parts = raw.split()
    if not parts:
        return None, "fallback_catalog"

    keyword = parts[0] if case_sensitive else parts[0].upper()
    kw_product = keyword_product if case_sensitive else keyword_product.upper()
    kw_look = keyword_look if case_sensitive else keyword_look.upper()
    kw_catalog = keyword_catalog if case_sensitive else keyword_catalog.upper()

    if keyword == kw_catalog and len(parts) == 1:
        return None, "fallback_catalog"

    if len(parts) < 2:
        return None, "fallback_catalog"

    code = parts[1].strip()
    if not is_valid_start_param(code):
        return None, "fallback_catalog"

    if keyword == kw_product:
        return code, "fallback_payload"

    if keyword == kw_look:
        # SIS uses safe auto-generated codes: LOOK_LK7X9M2P format
        if code.startswith("LOOK_"):
            return code, "fallback_payload"
        look_code = f"LOOK_{code}"
        if is_valid_start_param(look_code):
            return look_code, "fallback_payload"

    return None, "fallback_catalog"

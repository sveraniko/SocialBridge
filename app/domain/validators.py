import re

SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
START_PARAM_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
PRODUCT_CODE_RE = re.compile(r"^(?=.*\d)[A-Za-z0-9_-]{1,64}$")


def is_valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.fullmatch(slug))


def is_valid_start_param(value: str) -> bool:
    return bool(START_PARAM_RE.fullmatch(value))


def parse_start_param_from_text(text: str | None) -> str | None:
    if not text:
        return None
    for token in re.findall(r"[A-Za-z0-9_-]+", text):
        if token.startswith("LOOK_") and is_valid_start_param(token):
            return token
        if token.startswith("prod_") and is_valid_start_param(token):
            return token
        if PRODUCT_CODE_RE.fullmatch(token):
            return token
    return None

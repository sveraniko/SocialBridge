import re

START_PARAM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


def validate_start_param(kind: str, value: str | None) -> tuple[bool, str | None, str | None]:
    text = (value or "").strip()
    if kind == "catalog":
        return True, None, None
    if not text:
        return False, None, "Value is required."
    if not START_PARAM_RE.match(text):
        return False, None, "Use only letters, digits, _ or -, max 64 chars."
    if kind == "look" and not text.startswith("LOOK_"):
        return False, None, "Look code must start with LOOK_."
    return True, text, None


def validate_slug(value: str | None) -> tuple[bool, str | None, str | None]:
    text = (value or "").strip().lower()
    if not text:
        return False, None, "Slug is required."
    if not SLUG_RE.match(text):
        return False, None, "Slug: lowercase letters/digits/_/-, 3..64 chars."
    return True, text, None

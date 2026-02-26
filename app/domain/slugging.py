import re
from hashlib import sha256

from app.domain.validators import is_valid_slug

_SANITIZE_RE = re.compile(r"[^a-z0-9_-]+")


def _sanitize_slug_part(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.strip().lower()
    cleaned = _SANITIZE_RE.sub("_", lowered).strip("_-")
    return cleaned


def derive_slug(content_ref: str, start_param: str | None) -> str:
    tail = content_ref.rsplit(":", 1)[-1] if content_ref else ""
    candidate = _sanitize_slug_part(tail) or _sanitize_slug_part(start_param)
    if candidate and len(candidate) <= 64 and is_valid_slug(candidate):
        return candidate
    digest = sha256(content_ref.encode("utf-8")).hexdigest()[:10]
    return f"sb_{digest}"

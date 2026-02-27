from dataclasses import dataclass
from enum import Enum


class ResolveResult(str, Enum):
    HIT = "hit"
    FALLBACK_PAYLOAD = "fallback_payload"
    FALLBACK_CATALOG = "fallback_catalog"


@dataclass(slots=True)
class ResolveInput:
    channel: str
    content_ref: str | None
    text: str | None
    mc_contact_id: str | None
    mc_flow_id: str | None
    mc_trigger: str | None
    payload_min: dict


@dataclass(slots=True)
class ResolveOutput:
    reply_text: str
    url: str
    tg_url: str
    start_param: str | None
    slug: str
    tag: str | None
    result: ResolveResult

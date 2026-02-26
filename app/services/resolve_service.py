import time

from app.adapters.hashing import payload_hash
from app.adapters.shortlink import build_shortlink
from app.core.config import Settings
from app.domain.types import ResolveInput, ResolveOutput, ResolveResult
from app.domain.validators import parse_start_param_from_text
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository

HIT_TEXT = "Готово. Вот ссылка 👇"
CATALOG_TEXT = "Открыл каталог. Выберите товар 👇"


class ResolveService:
    def __init__(
        self,
        settings: Settings,
        content_repo: ContentMapRepository,
        inbound_repo: InboundEventRepository,
    ):
        self.settings = settings
        self.content_repo = content_repo
        self.inbound_repo = inbound_repo

    async def resolve(
        self,
        raw_payload: dict,
        data: ResolveInput,
        request_id: str | None,
        persist_inbound_event: bool = True,
    ) -> ResolveOutput:
        started = time.monotonic()
        start_param = None
        slug = "catalog"
        result = ResolveResult.FALLBACK_CATALOG
        tag = None

        if data.content_ref:
            mapped = await self.content_repo.find_active_by_channel_ref(data.channel, data.content_ref)
            if mapped:
                start_param = mapped.start_param
                slug = mapped.slug
                result = ResolveResult.HIT
                tag = f"{data.channel}|{data.content_ref}"

        if result == ResolveResult.FALLBACK_CATALOG:
            parsed = parse_start_param_from_text(data.text)
            if parsed:
                dynamic = await self.content_repo.get_or_create_dynamic_mapping(parsed)
                start_param = dynamic.start_param
                slug = dynamic.slug
                result = ResolveResult.FALLBACK_PAYLOAD

        reply_text = HIT_TEXT if result != ResolveResult.FALLBACK_CATALOG else CATALOG_TEXT
        output = ResolveOutput(
            reply_text=reply_text,
            url=build_shortlink(self.settings.BASE_URL, slug),
            start_param=start_param,
            slug=slug,
            tag=tag,
            result=result,
        )
        if persist_inbound_event:
            await self.inbound_repo.insert_dedup(
                {
                    "channel": data.channel,
                    "payload_hash": payload_hash(raw_payload),
                    "content_ref": data.content_ref,
                    "mc_contact_id": data.mc_contact_id,
                    "mc_flow_id": data.mc_flow_id,
                    "mc_trigger": data.mc_trigger,
                    "text_preview": (data.text or "")[:256] if self.settings.STORE_TEXT_PREVIEW else None,
                    "result": output.result.value,
                    "resolved_slug": output.slug,
                    "resolved_start_param": output.start_param,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "request_id": request_id,
                    "payload_min": data.payload_min,
                }
            )
        return output

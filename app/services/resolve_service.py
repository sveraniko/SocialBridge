import logging
import time
from dataclasses import dataclass

from app.adapters.deeplink import build_tg_deeplink
from app.adapters.hashing import payload_hash
from app.adapters.shortlink import build_shortlink
from app.core.config import Settings
from app.domain.types import ResolveInput, ResolveOutput, ResolveResult
from app.domain.validators import START_PARAM_RE, is_valid_start_param
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository

HIT_TEXT = "Готово. Вот ссылка 👇"
CATALOG_TEXT = "Открыл каталог. Выберите товар 👇"
ASK_CODE_TEXT = "Пришлите код из поста. Пример: LOOK LKHZLTQN или BUY BOIZMRJS."
ASK_KIND_TEXT = "Уточните формат: {look} <code> или {product} <code>."
ASK_AMBIGUOUS_TEXT = "Неясно, что открыть. Напишите {look} <code> или {product} <code>."
CATALOG_HINT_TEXT = "Вот каталог 👇"

NOISE_TOKENS = {
    "цена",
    "сколько",
    "прайс",
    "price",
    "cost",
    "buy",
    "look",
    "cat",
    "хочу",
    "купить",
    "придбати",
}

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParsedResolveText:
    code: str | None
    kind: str  # LOOK|PRODUCT|CATALOG|UNKNOWN
    ask: bool = False
    ask_text: str | None = None
    catalog_intent: bool = False


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
        reply_text = CATALOG_TEXT

        if data.content_ref:
            mapped = await self.content_repo.find_active_by_channel_ref(data.channel, data.content_ref)
            if mapped:
                start_param = mapped.start_param
                slug = mapped.slug
                result = ResolveResult.HIT
                tag = f"{data.channel}|{data.content_ref}"
                reply_text = HIT_TEXT

        if result == ResolveResult.FALLBACK_CATALOG:
            parsed = await self._parse_mode1_text(data.text)

            if parsed.catalog_intent:
                reply_text = CATALOG_HINT_TEXT
            elif parsed.ask:
                reply_text = parsed.ask_text or ASK_CODE_TEXT
            elif parsed.code:
                dynamic_count = await self.content_repo.count_dynamic_created_last_24h()
                if dynamic_count >= self.settings.DYNAMIC_MAPPING_MAX_PER_DAY:
                    logger.warning(
                        "Dynamic mapping daily limit reached; degrading to fallback_catalog",
                        extra={"dynamic_count_24h": dynamic_count, "limit": self.settings.DYNAMIC_MAPPING_MAX_PER_DAY},
                    )
                else:
                    dynamic = await self.content_repo.get_or_create_dynamic_mapping(parsed.code)
                    start_param = dynamic.start_param
                    slug = dynamic.slug
                    result = ResolveResult.FALLBACK_PAYLOAD
                    reply_text = HIT_TEXT
            else:
                reply_text = ASK_CODE_TEXT

        output = ResolveOutput(
            reply_text=reply_text,
            url=build_shortlink(self.settings.BASE_URL, slug),
            tg_url=build_tg_deeplink(self.settings.SIS_BOT_USERNAME, start_param),
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

    async def _parse_mode1_text(self, text: str | None) -> ParsedResolveText:
        raw = " ".join((text or "").strip().split())
        if not raw:
            return ParsedResolveText(code=None, kind="UNKNOWN", ask=True, ask_text=ASK_CODE_TEXT)

        tokens_original = raw.split(" ")
        tokens_cmp = tokens_original if self.settings.KEYWORD_CASE_SENSITIVE else [t.lower() for t in tokens_original]
        product_keywords = self._normalize_keywords(self.settings.keyword_product_list)
        look_keywords = self._normalize_keywords(self.settings.keyword_look_list)
        catalog_keywords = self._normalize_keywords(self.settings.keyword_catalog_list)

        kind = "UNKNOWN"
        if any(token in catalog_keywords for token in tokens_cmp):
            return ParsedResolveText(code=None, kind="CATALOG", catalog_intent=True)
        if any(token in look_keywords for token in tokens_cmp):
            kind = "LOOK"
        elif any(token in product_keywords for token in tokens_cmp):
            kind = "PRODUCT"

        code = self._extract_code_candidate(tokens_original, tokens_cmp)
        if not code:
            return ParsedResolveText(code=None, kind=kind, ask=True, ask_text=ASK_CODE_TEXT)

        if not is_valid_start_param(code):
            return ParsedResolveText(code=None, kind=kind, ask=True, ask_text=ASK_CODE_TEXT)

        if kind == "LOOK":
            start_param = code if code.startswith(self.settings.LOOK_PREFIX) else f"{self.settings.LOOK_PREFIX}{code}"
            if not is_valid_start_param(start_param):
                return ParsedResolveText(code=None, kind=kind, ask=True, ask_text=ASK_CODE_TEXT)
            return ParsedResolveText(code=start_param, kind=kind)

        if kind == "PRODUCT":
            return ParsedResolveText(code=code, kind=kind)

        if code.startswith(self.settings.LOOK_PREFIX):
            return ParsedResolveText(code=code, kind="LOOK")

        if not self.settings.RESOLVE_ALLOW_CODE_ONLY:
            return ParsedResolveText(
                code=None,
                kind=kind,
                ask=True,
                ask_text=ASK_KIND_TEXT.format(
                    look=self.settings.keyword_look_list[0],
                    product=self.settings.keyword_product_list[0],
                ),
            )

        if self.settings.RESOLVE_REQUIRE_KEYWORD:
            return ParsedResolveText(
                code=None,
                kind=kind,
                ask=True,
                ask_text=ASK_KIND_TEXT.format(
                    look=self.settings.keyword_look_list[0],
                    product=self.settings.keyword_product_list[0],
                ),
            )

        product_exists = await self.content_repo.exists_active_start_param(code)
        look_code = f"{self.settings.LOOK_PREFIX}{code}"
        look_exists = await self.content_repo.exists_active_start_param(look_code)

        if product_exists and look_exists:
            if self.settings.RESOLVE_AMBIGUOUS_POLICY == "prefer_look":
                return ParsedResolveText(code=look_code, kind="LOOK")
            if self.settings.RESOLVE_AMBIGUOUS_POLICY == "ask":
                return ParsedResolveText(
                    code=None,
                    kind=kind,
                    ask=True,
                    ask_text=ASK_AMBIGUOUS_TEXT.format(
                        look=self.settings.keyword_look_list[0],
                        product=self.settings.keyword_product_list[0],
                    ),
                )
            return ParsedResolveText(code=code, kind="PRODUCT")

        if look_exists:
            return ParsedResolveText(code=look_code, kind="LOOK")
        if product_exists:
            return ParsedResolveText(code=code, kind="PRODUCT")
        return ParsedResolveText(code=code, kind="PRODUCT")

    def _normalize_keywords(self, keywords: list[str]) -> set[str]:
        if self.settings.KEYWORD_CASE_SENSITIVE:
            return {k for k in keywords if k}
        return {k.lower() for k in keywords if k}

    def _extract_code_candidate(self, tokens_original: list[str], tokens_cmp: list[str]) -> str | None:
        code_like = []
        look_prefix_cmp = self.settings.LOOK_PREFIX if self.settings.KEYWORD_CASE_SENSITIVE else self.settings.LOOK_PREFIX.lower()
        keyword_noise = {
            *self._normalize_keywords(self.settings.keyword_product_list),
            *self._normalize_keywords(self.settings.keyword_look_list),
            *self._normalize_keywords(self.settings.keyword_catalog_list),
            *(NOISE_TOKENS if not self.settings.KEYWORD_CASE_SENSITIVE else set()),
        }

        for token_original, token_cmp in zip(tokens_original, tokens_cmp, strict=False):
            if token_cmp.startswith(look_prefix_cmp) and is_valid_start_param(token_original):
                return token_original
            if START_PARAM_RE.fullmatch(token_original) and 5 <= len(token_original) <= 64 and token_cmp not in keyword_noise:
                code_like.append(token_original)

        return code_like[-1] if code_like else None

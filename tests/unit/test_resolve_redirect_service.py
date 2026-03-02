import pytest

from app.core.config import Settings
from app.domain.types import ResolveInput
from app.services.redirect_service import RedirectService
from app.services.resolve_service import ResolveService
from tests.fakes.repos_fake import FakeClickEventRepo, FakeContentMapRepo, FakeInboundEventRepo


@pytest.mark.asyncio
async def test_resolve_hit():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="bot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    inbound = FakeInboundEventRepo()
    service = ResolveService(settings, FakeContentMapRepo(), inbound)
    out = await service.resolve(
        {"channel": "ig", "content_ref": "campaign:hit"},
        ResolveInput("ig", "campaign:hit", None, None, None, None, {"channel": "ig"}),
        request_id="r1",
    )
    assert out.result.value == "hit"
    assert inbound.saved["resolved_slug"] == "dress1"


@pytest.mark.asyncio
async def test_resolve_fallback_payload_creates_dynamic_mapping_and_redirect_works():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    content_repo = FakeContentMapRepo()
    inbound = FakeInboundEventRepo()
    click = FakeClickEventRepo()
    resolve_service = ResolveService(settings, content_repo, inbound)
    redirect_service = RedirectService(settings, content_repo, click)

    out = await resolve_service.resolve(
        {"channel": "ig", "text": "LOOK LKHZLTQN"},
        ResolveInput("ig", None, "LOOK LKHZLTQN", None, None, None, {"channel": "ig"}),
        request_id="r2",
    )

    assert out.result.value == "fallback_payload"
    assert out.slug == "dyn_look_lkhzltqn"
    assert out.url.endswith("/t/dyn_look_lkhzltqn")

    target = await redirect_service.resolve_redirect(out.slug, "ua", None, None)
    assert target == "https://t.me/sisbot?start=LOOK_LKHZLTQN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("LOOK LKHZLTQN", "LOOK_LKHZLTQN"),
        ("BUY BOIZMRJS", "BOIZMRJS"),
        ("CAT", None),
        ("LOOK_LKHZLTQN", "LOOK_LKHZLTQN"),
    ],
)
async def test_mode1_parsing_common_paths(text: str, expected: str | None):
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    service = ResolveService(settings, FakeContentMapRepo(), FakeInboundEventRepo())
    out = await service.resolve(
        {"channel": "ig", "text": text},
        ResolveInput("ig", None, text, None, None, None, {"channel": "ig"}),
        request_id="r3",
    )
    assert out.start_param == expected


@pytest.mark.asyncio
async def test_marketing_phrase_can_map_to_look_when_keyword_configured():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
        KEYWORDS_LOOK="LOOK,хочу",
    )
    service = ResolveService(settings, FakeContentMapRepo(), FakeInboundEventRepo())
    out = await service.resolve(
        {"channel": "ig", "text": "хочу LKHZLTQN"},
        ResolveInput("ig", None, "хочу LKHZLTQN", None, None, None, {"channel": "ig"}),
        request_id="r4",
    )
    assert out.start_param == "LOOK_LKHZLTQN"


@pytest.mark.asyncio
async def test_code_only_uses_ambiguity_policy_ask():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
        RESOLVE_AMBIGUOUS_POLICY="ask",
    )
    repo = FakeContentMapRepo()
    repo.active_start_params = {"LKHZLTQN", "LOOK_LKHZLTQN"}
    service = ResolveService(settings, repo, FakeInboundEventRepo())
    out = await service.resolve(
        {"channel": "ig", "text": "LKHZLTQN"},
        ResolveInput("ig", None, "LKHZLTQN", None, None, None, {"channel": "ig"}),
        request_id="r5",
    )
    assert out.result.value == "fallback_catalog"
    assert out.start_param is None
    assert "LOOK" in out.reply_text and "BUY" in out.reply_text


@pytest.mark.asyncio
async def test_code_only_can_require_keyword():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
        RESOLVE_REQUIRE_KEYWORD=True,
    )
    service = ResolveService(settings, FakeContentMapRepo(), FakeInboundEventRepo())
    out = await service.resolve(
        {"channel": "ig", "text": "LKHZLTQN"},
        ResolveInput("ig", None, "LKHZLTQN", None, None, None, {"channel": "ig"}),
        request_id="r6",
    )
    assert out.result.value == "fallback_catalog"
    assert out.start_param is None


@pytest.mark.asyncio
async def test_invalid_characters_are_ignored_for_safe_code_extraction():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    service = ResolveService(settings, FakeContentMapRepo(), FakeInboundEventRepo())
    out = await service.resolve(
        {"channel": "ig", "text": "LOOK LKHZ:LTQN #oops BOIZMRJS"},
        ResolveInput("ig", None, "LOOK LKHZ:LTQN #oops BOIZMRJS", None, None, None, {"channel": "ig"}),
        request_id="r7",
    )
    assert out.start_param == "LOOK_BOIZMRJS"


@pytest.mark.asyncio
async def test_redirect_miss_goes_catalog():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    click = FakeClickEventRepo()
    service = RedirectService(settings, FakeContentMapRepo(), click)
    target = await service.resolve_redirect("unknown", "ua", None, None)
    assert target == "https://t.me/sisbot"
    assert click.saved["meta"]["miss"] is True

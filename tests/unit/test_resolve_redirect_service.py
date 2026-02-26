from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.domain.types import ResolveInput
from app.services.redirect_service import RedirectService
from app.services.resolve_service import ResolveService


class FakeContentRepo:
    def __init__(self):
        self.dynamic = {}

    async def find_active_by_channel_ref(self, channel, content_ref):
        if content_ref == "campaign:hit":
            return SimpleNamespace(start_param="DRESS1", slug="dress1")
        return None

    async def get_or_create_dynamic_mapping(self, start_param):
        slug = f"dyn_{start_param.lower()}"
        obj = SimpleNamespace(start_param=start_param, slug=slug)
        self.dynamic[slug] = obj
        return obj

    async def find_active_by_slug(self, slug):
        if slug == "dress1":
            return SimpleNamespace(id="1", start_param="DRESS1")
        if slug in self.dynamic:
            return SimpleNamespace(id="2", start_param=self.dynamic[slug].start_param)
        return None


class FakeInboundRepo:
    def __init__(self):
        self.saved = None

    async def insert_dedup(self, payload):
        self.saved = payload


class FakeClickRepo:
    def __init__(self):
        self.saved = None

    async def create(self, payload):
        self.saved = payload


@pytest.mark.asyncio
async def test_resolve_hit():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="bot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    inbound = FakeInboundRepo()
    service = ResolveService(settings, FakeContentRepo(), inbound)
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
    content_repo = FakeContentRepo()
    inbound = FakeInboundRepo()
    click = FakeClickRepo()
    resolve_service = ResolveService(settings, content_repo, inbound)
    redirect_service = RedirectService(settings, content_repo, click)

    out = await resolve_service.resolve(
        {"channel": "ig", "text": "LOOK_SPRING2026"},
        ResolveInput("ig", None, "LOOK_SPRING2026", None, None, None, {"channel": "ig"}),
        request_id="r2",
    )

    assert out.result.value == "fallback_payload"
    assert out.slug == "dyn_look_spring2026"
    assert out.url.endswith("/t/dyn_look_spring2026")

    target = await redirect_service.resolve_redirect(out.slug, "ua", None, None)
    assert target == "https://t.me/sisbot?start=LOOK_SPRING2026"


@pytest.mark.asyncio
async def test_redirect_miss_goes_catalog():
    settings = Settings(
        BASE_URL="http://localhost:8000",
        SIS_BOT_USERNAME="sisbot",
        DATABASE_URL="postgresql+asyncpg://x",
        ADMIN_TOKEN="a",
        MC_TOKEN="m",
    )
    click = FakeClickRepo()
    service = RedirectService(settings, FakeContentRepo(), click)
    target = await service.resolve_redirect("unknown", "ua", None, None)
    assert target == "https://t.me/sisbot"
    assert click.saved["meta"]["miss"] is True

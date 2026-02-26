from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.domain.types import ResolveInput
from app.services.redirect_service import RedirectService
from app.services.resolve_service import ResolveService


class FakeContentRepo:
    async def find_active_by_channel_ref(self, channel, content_ref):
        if content_ref == "campaign:hit":
            return SimpleNamespace(start_param="DRESS1", slug="dress1")
        return None

    async def find_active_by_slug(self, slug):
        if slug == "dress1":
            return SimpleNamespace(id="1", start_param="DRESS1")
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

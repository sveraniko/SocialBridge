from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import app
from app.repositories.click_event_repo import ClickEventRepository
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository


class FakeSession:
    async def execute(self, *args, **kwargs):
        class R:
            rowcount = 1

            def scalar_one_or_none(self):
                return None

            def scalars(self):
                class S:
                    def all(self):
                        return []

                return S()

            def scalar_one(self):
                return 0

        return R()

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None

    def add(self, *_):
        return None


async def fake_db():
    yield FakeSession()


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_db_session] = fake_db

    async def fake_find(self, channel, content_ref):
        if content_ref == "campaign:dress001":
            return SimpleNamespace(start_param="DRESS001", slug="dress001")
        return None

    async def fake_find_slug(self, slug):
        if slug == "dress001":
            return SimpleNamespace(id="1", start_param="DRESS001")
        return None

    async def fake_insert(self, payload):
        return None

    async def fake_click(self, payload):
        return None

    monkeypatch.setattr(ContentMapRepository, "find_active_by_channel_ref", fake_find)
    monkeypatch.setattr(ContentMapRepository, "find_active_by_slug", fake_find_slug)
    monkeypatch.setattr(InboundEventRepository, "insert_dedup", fake_insert)
    monkeypatch.setattr(ClickEventRepository, "create", fake_click)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_resolve_hit(client):
    response = client.post("/v1/mc/resolve", json={"channel": "ig", "content_ref": "campaign:dress001"})
    assert response.status_code == 200
    assert response.json()["result"] == "hit"


def test_resolve_fallback_catalog(client):
    response = client.post("/v1/mc/resolve", json={"channel": "ig"})
    assert response.status_code == 200
    assert response.json()["result"] == "fallback_catalog"


def test_redirect(client):
    response = client.get("/t/dress001", follow_redirects=False)
    assert response.status_code == 302
    assert "t.me" in response.headers["location"]

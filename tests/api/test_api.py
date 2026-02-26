from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

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

    def __init__(self):
        self.rollback_calls = 0

    async def rollback(self):
        self.rollback_calls += 1
        return None

    def add(self, *_):
        return None

    @asynccontextmanager
    async def begin(self):
        yield self

    @asynccontextmanager
    async def begin_nested(self):
        yield self


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

    async def fake_dynamic(self, start_param):
        return SimpleNamespace(start_param=start_param, slug=f"dyn_{start_param.lower()}")

    monkeypatch.setattr(ContentMapRepository, "find_active_by_channel_ref", fake_find)
    monkeypatch.setattr(ContentMapRepository, "find_active_by_slug", fake_find_slug)
    monkeypatch.setattr(ContentMapRepository, "get_or_create_dynamic_mapping", fake_dynamic)
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


def test_admin_import_partial_success(client, monkeypatch):
    state = {"written": []}

    async def fake_find_by_channel_ref(self, channel, content_ref):
        if content_ref == "exists":
            return SimpleNamespace(channel=channel, content_ref=content_ref)
        return None

    async def fake_upsert(self, payload):
        if payload["slug"] == "taken":
            raise IntegrityError("stmt", "params", "orig")
        state["written"].append(payload["content_ref"])
        return SimpleNamespace(
            id="1",
            channel=payload["channel"],
            content_ref=payload["content_ref"],
            start_param=payload.get("start_param"),
            slug=payload["slug"],
            is_active=True,
            meta=payload.get("meta", {}),
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(ContentMapRepository, "find_by_channel_ref", fake_find_by_channel_ref)
    monkeypatch.setattr(ContentMapRepository, "upsert", fake_upsert)

    response = client.post(
        "/v1/admin/content-map/import",
        json=[
            {"channel": "ig", "content_ref": "ok1", "slug": "ok1", "start_param": "LOOK_A"},
            {"channel": "ig", "content_ref": "bad", "slug": "taken", "start_param": "LOOK_B"},
            {"channel": "ig", "content_ref": "ok2", "slug": "ok2", "start_param": "LOOK_C"},
        ],
        headers={"X-Admin-Token": "change-me-admin"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 2
    assert response.json()["failed"] == 1
    assert response.json()["errors"][0]["code"] == "conflict"
    assert state["written"] == ["ok1", "ok2"]



def test_admin_import_does_not_call_manual_rollback(client, monkeypatch):
    session = FakeSession()

    async def tracked_db():
        yield session

    app.dependency_overrides[get_db_session] = tracked_db

    async def fake_find_by_channel_ref(self, channel, content_ref):
        return None

    async def fake_upsert(self, payload):
        if payload["slug"] == "taken":
            raise IntegrityError("stmt", "params", "orig")
        return SimpleNamespace(
            id="1",
            channel=payload["channel"],
            content_ref=payload["content_ref"],
            start_param=payload.get("start_param"),
            slug=payload["slug"],
            is_active=True,
            meta=payload.get("meta", {}),
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(ContentMapRepository, "find_by_channel_ref", fake_find_by_channel_ref)
    monkeypatch.setattr(ContentMapRepository, "upsert", fake_upsert)

    response = client.post(
        "/v1/admin/content-map/import",
        json=[
            {"channel": "ig", "content_ref": "ok1", "slug": "ok1", "start_param": "LOOK_A"},
            {"channel": "ig", "content_ref": "bad", "slug": "taken", "start_param": "LOOK_B"},
            {"channel": "ig", "content_ref": "ok2", "slug": "ok2", "start_param": "LOOK_C"},
        ],
        headers={"X-Admin-Token": "change-me-admin"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 2
    assert response.json()["failed"] == 1
    assert session.rollback_calls == 0


def test_admin_disable_missing_payload_keys_returns_400(client):
    response = client.post(
        "/v1/admin/content-map/disable",
        json={"channel": "ig"},
        headers={"X-Admin-Token": "change-me-admin"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"

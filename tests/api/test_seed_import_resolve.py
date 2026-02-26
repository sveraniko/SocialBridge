import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import app
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository


class FakeSession:
    async def commit(self):
        return None

    async def rollback(self):
        return None

    def add(self, *_):
        return None


async def fake_db():
    yield FakeSession()


def test_seed_min_import_and_resolve_catalog(monkeypatch):
    state: dict[tuple[str, str], dict] = {}

    async def fake_find_by_channel_ref(self, channel, content_ref):
        item = state.get((channel, content_ref))
        return SimpleNamespace(**item) if item else None

    async def fake_upsert(self, payload):
        item = {
            "channel": payload["channel"],
            "content_ref": payload["content_ref"],
            "start_param": payload.get("start_param"),
            "slug": payload["slug"],
            "is_active": payload.get("is_active", True),
            "meta": payload.get("meta", {}),
            "id": "1",
            "created_at": None,
            "updated_at": None,
        }
        state[(item["channel"], item["content_ref"])] = item
        return SimpleNamespace(**item)

    async def fake_find_active_by_channel_ref(self, channel, content_ref):
        item = state.get((channel, content_ref))
        if item and item.get("is_active", True):
            return SimpleNamespace(start_param=item["start_param"], slug=item["slug"])
        return None

    async def fake_insert_dedup(self, payload):
        return None

    monkeypatch.setattr(ContentMapRepository, "find_by_channel_ref", fake_find_by_channel_ref)
    monkeypatch.setattr(ContentMapRepository, "upsert", fake_upsert)
    monkeypatch.setattr(ContentMapRepository, "find_active_by_channel_ref", fake_find_active_by_channel_ref)
    monkeypatch.setattr(InboundEventRepository, "insert_dedup", fake_insert_dedup)

    app.dependency_overrides[get_db_session] = fake_db
    seed_payload = json.loads(Path("seed/content_map_seed_min.json").read_text(encoding="utf-8"))

    with TestClient(app) as client:
        import_response = client.post(
            "/v1/admin/content-map/import",
            json=seed_payload,
            headers={"X-Admin-Token": "change-me-admin"},
        )
        assert import_response.status_code == 200
        assert import_response.json()["failed"] == 0

        resolve_response = client.post(
            "/v1/mc/resolve",
            json={"channel": "ig", "content_ref": "campaign:catalog", "text": "hi"},
        )
        assert resolve_response.status_code == 200
        assert resolve_response.json()["url"].endswith("/t/catalog")

    app.dependency_overrides.clear()

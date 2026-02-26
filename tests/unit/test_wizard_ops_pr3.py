import json

import pytest

from wizard_bot.handlers.create_link import handle_wizard_callback
from wizard_bot.handlers.ops_tools import parse_import_payload


class FakeRedis:
    def __init__(self):
        self.db = {}

    async def get(self, key):
        return self.db.get(key)

    async def set(self, key, value):
        self.db[key] = value


class FakePanel:
    async def render(self, chat_id: int, text: str, keyboard: dict):
        return 1


class FakeSettings:
    WIZARD_DEFAULT_CHANNEL = "ig"
    WIZARD_PUBLIC_BASE_URL = "http://localhost:8000"


class FakeSBClient:
    def __init__(self):
        self.last_upsert = None

    async def upsert_content_map(self, **kwargs):
        self.last_upsert = kwargs
        return {"slug": "dress001"}


@pytest.mark.parametrize(
    "payload,expected_len",
    [
        (b'[{"channel":"ig","content_ref":"campaign:a"}]', 1),
        (b'{"items":[{"channel":"ig","content_ref":"campaign:b"}]}', 1),
    ],
)
def test_parse_import_payload_accepts_array_and_wrapper(payload, expected_len):
    parsed = parse_import_payload(payload)
    assert isinstance(parsed, list)
    assert len(parsed) == expected_len


@pytest.mark.asyncio
async def test_wizard_create_upsert_sets_is_active_true():
    redis = FakeRedis()
    panel = FakePanel()
    sb_client = FakeSBClient()
    chat_id = 77
    redis.db[f"wiz:chat:{chat_id}:session"] = json.dumps(
        {
            "step": "confirm",
            "history": ["mode", "kind", "start_param", "slug_choice", "confirm"],
            "mode": "0",
            "kind": "product",
            "start_param": "DRESS001",
            "slug": "dress001",
        }
    )

    handled = await handle_wizard_callback("wiz:create", chat_id, panel, redis, sb_client, FakeSettings())

    assert handled is True
    assert sb_client.last_upsert is not None
    assert sb_client.last_upsert["is_active"] is True

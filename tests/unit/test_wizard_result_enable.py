import json

import pytest

from wizard_bot.handlers.create_link import handle_wizard_callback
from tests.fakes.socialbridge_admin_client_fake import FakeSocialBridgeAdminClient


class FakeRedis:
    def __init__(self):
        self.db = {}

    async def get(self, key):
        return self.db.get(key)

    async def set(self, key, value):
        self.db[key] = value


class FakePanel:
    def __init__(self):
        self.text = None
        self.keyboard = None

    async def render(self, chat_id: int, text: str, keyboard: dict):
        self.text = text
        self.keyboard = keyboard


class FakeSettings:
    WIZARD_DEFAULT_CHANNEL = "ig"
    WIZARD_PUBLIC_BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_result_enable_calls_upsert_with_is_active_true_when_initially_inactive():
    redis = FakeRedis()
    panel = FakePanel()
    sb_client = FakeSocialBridgeAdminClient(items=[
        {
            "channel": "ig",
            "content_ref": "campaign:dress001",
            "start_param": "DRESS001",
            "slug": "dress001",
            "is_active": False,
            "meta": {"wizard": True},
        }
    ])
    chat_id = 900
    redis.db[f"wiz:chat:{chat_id}:session"] = json.dumps(
        {
            "step": "result",
            "history": ["mode", "kind", "start_param", "slug_choice", "confirm", "result"],
            "mode": "0",
            "kind": "product",
            "start_param": "DRESS001",
            "slug": "dress001",
            "campaign_key": "dress001",
            "created_item": sb_client.items[0],
        }
    )

    await handle_wizard_callback("wiz:enable", chat_id, panel, redis, sb_client, FakeSettings())

    assert len(sb_client.upsert_calls) == 1
    assert sb_client.upsert_calls[0]["is_active"] is True
    assert sb_client.upsert_calls[0]["start_param"] == "DRESS001"


@pytest.mark.asyncio
async def test_result_panel_reflects_state_and_status_line_after_toggle():
    redis = FakeRedis()
    panel = FakePanel()
    sb_client = FakeSocialBridgeAdminClient(items=[
        {
            "channel": "ig",
            "content_ref": "campaign:dress001",
            "start_param": "DRESS001",
            "slug": "dress001",
            "is_active": False,
            "meta": {"wizard": True},
        }
    ])
    chat_id = 901
    redis.db[f"wiz:chat:{chat_id}:session"] = json.dumps(
        {
            "step": "result",
            "history": ["mode", "kind", "start_param", "slug_choice", "confirm", "result"],
            "mode": "0",
            "kind": "product",
            "start_param": "DRESS001",
            "slug": "dress001",
            "campaign_key": "dress001",
            "created_item": sb_client.items[0],
        }
    )

    await handle_wizard_callback("wiz:enable", chat_id, panel, redis, sb_client, FakeSettings())
    button_rows = panel.keyboard["inline_keyboard"]
    assert button_rows[0][0]["text"] == "Disable campaign"
    assert "✅ Campaign enabled" in panel.text

    await handle_wizard_callback("wiz:disable", chat_id, panel, redis, sb_client, FakeSettings())
    button_rows = panel.keyboard["inline_keyboard"]
    assert button_rows[0][0]["text"] == "Enable campaign"
    assert "⛔ Campaign disabled" in panel.text

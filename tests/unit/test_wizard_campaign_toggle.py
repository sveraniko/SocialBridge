import json

import pytest

from wizard_bot.handlers.menu import handle_callback


class FakeRedis:
    def __init__(self):
        self.db = {}

    async def get(self, key):
        return self.db.get(key)

    async def set(self, key, value):
        self.db[key] = value

    async def sadd(self, key, value):
        self.db.setdefault(key, set()).add(value)


class FakePanel:
    async def render(self, chat_id: int, text: str, keyboard: dict):
        return 1


class FakeTelegram:
    pass


class FakeMessenger:
    async def send_document(self, **kwargs):
        return 1


class FakeSBClient:
    def __init__(self):
        self.disable_calls = []
        self.enable_calls = []

    async def disable_content_map(self, channel: str, content_ref: str):
        self.disable_calls.append((channel, content_ref))
        return {"result": "disabled"}

    async def upsert_content_map(self, **kwargs):
        self.enable_calls.append(kwargs)
        return {"is_active": True, "slug": kwargs.get("slug")}


class FakeSettings:
    WIZARD_CAMPAIGNS_PAGE_LIMIT = 50
    WIZARD_DEFAULT_CHANNEL = "ig"
    WIZARD_PUBLIC_BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_campaign_toggle_calls_disable_and_enable_clients():
    redis = FakeRedis()
    panel = FakePanel()
    telegram = FakeTelegram()
    messenger = FakeMessenger()
    sb_client = FakeSBClient()
    chat_id = 11
    redis.db[f"wiz:chat:{chat_id}:session"] = json.dumps(
        {
            "history": ["mode"],
            "campaign_view": {
                "channel": "ig",
                "content_ref": "campaign:dress001",
                "start_param": "DRESS001",
                "slug": "dress001",
                "meta": {"wizard": True},
                "is_active": True,
            },
        }
    )

    await handle_callback("camp:disable", chat_id, panel, redis, telegram, messenger, sb_client, FakeSettings())
    await handle_callback("camp:enable", chat_id, panel, redis, telegram, messenger, sb_client, FakeSettings())

    assert sb_client.disable_calls == [("ig", "campaign:dress001")]
    assert len(sb_client.enable_calls) == 1
    assert sb_client.enable_calls[0]["is_active"] is True

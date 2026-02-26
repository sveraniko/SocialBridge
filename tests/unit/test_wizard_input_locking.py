import asyncio
import json

import pytest

from wizard_bot.handlers.create_link import handle_wizard_input
from wizard_bot.main import _handle_document_message
from wizard_bot.wizard.state import session_key


class FakeRedis:
    def __init__(self):
        self.db: dict[str, str] = {}

    async def get(self, key):
        return self.db.get(key)

    async def set(self, key, value, nx=False, px=None, ex=None):
        if nx and key in self.db:
            return False
        self.db[key] = value
        return True

    async def delete(self, key):
        self.db.pop(key, None)


class FakePanel:
    def __init__(self):
        self.render_calls = 0

    async def render(self, chat_id: int, text: str, keyboard: dict):
        self.render_calls += 1
        return 1


class FakeTelegram:
    async def get_file(self, file_id: str):
        return "path/to/import.json"

    async def download_file(self, file_path: str):
        return b'[{"channel":"telegram","content_ref":"campaign:a"}]'


class FakeSBClient:
    def __init__(self):
        self.import_calls = 0

    async def import_content_map(self, items: list[dict]):
        self.import_calls += 1
        return {"imported": len(items), "created": len(items), "updated": 0}


@pytest.mark.asyncio
async def test_awaiting_input_lock_allows_single_consumer():
    redis = FakeRedis()
    panel = FakePanel()
    chat_id = 101
    redis.db[session_key(chat_id)] = json.dumps(
        {
            "step": "start_param",
            "history": ["mode", "kind", "start_param"],
            "kind": "product",
            "awaiting_input": "start_param",
        }
    )

    first, second = await asyncio.gather(
        handle_wizard_input(chat_id, "AAA111", panel, redis, telegram=None),
        handle_wizard_input(chat_id, "AAA111", panel, redis, telegram=None),
    )

    assert sorted([first, second]) == [False, True]
    saved = json.loads(redis.db[session_key(chat_id)])
    assert saved["awaiting_input"] is None
    assert saved["start_param"] == "AAA111"
    assert panel.render_calls == 1


@pytest.mark.asyncio
async def test_document_import_deduplicates_same_file_id():
    redis = FakeRedis()
    panel = FakePanel()
    telegram = FakeTelegram()
    sb_client = FakeSBClient()
    chat_id = 202
    redis.db[session_key(chat_id)] = json.dumps(
        {
            "step": "import",
            "history": ["mode", "import"],
            "awaiting_document": "import_content_map",
        }
    )
    message = {"document": {"file_id": "same-file-id"}}

    consumed_first = await _handle_document_message(chat_id, message, panel, redis, telegram, sb_client)

    restored = json.loads(redis.db[session_key(chat_id)])
    restored["awaiting_document"] = "import_content_map"
    redis.db[session_key(chat_id)] = json.dumps(restored)

    consumed_second = await _handle_document_message(chat_id, message, panel, redis, telegram, sb_client)

    assert consumed_first is True
    assert consumed_second is True
    assert sb_client.import_calls == 1

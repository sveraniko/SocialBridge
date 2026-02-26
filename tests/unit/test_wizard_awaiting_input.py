import pytest

from wizard_bot.handlers.create_link import handle_wizard_input


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


@pytest.mark.asyncio
async def test_awaiting_input_consumes_start_param():
    redis = FakeRedis()
    panel = FakePanel()
    chat_id = 99
    redis.db[f"wiz:chat:{chat_id}:session"] = (
        '{"step":"start_param","history":["mode","kind","start_param"],"kind":"product","awaiting_input":"start_param"}'
    )

    consumed = await handle_wizard_input(chat_id, "DRESS001", panel, redis, telegram=None)

    assert consumed is True
    saved = redis.db[f"wiz:chat:{chat_id}:session"]
    assert "DRESS001" in saved
    assert '"slug_choice"' in saved

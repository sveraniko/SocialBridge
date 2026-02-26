import pytest

from wizard_bot.ui.messenger import Messenger
from wizard_bot.ui.registry import list_messages


class FakeRedis:
    def __init__(self):
        self.sets: dict[str, set[str]] = {}

    async def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(str(value))

    async def smembers(self, key):
        return self.sets.get(key, set())


class FakeTelegram:
    async def send_message(self, **kwargs):
        return {"message_id": 111}

    async def send_document(self, **kwargs):
        return {"message_id": 222}


@pytest.mark.asyncio
async def test_send_text_registers_message_id():
    redis = FakeRedis()
    messenger = Messenger(redis, FakeTelegram())

    message_id = await messenger.send_text(chat_id=5, text="hello")

    assert message_id == 111
    assert await list_messages(redis, 5) == [111]


@pytest.mark.asyncio
async def test_send_document_registers_message_id():
    redis = FakeRedis()
    messenger = Messenger(redis, FakeTelegram())

    message_id = await messenger.send_document(chat_id=5, filename="backup.json", bytes_or_file=b"{}")

    assert message_id == 222
    assert await list_messages(redis, 5) == [222]

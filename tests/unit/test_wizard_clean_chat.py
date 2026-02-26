import pytest

from wizard_bot.nav.stack import stack_key
from wizard_bot.storage.redis import active_panel_key, chat_messages_key
from wizard_bot.ui.clean_chat import ChatCleaner
from wizard_bot.wizard.state import session_key


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        self.values[key] = str(value)

    async def smembers(self, key):
        return self.sets.get(key, set())

    async def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(str(value))

    async def srem(self, key, value):
        if key in self.sets:
            self.sets[key].discard(str(value))

    async def delete(self, key):
        self.values.pop(key, None)
        self.sets.pop(key, None)


class FakeTelegram:
    def __init__(self):
        self.deleted: list[int] = []

    async def delete_message(self, chat_id: int, message_id: int):
        if message_id == 12:
            raise RuntimeError("message not found")
        self.deleted.append(message_id)


@pytest.mark.asyncio
async def test_clean_chat_deletes_registered_messages_and_clears_keys():
    redis = FakeRedis()
    telegram = FakeTelegram()
    cleaner = ChatCleaner(redis, telegram)
    chat_id = 55

    await redis.set(active_panel_key(chat_id), 10)
    await redis.sadd(chat_messages_key(chat_id), 11)
    await redis.sadd(chat_messages_key(chat_id), 12)
    await redis.set(session_key(chat_id), "{\"awaiting_input\":\"x\"}")
    await redis.set(stack_key(chat_id), '["MAIN", "CREATE"]')

    await cleaner.clean(chat_id)

    assert telegram.deleted == [10, 11]
    assert await redis.get(active_panel_key(chat_id)) is None
    assert await redis.smembers(chat_messages_key(chat_id)) == set()
    assert await redis.get(session_key(chat_id)) is None
    assert await redis.get(stack_key(chat_id)) is None

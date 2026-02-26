from __future__ import annotations

from wizard_bot.storage.redis import active_panel_key, chat_messages_key
from wizard_bot.wizard.state import session_key


def normalize_message_ids(values: list[str]) -> list[int]:
    cleaned: set[int] = set()
    for value in values:
        if isinstance(value, str) and value.isdigit():
            cleaned.add(int(value))
    return sorted(cleaned)


class ChatCleaner:
    def __init__(self, redis, telegram_client):
        self.redis = redis
        self.telegram_client = telegram_client

    async def clean(self, chat_id: int) -> None:
        key = chat_messages_key(chat_id)
        registered = await self.redis.smembers(key)
        for message_id in normalize_message_ids(list(registered)):
            try:
                await self.telegram_client.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                continue
        await self.redis.delete(key)
        await self.redis.delete(active_panel_key(chat_id))
        await self.redis.delete(session_key(chat_id))

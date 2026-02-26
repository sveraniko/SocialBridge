from __future__ import annotations

from wizard_bot.nav.stack import stack_key
from wizard_bot.storage.redis import active_panel_key
from wizard_bot.ui.registry import clear_messages, list_messages
from wizard_bot.wizard.state import session_key


class ChatCleaner:
    def __init__(self, redis, telegram_client):
        self.redis = redis
        self.telegram_client = telegram_client

    async def clean(self, chat_id: int) -> None:
        active_key = active_panel_key(chat_id)
        active_message_id = await self.redis.get(active_key)
        if active_message_id and str(active_message_id).isdigit():
            try:
                await self.telegram_client.delete_message(chat_id=chat_id, message_id=int(active_message_id))
            except Exception:
                pass

        for message_id in await list_messages(self.redis, chat_id):
            try:
                await self.telegram_client.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                continue

        await clear_messages(self.redis, chat_id)
        await self.redis.delete(active_key)
        await self.redis.delete(session_key(chat_id))
        await self.redis.delete(stack_key(chat_id))

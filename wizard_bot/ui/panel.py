from __future__ import annotations

from wizard_bot.storage.redis import active_panel_key
from wizard_bot.ui.messenger import Messenger
from wizard_bot.ui.registry import register_message


class PanelManager:
    def __init__(self, redis, telegram_client):
        self.redis = redis
        self.telegram_client = telegram_client
        self.messenger = Messenger(redis, telegram_client)

    async def render(self, chat_id: int, text: str, keyboard: dict) -> int:
        active_key = active_panel_key(chat_id)
        current_message_id = await self.redis.get(active_key)
        if current_message_id and str(current_message_id).isdigit():
            message_id_int = int(current_message_id)
            try:
                await self.telegram_client.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id_int,
                    text=text,
                    reply_markup=keyboard,
                )
                await register_message(self.redis, chat_id, message_id_int)
                return message_id_int
            except Exception:
                pass

        new_message_id = await self.messenger.send_text(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            register=True,
        )
        await self.redis.set(active_key, new_message_id)

        if current_message_id and str(current_message_id).isdigit() and int(current_message_id) != new_message_id:
            try:
                await self.telegram_client.delete_message(chat_id=chat_id, message_id=int(current_message_id))
            except Exception:
                pass

        return new_message_id

    async def register_message(self, chat_id: int, message_id: int) -> None:
        await register_message(self.redis, chat_id, message_id)

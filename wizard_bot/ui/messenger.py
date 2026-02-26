from __future__ import annotations

from wizard_bot.ui.registry import register_message


class Messenger:
    def __init__(self, redis, telegram_client):
        self.redis = redis
        self.telegram_client = telegram_client

    async def send_text(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
        disable_web_page_preview: bool = True,
        reply_markup: dict | None = None,
        register: bool = True,
    ) -> int:
        sent = await self.telegram_client.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
        )
        message_id = int(sent.get("message_id", 0))
        if register and message_id:
            await register_message(self.redis, chat_id, message_id)
        return message_id

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        bytes_or_file: bytes,
        *,
        caption: str | None = None,
        register: bool = True,
    ) -> int:
        sent = await self.telegram_client.send_document(
            chat_id=chat_id,
            filename=filename,
            content=bytes_or_file,
            caption=caption,
        )
        message_id = int(sent.get("message_id", 0))
        if register and message_id:
            await register_message(self.redis, chat_id, message_id)
        return message_id

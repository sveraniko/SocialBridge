from wizard_bot.storage.redis import chat_messages_key


async def register_message(redis, chat_id: int, message_id: int) -> None:
    await redis.sadd(chat_messages_key(chat_id), str(message_id))

from wizard_bot.storage.redis import chat_messages_key


async def register_message(redis, chat_id: int, message_id: int) -> None:
    await redis.sadd(chat_messages_key(chat_id), str(message_id))


async def unregister_message(redis, chat_id: int, message_id: int) -> None:
    await redis.srem(chat_messages_key(chat_id), str(message_id))


async def list_messages(redis, chat_id: int) -> list[int]:
    values = await redis.smembers(chat_messages_key(chat_id))
    cleaned: set[int] = set()
    for value in values:
        string_value = str(value)
        if string_value.isdigit():
            cleaned.add(int(string_value))
    return sorted(cleaned)


async def clear_messages(redis, chat_id: int) -> None:
    await redis.delete(chat_messages_key(chat_id))

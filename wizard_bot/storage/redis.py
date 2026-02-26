from functools import lru_cache

from redis.asyncio import Redis

from wizard_bot.config import get_settings


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.WIZARD_REDIS_URL, decode_responses=True)


def chat_messages_key(chat_id: int) -> str:
    return f"wiz:chat:{chat_id}:msgs"


def active_panel_key(chat_id: int) -> str:
    return f"wiz:chat:{chat_id}:panel:active"

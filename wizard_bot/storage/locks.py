from __future__ import annotations

import secrets


class ChatLock:
    def __init__(self, redis, chat_id: int, ttl_ms: int = 4000):
        self.redis = redis
        self.chat_id = chat_id
        self.ttl_ms = ttl_ms
        self._token = secrets.token_hex(8)
        self._key = f"wiz:chat:{chat_id}:lock"
        self.acquired = False

    async def __aenter__(self) -> "ChatLock":
        self.acquired = bool(await self.redis.set(self._key, self._token, nx=True, px=self.ttl_ms))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if not self.acquired:
            return
        current = await self.redis.get(self._key)
        if current == self._token:
            await self.redis.delete(self._key)

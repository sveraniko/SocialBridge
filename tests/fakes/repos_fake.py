from __future__ import annotations

from types import SimpleNamespace


class FakeContentMapRepo:
    def __init__(self):
        self.dynamic: dict[str, SimpleNamespace] = {}

    async def find_active_by_channel_ref(self, channel: str, content_ref: str):
        if content_ref == "campaign:hit":
            return SimpleNamespace(start_param="DRESS1", slug="dress1")
        return None

    async def get_or_create_dynamic_mapping(self, start_param: str):
        slug = f"dyn_{start_param.lower()}"
        obj = SimpleNamespace(start_param=start_param, slug=slug)
        self.dynamic[slug] = obj
        return obj

    async def count_dynamic_created_last_24h(self) -> int:
        return 0

    async def find_active_by_slug(self, slug: str):
        if slug == "dress1":
            return SimpleNamespace(id="1", start_param="DRESS1")
        if slug in self.dynamic:
            return SimpleNamespace(id="2", start_param=self.dynamic[slug].start_param)
        return None


class FakeInboundEventRepo:
    def __init__(self):
        self.saved = None

    async def insert_dedup(self, payload: dict) -> None:
        self.saved = payload


class FakeClickEventRepo:
    def __init__(self):
        self.saved = None

    async def create(self, payload: dict) -> None:
        self.saved = payload

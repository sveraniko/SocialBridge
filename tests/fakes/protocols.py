from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SocialBridgeAdminClientProtocol(Protocol):
    async def upsert_content_map(
        self,
        channel: str,
        content_ref: str,
        start_param: str | None,
        slug: str | None = None,
        meta: dict | None = None,
        is_active: bool | None = None,
    ) -> dict: ...

    async def disable_content_map(self, channel: str, content_ref: str) -> dict: ...

    async def resolve_preview(self, channel: str, content_ref: str, text: str | None = None) -> dict: ...

    async def export_content_map(self, channel: str | None = None, is_active: bool | None = None) -> list[dict]: ...

    async def import_content_map(self, items: list[dict]) -> dict: ...

    async def list_content_map(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: str | None = None,
        is_active: bool | None = True,
    ) -> dict: ...


@runtime_checkable
class ContentMapRepoProtocol(Protocol):
    async def find_active_by_channel_ref(self, channel: str, content_ref: str): ...

    async def get_or_create_dynamic_mapping(self, start_param: str): ...

    async def count_dynamic_created_last_24h(self) -> int: ...

    async def find_active_by_slug(self, slug: str): ...


@runtime_checkable
class InboundEventRepoProtocol(Protocol):
    async def insert_dedup(self, payload: dict) -> None: ...


@runtime_checkable
class ClickEventRepoProtocol(Protocol):
    async def create(self, payload: dict) -> None: ...

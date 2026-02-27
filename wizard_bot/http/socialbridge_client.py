from __future__ import annotations

import httpx


class SocialBridgeClient:
    def __init__(self, base_url: str, admin_token: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=20,
            headers={"X-Admin-Token": admin_token},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()

    async def ready(self) -> dict:
        response = await self._client.get("/ready")
        response.raise_for_status()
        return response.json()

    async def list_content_map(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: str | None = None,
        is_active: bool | None = True,
    ) -> dict:
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if channel:
            params["channel"] = channel
        if is_active is not None:
            params["is_active"] = is_active
        response = await self._client.get("/v1/admin/content-map", params=params)
        response.raise_for_status()
        return response.json()

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: str | None = None,
        is_active: bool | None = True,
    ) -> list[dict]:
        payload = await self.list_content_map(limit=limit, offset=offset, channel=channel, is_active=is_active)
        return payload.get("items", [])

    async def export_content_map(self, channel: str | None = None, is_active: bool | None = None) -> list[dict]:
        params: dict[str, object] = {}
        if channel:
            params["channel"] = channel
        if is_active is not None:
            params["is_active"] = is_active
        response = await self._client.get("/v1/admin/content-map/export", params=params)
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, list) else []

    async def import_content_map(self, items: list[dict]) -> dict:
        response = await self._client.post("/v1/admin/content-map/import", json=items)
        response.raise_for_status()
        return response.json()

    async def upsert_content_map(
        self,
        channel: str,
        content_ref: str,
        start_param: str | None,
        slug: str | None = None,
        meta: dict | None = None,
        is_active: bool | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "channel": channel,
            "content_ref": content_ref,
            "start_param": start_param,
            "meta": meta or {},
        }
        if slug:
            payload["slug"] = slug
        if is_active is not None:
            payload["is_active"] = is_active
        response = await self._client.post("/v1/admin/content-map/upsert", json=payload)
        response.raise_for_status()
        return response.json().get("item", {})

    async def disable_content_map(self, channel: str, content_ref: str) -> dict:
        response = await self._client.post(
            "/v1/admin/content-map/disable",
            json={"channel": channel, "content_ref": content_ref},
        )
        response.raise_for_status()
        return response.json()

    async def delete_content_map(self, channel: str, content_ref: str) -> dict:
        response = await self._client.post(
            "/v1/admin/content-map/delete",
            json={"channel": channel, "content_ref": content_ref},
        )
        response.raise_for_status()
        return response.json()

    async def resolve_preview(self, channel: str, content_ref: str, text: str | None = None) -> dict:
        payload: dict[str, object] = {"channel": channel, "content_ref": content_ref}
        if text is not None:
            payload["text"] = text
        response = await self._client.post("/v1/admin/resolve-preview", json=payload)
        response.raise_for_status()
        return response.json()

    async def stats_overview(self, hours: int = 24) -> dict:
        response = await self._client.get("/v1/admin/stats/overview", params={"hours": hours})
        response.raise_for_status()
        return response.json()

    async def stats_top(self, hours: int = 24, limit: int = 20) -> dict:
        response = await self._client.get("/v1/admin/stats/top", params={"hours": hours, "limit": limit})
        response.raise_for_status()
        return response.json()

    async def stats_campaign(self, content_ref: str, hours: int = 24) -> dict:
        response = await self._client.get("/v1/admin/stats/campaign", params={"content_ref": content_ref, "hours": hours})
        response.raise_for_status()
        return response.json()

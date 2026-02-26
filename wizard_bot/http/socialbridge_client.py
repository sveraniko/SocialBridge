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

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: str | None = None,
        is_active: bool | None = True,
    ) -> list[dict]:
        params: dict[str, object] = {"limit": limit, "offset": offset}
        if channel:
            params["channel"] = channel
        if is_active is not None:
            params["is_active"] = is_active
        response = await self._client.get("/v1/admin/content-map", params=params)
        response.raise_for_status()
        return response.json().get("items", [])

    async def upsert_content_map(
        self,
        channel: str,
        content_ref: str,
        start_param: str | None,
        slug: str | None = None,
        meta: dict | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "channel": channel,
            "content_ref": content_ref,
            "start_param": start_param,
            "meta": meta or {},
        }
        if slug:
            payload["slug"] = slug
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

    async def resolve_preview(self, channel: str, content_ref: str, text: str | None = None) -> dict:
        payload: dict[str, object] = {"channel": channel, "content_ref": content_ref}
        if text is not None:
            payload["text"] = text
        response = await self._client.post("/v1/admin/resolve-preview", json=payload)
        response.raise_for_status()
        return response.json()

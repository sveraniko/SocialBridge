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

    async def list_campaigns(self, limit: int = 50) -> list[dict]:
        response = await self._client.get("/v1/admin/content-map", params={"limit": limit})
        response.raise_for_status()
        return response.json().get("items", [])

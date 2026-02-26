from __future__ import annotations

from copy import deepcopy


class FakeSocialBridgeAdminClient:
    def __init__(self, items: list[dict] | None = None):
        self.items = deepcopy(items) if items is not None else []
        self.upsert_calls: list[dict] = []
        self.disable_calls: list[tuple[str, str]] = []
        self.resolve_preview_calls: list[dict] = []
        self.export_calls: list[dict] = []
        self.import_calls: list[list[dict]] = []
        self.list_calls: list[dict] = []

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
            "slug": slug,
            "meta": meta or {},
        }
        if is_active is not None:
            payload["is_active"] = is_active
        self.upsert_calls.append(payload)

        updated = None
        for item in self.items:
            if item["channel"] == channel and item["content_ref"] == content_ref:
                item.update(payload)
                updated = item
                break

        if updated is None:
            updated = {
                "channel": channel,
                "content_ref": content_ref,
                "start_param": start_param,
                "slug": slug or content_ref.replace(":", "-"),
                "meta": meta or {},
                "is_active": is_active if is_active is not None else True,
            }
            self.items.append(updated)

        return deepcopy(updated)

    async def disable_content_map(self, channel: str, content_ref: str) -> dict:
        self.disable_calls.append((channel, content_ref))
        for item in self.items:
            if item["channel"] == channel and item["content_ref"] == content_ref:
                item["is_active"] = False
                break
        return {"result": "disabled"}

    async def resolve_preview(self, channel: str, content_ref: str, text: str | None = None) -> dict:
        payload = {"channel": channel, "content_ref": content_ref, "text": text}
        self.resolve_preview_calls.append(payload)
        for item in self.items:
            if item["channel"] == channel and item["content_ref"] == content_ref and item.get("is_active", True):
                return {
                    "result": "hit",
                    "slug": item.get("slug"),
                    "start_param": item.get("start_param"),
                    "url": f"http://localhost:8000/t/{item.get('slug')}",
                }
        return {"result": "fallback_catalog", "slug": "catalog", "start_param": None, "url": "http://localhost:8000/t/catalog"}

    async def export_content_map(self, channel: str | None = None, is_active: bool | None = None) -> list[dict]:
        self.export_calls.append({"channel": channel, "is_active": is_active})
        return deepcopy(self._filter_items(channel, is_active))

    async def import_content_map(self, items: list[dict]) -> dict:
        self.import_calls.append(deepcopy(items))
        created = 0
        updated = 0
        for item in items:
            existing = next(
                (
                    x
                    for x in self.items
                    if x["channel"] == item["channel"] and x["content_ref"] == item["content_ref"]
                ),
                None,
            )
            if existing:
                existing.update(item)
                updated += 1
            else:
                self.items.append(deepcopy(item))
                created += 1
        return {"imported": len(items), "created": created, "updated": updated, "errors": []}

    async def list_content_map(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: str | None = None,
        is_active: bool | None = True,
    ) -> dict:
        self.list_calls.append({"limit": limit, "offset": offset, "channel": channel, "is_active": is_active})
        filtered = self._filter_items(channel, is_active)
        page = filtered[offset : offset + limit]
        return {"items": deepcopy(page), "total": len(filtered), "limit": limit, "offset": offset}

    def _filter_items(self, channel: str | None, is_active: bool | None) -> list[dict]:
        filtered = self.items
        if channel is not None:
            filtered = [item for item in filtered if item.get("channel") == channel]
        if is_active is not None:
            filtered = [item for item in filtered if item.get("is_active", True) is is_active]
        return filtered

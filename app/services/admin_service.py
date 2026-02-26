from app.domain.validators import is_valid_slug, is_valid_start_param
from app.repositories.content_map_repo import ContentMapRepository


class AdminService:
    def __init__(self, content_repo: ContentMapRepository):
        self.content_repo = content_repo

    async def list_content_map(self, channel, is_active, limit, offset):
        items, total = await self.content_repo.list_items(channel, is_active, limit, offset)
        return {"items": [self.serialize(x) for x in items], "total": total, "limit": limit, "offset": offset}

    async def upsert(self, payload: dict):
        self._validate(payload)
        obj = await self.content_repo.upsert(payload)
        return self.serialize(obj)

    async def import_item(self, item: dict) -> str:
        self._validate(item)
        exists = await self.content_repo.find_by_channel_ref(item["channel"], item["content_ref"])
        await self.content_repo.upsert(item)
        return "updated" if exists else "created"

    async def export(self):
        return [self.serialize(x) for x in await self.content_repo.export()]

    async def disable(self, channel: str, content_ref: str) -> bool:
        return await self.content_repo.disable(channel, content_ref)

    @staticmethod
    def serialize(obj):
        return {
            "id": str(obj.id),
            "channel": obj.channel,
            "content_ref": obj.content_ref,
            "start_param": obj.start_param,
            "slug": obj.slug,
            "is_active": obj.is_active,
            "meta": obj.meta,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }

    @staticmethod
    def _validate(payload: dict) -> None:
        channel = payload.get("channel")
        content_ref = payload.get("content_ref")
        slug = payload.get("slug")
        start_param = payload.get("start_param")
        if not isinstance(channel, str) or not channel:
            raise ValueError("channel is required")
        if not isinstance(content_ref, str) or not content_ref:
            raise ValueError("content_ref is required")
        if not isinstance(slug, str) or not is_valid_slug(slug):
            raise ValueError("invalid slug")
        if start_param is not None and not is_valid_start_param(start_param):
            raise ValueError("invalid start_param")


from app.domain.slugging import derive_slug
from app.domain.validators import is_valid_slug, is_valid_start_param
from app.repositories.content_map_repo import ContentMapRepository


class AdminValidationError(ValueError):
    def __init__(self, message: str, field: str | None = None, code: str = "bad_request"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code


class AdminService:
    def __init__(self, content_repo: ContentMapRepository):
        self.content_repo = content_repo

    async def list_content_map(self, channel, is_active, limit, offset):
        items, total = await self.content_repo.list_items(channel, is_active, limit, offset)
        return {"items": [self.serialize(x) for x in items], "total": total, "limit": limit, "offset": offset}

    async def upsert(self, payload: dict):
        clean_payload = self._validate(payload)
        exists = await self.content_repo.find_by_channel_ref(clean_payload["channel"], clean_payload["content_ref"])
        obj = await self.content_repo.upsert(clean_payload)
        result = "updated" if exists else "created"
        return self.serialize(obj), result

    async def import_item(self, item: dict) -> str:
        clean_item = self._validate(item)
        exists = await self.content_repo.find_by_channel_ref(clean_item["channel"], clean_item["content_ref"])
        await self.content_repo.upsert(clean_item)
        return "updated" if exists else "created"

    async def export(self, channel: str | None = None, is_active: bool | None = None):
        return [self.serialize(x) for x in await self.content_repo.export(channel=channel, is_active=is_active)]

    async def disable(self, channel: str, content_ref: str) -> bool:
        return await self.content_repo.disable(channel, content_ref)

    async def delete(self, channel: str, content_ref: str) -> bool:
        return await self.content_repo.delete(channel, content_ref)

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
    def _validate(payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise AdminValidationError("item must be an object")
        clean_payload = dict(payload)

        # Strip server-managed fields that must not be set on insert/update
        for key in ("id", "created_at", "updated_at"):
            clean_payload.pop(key, None)
        channel = clean_payload.get("channel")
        if not isinstance(channel, str) or not channel:
            raise AdminValidationError("channel is required", field="channel")

        content_ref = clean_payload.get("content_ref")
        if not isinstance(content_ref, str) or not content_ref:
            raise AdminValidationError("content_ref is required", field="content_ref")

        start_param = clean_payload.get("start_param")
        if start_param is not None and not is_valid_start_param(start_param):
            raise AdminValidationError("invalid start_param", field="start_param")

        slug = clean_payload.get("slug")
        if slug is None or (isinstance(slug, str) and not slug.strip()):
            clean_payload["slug"] = derive_slug(content_ref=content_ref, start_param=start_param)
        elif not isinstance(slug, str) or not is_valid_slug(slug):
            raise AdminValidationError("invalid slug", field="slug")

        if not is_valid_slug(clean_payload["slug"]):
            raise AdminValidationError("invalid slug", field="slug")

        return clean_payload

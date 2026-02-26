from sqlalchemy.exc import IntegrityError

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

    async def import_items(self, items: list[dict]) -> dict:
        created = 0
        updated = 0
        failed = 0
        errors = []
        for idx, item in enumerate(items):
            try:
                exists = await self.content_repo.find_by_channel_ref(item["channel"], item["content_ref"])
                await self.upsert(item)
                updated += 1 if exists else 0
                created += 0 if exists else 1
            except (ValueError, KeyError, IntegrityError) as exc:
                failed += 1
                errors.append({"index": idx, "error": str(exc)})
        return {"created": created, "updated": updated, "failed": failed, "errors": errors}

    async def export(self):
        return [self.serialize(x) for x in await self.content_repo.export()]

    async def disable(self, channel: str, content_ref: str) -> bool:
        return await self.content_repo.disable(channel, content_ref)

    @staticmethod
    def serialize(obj):
        return {
            "channel": obj.channel,
            "content_ref": obj.content_ref,
            "start_param": obj.start_param,
            "slug": obj.slug,
            "is_active": obj.is_active,
            "meta": obj.meta,
        }

    @staticmethod
    def _validate(payload: dict) -> None:
        slug = payload.get("slug")
        start_param = payload.get("start_param")
        if not isinstance(slug, str) or not is_valid_slug(slug):
            raise ValueError("invalid slug")
        if start_param is not None and not is_valid_start_param(start_param):
            raise ValueError("invalid start_param")

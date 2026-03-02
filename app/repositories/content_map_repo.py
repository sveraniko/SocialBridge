from hashlib import sha256

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content_map import ContentMap


class ContentMapRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_active_by_channel_ref(self, channel: str, content_ref: str) -> ContentMap | None:
        q = select(ContentMap).where(
            ContentMap.channel == channel,
            ContentMap.content_ref == content_ref,
            ContentMap.is_active.is_(True),
        )
        return (await self.session.execute(q)).scalar_one_or_none()

    async def find_active_by_slug(self, slug: str) -> ContentMap | None:
        q = select(ContentMap).where(ContentMap.slug == slug, ContentMap.is_active.is_(True))
        return (await self.session.execute(q)).scalar_one_or_none()
    async def exists_active_start_param(self, start_param: str) -> bool:
        q = select(ContentMap.id).where(ContentMap.start_param == start_param, ContentMap.is_active.is_(True)).limit(1)
        return (await self.session.execute(q)).scalar_one_or_none() is not None


    async def list_items(self, channel: str | None, is_active: bool | None, limit: int, offset: int):
        base_filter = []
        if channel:
            base_filter.append(ContentMap.channel == channel)
        if is_active is not None:
            base_filter.append(ContentMap.is_active.is_(is_active))

        q = select(ContentMap).where(*base_filter).order_by(ContentMap.updated_at.desc()).limit(limit).offset(offset)
        c = select(func.count()).select_from(ContentMap).where(*base_filter)
        rows = (await self.session.execute(q)).scalars().all()
        total = (await self.session.execute(c)).scalar_one()
        return rows, total

    async def upsert(self, payload: dict) -> ContentMap:
        existing = await self.find_by_channel_ref(payload["channel"], payload["content_ref"])
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        obj = ContentMap(**payload)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def find_by_channel_ref(self, channel: str, content_ref: str) -> ContentMap | None:
        q = select(ContentMap).where(ContentMap.channel == channel, ContentMap.content_ref == content_ref)
        return (await self.session.execute(q)).scalar_one_or_none()

    async def disable(self, channel: str, content_ref: str) -> bool:
        obj = await self.find_by_channel_ref(channel, content_ref)
        if not obj:
            return False
        obj.is_active = False
        await self.session.flush()
        await self.session.refresh(obj)
        return True

    async def delete(self, channel: str, content_ref: str) -> bool:
        obj = await self.find_by_channel_ref(channel, content_ref)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def export(self, channel: str | None = None, is_active: bool | None = None) -> list[ContentMap]:
        filters = []
        if channel:
            filters.append(ContentMap.channel == channel)
        if is_active is not None:
            filters.append(ContentMap.is_active.is_(is_active))
        q = select(ContentMap).where(*filters).order_by(ContentMap.channel, ContentMap.content_ref)
        return (await self.session.execute(q)).scalars().all()

    async def count_dynamic_created_last_24h(self) -> int:
        q = text(
            """
            SELECT count(*)
            FROM sb_content_map
            WHERE channel = 'generic'
              AND content_ref LIKE 'dyn:%'
              AND coalesce((meta->>'dynamic')::boolean, false) = true
              AND created_at >= now() - interval '24 hours'
            """
        )
        return int((await self.session.execute(q)).scalar_one() or 0)

    async def get_or_create_dynamic_mapping(self, start_param: str) -> ContentMap:
        content_ref = f"dyn:{start_param}"
        existing = await self.find_by_channel_ref("generic", content_ref)
        if existing:
            return existing

        preferred_slug = f"dyn_{start_param.lower()}"
        slug = preferred_slug if len(preferred_slug) <= 64 else self._hashed_dynamic_slug(start_param)
        payload = {
            "channel": "generic",
            "content_ref": content_ref,
            "start_param": start_param,
            "slug": slug,
            "is_active": True,
            "meta": {"dynamic": True},
        }
        try:
            return await self.upsert(payload)
        except IntegrityError:
            await self.session.rollback()
            payload["slug"] = self._hashed_dynamic_slug(start_param)
            return await self.upsert(payload)

    @staticmethod
    def _hashed_dynamic_slug(start_param: str) -> str:
        digest = sha256(start_param.encode("utf-8")).hexdigest()[:10]
        return f"dyn_{digest}"

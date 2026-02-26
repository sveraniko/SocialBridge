from sqlalchemy import func, select
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

    async def list_items(self, channel: str | None, is_active: bool | None, limit: int, offset: int):
        q = select(ContentMap)
        c = select(func.count(ContentMap.id))
        if channel:
            q = q.where(ContentMap.channel == channel)
            c = c.where(ContentMap.channel == channel)
        if is_active is not None:
            q = q.where(ContentMap.is_active.is_(is_active))
            c = c.where(ContentMap.is_active.is_(is_active))
        q = q.order_by(ContentMap.updated_at.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(q)).scalars().all()
        total = (await self.session.execute(c)).scalar_one()
        return rows, total

    async def upsert(self, payload: dict) -> ContentMap:
        existing = await self.find_by_channel_ref(payload["channel"], payload["content_ref"])
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        obj = ContentMap(**payload)
        self.session.add(obj)
        await self.session.flush()
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
        return True

    async def export(self) -> list[ContentMap]:
        return (await self.session.execute(select(ContentMap).order_by(ContentMap.channel))).scalars().all()

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.click_event import ClickEvent


class ClickEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: dict) -> None:
        self.session.add(ClickEvent(**payload))
        await self.session.flush()

    async def delete_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(delete(ClickEvent).where(ClickEvent.created_at < cutoff))
        return result.rowcount or 0

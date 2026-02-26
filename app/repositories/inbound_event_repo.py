from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inbound_event import InboundEvent


class InboundEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_dedup(self, payload: dict) -> None:
        stmt = insert(InboundEvent).values(**payload)
        stmt = stmt.on_conflict_do_nothing(index_elements=["channel", "payload_hash"])
        await self.session.execute(stmt)

    async def delete_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(delete(InboundEvent).where(InboundEvent.created_at < cutoff))
        return result.rowcount or 0

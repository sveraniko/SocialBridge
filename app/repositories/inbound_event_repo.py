from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inbound_event import InboundEvent


class InboundEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_dedup(self, payload: dict) -> InboundEvent | None:
        """
        Insert InboundEvent with deduplication based on (channel, payload_hash).
        If a duplicate exists, returns None.
        """
        stmt = (
            insert(InboundEvent)
            .values(**payload)
            .on_conflict_do_nothing(constraint="uq_sb_inbound_event_channel_payload_hash")
            .returning(InboundEvent)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row

    async def delete_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(delete(InboundEvent).where(InboundEvent.created_at < cutoff))
        return result.rowcount or 0

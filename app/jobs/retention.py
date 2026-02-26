from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.config import get_settings
from app.db.models.click_event import ClickEvent
from app.db.models.inbound_event import InboundEvent
from app.db.session import SessionLocal


async def run_retention() -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    inbound_cutoff = now - timedelta(days=settings.RETENTION_INBOUND_DAYS)
    click_cutoff = now - timedelta(days=settings.RETENTION_CLICK_DAYS)
    async with SessionLocal() as session:
        inbound_deleted = (
            await session.execute(delete(InboundEvent).where(InboundEvent.created_at < inbound_cutoff))
        ).rowcount or 0
        click_deleted = (
            await session.execute(delete(ClickEvent).where(ClickEvent.created_at < click_cutoff))
        ).rowcount or 0
        await session.commit()
    return {"inbound_deleted": inbound_deleted, "click_deleted": click_deleted}


def main() -> None:
    import asyncio

    print(asyncio.run(run_retention()))


if __name__ == "__main__":
    main()

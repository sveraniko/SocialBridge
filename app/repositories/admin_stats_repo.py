from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.click_event import ClickEvent
from app.db.models.content_map import ContentMap
from app.db.models.inbound_event import InboundEvent


class AdminStatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _since(hours: int) -> datetime:
        return datetime.now(UTC) - timedelta(hours=hours)

    async def overview(self, hours: int) -> dict:
        since = self._since(hours)

        resolves_total_q = select(func.count(InboundEvent.id)).where(InboundEvent.created_at >= since)
        resolves_total = int((await self.session.execute(resolves_total_q)).scalar_one() or 0)

        resolves_by_result_q = (
            select(InboundEvent.result, func.count(InboundEvent.id))
            .where(InboundEvent.created_at >= since)
            .group_by(InboundEvent.result)
        )
        result_rows = (await self.session.execute(resolves_by_result_q)).all()
        resolves_by_result = {"hit": 0, "fallback_payload": 0, "fallback_catalog": 0}
        for result, total in result_rows:
            if result in resolves_by_result:
                resolves_by_result[result] = int(total or 0)

        clicks_total_q = select(func.count(ClickEvent.id)).where(ClickEvent.created_at >= since)
        clicks_total = int((await self.session.execute(clicks_total_q)).scalar_one() or 0)

        redirect_miss_q = (
            select(func.count(ClickEvent.id))
            .where(ClickEvent.created_at >= since)
            .where(func.coalesce(ClickEvent.meta["miss"].as_boolean(), False).is_(True))
        )
        redirect_miss_total = int((await self.session.execute(redirect_miss_q)).scalar_one() or 0)

        ctr_bridge = float(clicks_total / resolves_total) if resolves_total else 0.0

        return {
            "hours": hours,
            "resolves_total": resolves_total,
            "resolves_by_result": resolves_by_result,
            "clicks_total": clicks_total,
            "ctr_bridge": ctr_bridge,
            "redirect_miss_total": redirect_miss_total,
        }

    async def top_campaigns_by_clicks(self, hours: int, limit: int) -> list[dict]:
        since = self._since(hours)
        q = (
            select(ContentMap.content_ref, func.count(ClickEvent.id).label("clicks_total"))
            .select_from(ClickEvent)
            .join(ContentMap, ClickEvent.content_map_id == ContentMap.id, isouter=True)
            .where(ClickEvent.created_at >= since)
            .group_by(ContentMap.content_ref)
            .order_by(func.count(ClickEvent.id).desc(), ContentMap.content_ref.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(q)).all()
        return [
            {
                "content_ref": str(content_ref or "(unmapped)"),
                "clicks_total": int(clicks_total or 0),
            }
            for content_ref, clicks_total in rows
        ]

    async def top_campaigns_by_resolves(self, hours: int, limit: int) -> list[dict]:
        since = self._since(hours)
        campaign_ref = func.coalesce(InboundEvent.content_ref, InboundEvent.resolved_slug)
        q = (
            select(campaign_ref.label("content_ref"), func.count(InboundEvent.id).label("resolves_total"))
            .where(InboundEvent.created_at >= since)
            .group_by(campaign_ref)
            .order_by(func.count(InboundEvent.id).desc(), campaign_ref.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(q)).all()
        return [
            {
                "content_ref": str(content_ref or "(unknown)"),
                "resolves_total": int(resolves_total or 0),
            }
            for content_ref, resolves_total in rows
        ]

    async def campaign_stats(self, content_ref: str, hours: int) -> dict:
        since = self._since(hours)

        resolves_q = (
            select(func.count(InboundEvent.id))
            .where(InboundEvent.created_at >= since)
            .where(
                (InboundEvent.content_ref == content_ref)
                | (InboundEvent.resolved_slug == content_ref)
            )
        )
        resolves_total = int((await self.session.execute(resolves_q)).scalar_one() or 0)

        click_q = (
            select(func.count(ClickEvent.id))
            .select_from(ClickEvent)
            .join(ContentMap, ClickEvent.content_map_id == ContentMap.id, isouter=True)
            .where(ClickEvent.created_at >= since)
            .where(
                (ContentMap.content_ref == content_ref)
                | (ClickEvent.slug == content_ref)
            )
        )
        clicks_total = int((await self.session.execute(click_q)).scalar_one() or 0)

        resolves_by_result_q = (
            select(
                InboundEvent.result,
                func.count(InboundEvent.id),
            )
            .where(InboundEvent.created_at >= since)
            .where(
                (InboundEvent.content_ref == content_ref)
                | (InboundEvent.resolved_slug == content_ref)
            )
            .group_by(InboundEvent.result)
        )
        result_rows = (await self.session.execute(resolves_by_result_q)).all()
        resolves_by_result = {"hit": 0, "fallback_payload": 0, "fallback_catalog": 0}
        for result, total in result_rows:
            if result in resolves_by_result:
                resolves_by_result[result] = int(total or 0)

        ctr_bridge = float(clicks_total / resolves_total) if resolves_total else 0.0

        redirect_miss_q = (
            select(func.count(ClickEvent.id))
            .select_from(ClickEvent)
            .join(ContentMap, ClickEvent.content_map_id == ContentMap.id, isouter=True)
            .where(ClickEvent.created_at >= since)
            .where(
                (ContentMap.content_ref == content_ref)
                | (ClickEvent.slug == content_ref)
            )
            .where(func.coalesce(ClickEvent.meta["miss"].as_boolean(), False).is_(True))
        )
        redirect_miss_total = int((await self.session.execute(redirect_miss_q)).scalar_one() or 0)

        return {
            "content_ref": content_ref,
            "hours": hours,
            "resolves_total": resolves_total,
            "resolves_by_result": resolves_by_result,
            "clicks_total": clicks_total,
            "ctr_bridge": ctr_bridge,
            "redirect_miss_total": redirect_miss_total,
        }

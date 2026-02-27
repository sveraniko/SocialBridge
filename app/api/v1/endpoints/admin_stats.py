from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import validate_admin_token
from app.db.session import get_db_session
from app.repositories.admin_stats_repo import AdminStatsRepository

router = APIRouter(prefix="/v1/admin/stats", tags=["admin"], dependencies=[Depends(validate_admin_token)])


@router.get("/overview")
async def get_overview(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AdminStatsRepository(session)
    return await repo.overview(hours=hours)


@router.get("/top")
async def get_top(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AdminStatsRepository(session)
    return {
        "hours": hours,
        "limit": limit,
        "top_campaigns_by_clicks": await repo.top_campaigns_by_clicks(hours=hours, limit=limit),
        "top_campaigns_by_resolves": await repo.top_campaigns_by_resolves(hours=hours, limit=limit),
    }


@router.get("/campaign")
async def get_campaign(
    content_ref: str,
    hours: int = Query(default=24, ge=1, le=24 * 30),
    session: AsyncSession = Depends(get_db_session),
):
    repo = AdminStatsRepository(session)
    return await repo.campaign_stats(content_ref=content_ref, hours=hours)

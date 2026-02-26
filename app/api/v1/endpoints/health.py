from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.db.session import get_db_session

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "socialbridge", "version": "v1"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_db_session)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise APIError(code="service_unavailable", message="database unavailable", status_code=503) from exc
    return {"status": "ok", "service": "socialbridge", "checks": {"database": "ok"}}

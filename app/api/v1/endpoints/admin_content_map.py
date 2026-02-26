from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import validate_admin_token
from app.db.session import get_db_session
from app.repositories.content_map_repo import ContentMapRepository
from app.services.admin_service import AdminService

router = APIRouter(prefix="/v1/admin/content-map", tags=["admin"], dependencies=[Depends(validate_admin_token)])


@router.get("")
async def list_content_map(
    channel: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    data = await AdminService(ContentMapRepository(session)).list_content_map(channel, is_active, limit, offset)
    return data


@router.post("/upsert")
async def upsert_content_map(payload: dict, session: AsyncSession = Depends(get_db_session)):
    try:
        item = await AdminService(ContentMapRepository(session)).upsert(payload)
        await session.commit()
        return item
    except ValueError as exc:
        await session.rollback()
        return JSONResponse(status_code=400, content={"error": str(exc)})


@router.post("/import")
async def import_content_map(items: list[dict], session: AsyncSession = Depends(get_db_session)):
    result = await AdminService(ContentMapRepository(session)).import_items(items)
    await session.commit()
    return result


@router.get("/export")
async def export_content_map(session: AsyncSession = Depends(get_db_session)):
    return await AdminService(ContentMapRepository(session)).export()


@router.post("/disable")
async def disable_content_map(payload: dict, session: AsyncSession = Depends(get_db_session)):
    ok = await AdminService(ContentMapRepository(session)).disable(payload["channel"], payload["content_ref"])
    await session.commit()
    return {"disabled": ok}

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
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
    service = AdminService(ContentMapRepository(session))
    try:
        item = await service.upsert(payload)
        await session.commit()
        return {"item": item}
    except ValueError as exc:
        await session.rollback()
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": str(exc)}})
    except IntegrityError:
        await session.rollback()
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "conflict", "message": "slug already exists"}},
        )


@router.post("/import")
async def import_content_map(items: list[dict], session: AsyncSession = Depends(get_db_session)):
    service = AdminService(ContentMapRepository(session))
    created = 0
    updated = 0
    failed = 0
    errors = []
    for idx, item in enumerate(items):
        try:
            async with session.begin_nested():
                result = await service.import_item(item)
            if result == "created":
                created += 1
            else:
                updated += 1
        except ValueError as exc:
            failed += 1
            await session.rollback()
            errors.append({"index": idx, "code": "bad_request", "message": str(exc)})
        except IntegrityError:
            failed += 1
            await session.rollback()
            errors.append({"index": idx, "code": "conflict", "message": "slug already exists"})
    await session.commit()
    return {"created": created, "updated": updated, "failed": failed, "errors": errors}


@router.get("/export")
async def export_content_map(session: AsyncSession = Depends(get_db_session)):
    return await AdminService(ContentMapRepository(session)).export()


@router.post("/disable")
async def disable_content_map(payload: dict, session: AsyncSession = Depends(get_db_session)):
    channel = payload.get("channel")
    content_ref = payload.get("content_ref")
    if not isinstance(channel, str) or not channel or not isinstance(content_ref, str) or not content_ref:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "bad_request", "message": "channel and content_ref are required"}},
        )
    ok = await AdminService(ContentMapRepository(session)).disable(channel, content_ref)
    await session.commit()
    return {"result": "disabled" if ok else "not_found"}

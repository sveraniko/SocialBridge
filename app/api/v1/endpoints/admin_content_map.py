from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import error_response
from app.core.security import validate_admin_token
from app.db.session import get_db_session
from app.repositories.content_map_repo import ContentMapRepository
from app.services.admin_service import AdminService, AdminValidationError

router = APIRouter(prefix="/v1/admin/content-map", tags=["admin"], dependencies=[Depends(validate_admin_token)])


@router.get("")
async def list_content_map(
    channel: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=200, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    data = await AdminService(ContentMapRepository(session)).list_content_map(channel, is_active, limit, offset)
    return data


@router.post("/upsert")
async def upsert_content_map(payload: dict, session: AsyncSession = Depends(get_db_session)):
    service = AdminService(ContentMapRepository(session))
    try:
        item, result = await service.upsert(payload)
        await session.commit()
        return {"item": item, "result": result}
    except AdminValidationError as exc:
        await session.rollback()
        extra = {"field": exc.field} if exc.field else {}
        return error_response(400, exc.message, code=exc.code, **extra)
    except IntegrityError:
        await session.rollback()
        return error_response(409, "slug already exists", code="conflict", field="slug")


def _extract_import_items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise AdminValidationError("import body must be array or object with items[]", field="items")


@router.post("/import")
async def import_content_map(payload: Any = Body(...), session: AsyncSession = Depends(get_db_session)):
    service = AdminService(ContentMapRepository(session))
    created = 0
    updated = 0
    failed = 0
    errors = []

    try:
        items = _extract_import_items(payload)
    except AdminValidationError as exc:
        extra = {"field": exc.field} if exc.field else {}
        return error_response(400, exc.message, code=exc.code, **extra)

    for idx, item in enumerate(items):
        try:
            async with session.begin():
                result = await service.import_item(item)
            if result == "created":
                created += 1
            else:
                updated += 1
        except AdminValidationError as exc:
            failed += 1
            details = {"index": idx, "code": exc.code, "message": exc.message}
            if exc.field:
                details["field"] = exc.field
            errors.append(details)
        except IntegrityError:
            failed += 1
            errors.append({"index": idx, "code": "conflict", "message": "slug already exists", "field": "slug"})
    return {"created": created, "updated": updated, "failed": failed, "errors": errors}


@router.get("/export")
async def export_content_map(
    channel: str | None = None,
    is_active: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    return await AdminService(ContentMapRepository(session)).export(channel=channel, is_active=is_active)


@router.post("/disable")
async def disable_content_map(payload: dict, session: AsyncSession = Depends(get_db_session)):
    channel = payload.get("channel")
    content_ref = payload.get("content_ref")
    if not isinstance(channel, str) or not channel or not isinstance(content_ref, str) or not content_ref:
        return error_response(400, "channel and content_ref are required", code="bad_request")
    ok = await AdminService(ContentMapRepository(session)).disable(channel, content_ref)
    await session.commit()
    return {"result": "disabled" if ok else "not_found"}

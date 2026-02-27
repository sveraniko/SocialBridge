from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.manychat_normalizer import normalize
from app.api.v1.schemas import ResolveResponse
from app.core.config import get_settings
from app.core.errors import error_response
from app.core.security import validate_admin_token
from app.db.session import get_db_session
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository
from app.services.resolve_service import ResolveService

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(validate_admin_token)])


@router.post("/resolve-preview", response_model=ResolveResponse)
async def resolve_preview(payload: dict, request: Request, session: AsyncSession = Depends(get_db_session)):
    data = normalize(payload)
    if not data.channel:
        return error_response(400, "channel is required", code="bad_request")

    service = ResolveService(
        get_settings(),
        ContentMapRepository(session),
        InboundEventRepository(session),
    )
    output = await service.resolve(payload, data, request_id=request.headers.get("X-Request-Id"), persist_inbound_event=False)
    return {
        "reply_text": output.reply_text,
        "url": output.url,
        "tg_url": output.tg_url,
        "start_param": output.start_param,
        "slug": output.slug,
        "tag": output.tag,
        "result": output.result.value,
    }

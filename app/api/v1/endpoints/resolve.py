from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.manychat_normalizer import normalize
from app.core.config import get_settings
from app.core.security import validate_mc_token
from app.db.session import get_db_session
from app.repositories.content_map_repo import ContentMapRepository
from app.repositories.inbound_event_repo import InboundEventRepository
from app.services.resolve_service import ResolveService

router = APIRouter(prefix="/v1/mc", tags=["manychat"])


@router.post("/resolve", dependencies=[Depends(validate_mc_token)])
async def resolve_manychat(
    payload: dict,
    request: Request,
    request_id: str | None = Header(default=None, alias="X-Request-Id"),
    session: AsyncSession = Depends(get_db_session),
):
    data = normalize(payload)
    if not data.channel:
        return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "channel is required"}})
    service = ResolveService(
        get_settings(),
        ContentMapRepository(session),
        InboundEventRepository(session),
    )
    output = await service.resolve(payload, data, request_id=request_id)
    await session.commit()
    return {
        "reply_text": output.reply_text,
        "url": output.url,
        "start_param": output.start_param,
        "slug": output.slug,
        "tag": output.tag,
        "result": output.result.value,
    }

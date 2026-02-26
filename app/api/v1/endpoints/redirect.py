from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.repositories.click_event_repo import ClickEventRepository
from app.repositories.content_map_repo import ContentMapRepository
from app.services.redirect_service import RedirectService

router = APIRouter(tags=["redirect"])


@router.get("/t/{slug}")
async def redirect_by_slug(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    service = RedirectService(get_settings(), ContentMapRepository(session), ClickEventRepository(session))
    target = await service.resolve_redirect(
        slug=slug,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        ip=request.client.host if request.client else None,
    )
    await session.commit()
    return RedirectResponse(target, status_code=302)

from app.adapters.deeplink import build_tg_deeplink
from app.adapters.hashing import ip_hash
from app.core.config import Settings
from app.db.models.content_map import ContentMap
from app.repositories.click_event_repo import ClickEventRepository
from app.repositories.content_map_repo import ContentMapRepository


class RedirectService:
    def __init__(
        self,
        settings: Settings,
        content_repo: ContentMapRepository,
        click_repo: ClickEventRepository,
    ):
        self.settings = settings
        self.content_repo = content_repo
        self.click_repo = click_repo

    async def resolve_redirect(
        self, slug: str, user_agent: str | None, referer: str | None, ip: str | None
    ) -> str:
        content: ContentMap | None = await self.content_repo.find_active_by_slug(slug)
        start_param = content.start_param if content else None
        await self.click_repo.create(
            {
                "content_map_id": content.id if content else None,
                "slug": slug,
                "user_agent": (user_agent or "")[:512] or None,
                "referer": referer,
                "ip_hash": self._build_ip_hash(ip),
                "meta": {"miss": content is None},
            }
        )
        return build_tg_deeplink(self.settings.SIS_BOT_USERNAME, start_param)

    def _build_ip_hash(self, ip: str | None) -> str | None:
        if not self.settings.CLICK_LOG_IP or not ip:
            return None
        return ip_hash(ip, self.settings.IP_HASH_SALT or "")

import logging

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s %(message)s",
    )

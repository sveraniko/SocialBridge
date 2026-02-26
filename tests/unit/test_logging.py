import logging

from app.core.logging import configure_logging


def test_configure_logging_request_id_filter_smoke():
    configure_logging()
    logger = logging.getLogger("test")
    logger.info("hello")

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SocialBridge", version="v1")
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    register_error_handlers(app)
    return app


app = create_app()

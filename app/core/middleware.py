import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request_id_ctx.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

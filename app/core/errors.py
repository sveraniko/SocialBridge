import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.middleware import request_id_ctx

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code


ERROR_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    403: "forbidden",
    404: "not_found",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def _build_error_response(status_code: int, message: str, code: str | None = None) -> JSONResponse:
    request_id = request_id_ctx.get()
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code or ERROR_CODE_BY_STATUS.get(status_code, "error"),
                "message": message,
                "request_id": request_id,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError):
        return _build_error_response(exc.status_code, exc.message, code=exc.code)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "request failed"
        return _build_error_response(exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_: Request, exc: RequestValidationError):
        first_error = exc.errors()[0].get("msg") if exc.errors() else None
        message = first_error if isinstance(first_error, str) else "validation failed"
        return _build_error_response(422, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_: Request, exc: Exception):
        logger.exception("Unhandled exception")
        return _build_error_response(500, "internal server error")

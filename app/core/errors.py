from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

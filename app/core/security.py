from fastapi import Header, HTTPException

from app.core.config import get_settings


def validate_admin_token(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != get_settings().ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")


def validate_mc_token(x_mc_token: str = Header(default="")) -> None:
    settings = get_settings()
    if settings.MC_TOKEN_REQUIRED and x_mc_token != settings.MC_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

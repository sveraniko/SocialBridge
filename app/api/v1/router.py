from fastapi import APIRouter

from app.api.v1.endpoints import admin_content_map, admin_resolve_preview, health, redirect, resolve

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(resolve.router)
api_router.include_router(redirect.router)
api_router.include_router(admin_content_map.router)
api_router.include_router(admin_resolve_preview.router)

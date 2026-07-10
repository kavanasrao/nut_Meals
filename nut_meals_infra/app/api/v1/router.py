"""Mount all API v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import backups, restore, storage

api_router = APIRouter()
api_router.include_router(backups.router, prefix="/backups", tags=["backups"])
api_router.include_router(restore.router, prefix="/restore", tags=["restore"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])

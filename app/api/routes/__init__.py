from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(jobs_router)

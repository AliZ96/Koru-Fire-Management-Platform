from fastapi import APIRouter
from app.api.routers.core import router as core_router
from app.api.routers.auth import router as auth_router

router = APIRouter()
router.include_router(core_router)
router.include_router(auth_router)

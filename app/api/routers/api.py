from fastapi import APIRouter
from app.api.routers.core import router as core_router
from app.api.routers.auth import router as auth_router

router = APIRouter()
router.include_router(core_router)
router.include_router(auth_router)
from app.api.routers.fire_risk import router as fire_risk_router

router.include_router(fire_risk_router)

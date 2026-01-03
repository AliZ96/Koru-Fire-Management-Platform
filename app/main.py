from fastapi import FastAPI

# Router imports
from app.api.routers.core import router as core_router
from app.api.routers.auth import router as auth_router
from app.api.routers.health_router import router as health_router
from app.api.routers.fire_risk import router as fire_risk_router


def create_app() -> FastAPI:
    """
    Application factory.
    İleride test, prod, dev ayrımı yapmak istersek çok işimize yarar.
    """
    app = FastAPI(
        title="Koru Bitirme",
        version="1.0.0",
        description="KORU – Orman Yangını Risk Analizi ve Yönetim Sistemi"
    )

    # Core (mevcut) endpointler
    app.include_router(core_router)

    # Authentication endpointleri
    app.include_router(auth_router)

    # Health / DB test endpointleri
    app.include_router(health_router)

    # Fire risk endpointleri
    app.include_router(fire_risk_router)

    return app


# Uvicorn'un göreceği app
app = create_app()

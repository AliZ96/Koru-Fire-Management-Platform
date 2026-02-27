from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# DB imports
from app.db.base import Base
from app.core.database import engine

# 🔥 MODELLERİ IMPORT ET
import app.models

# Router imports
from app.api.routers.core import router as core_router
from app.api.routers.auth import router as auth_router
from app.api.routers.health_router import router as health_router
from app.api.routers.fire_risk import router as fire_risk_router
from app.api.routers.air_accessibility import router as air_accessibility_router
from app.api.routers.resource_proximity import router as resource_proximity_router
from app.api.routers.accessibility import router as accessibility_router



def create_app() -> FastAPI:

    app = FastAPI(
        title="Koru Bitirme",
        version="1.0.0",
        description="KORU – Orman Yangını Risk Analizi ve Yönetim Sistemi"
    )

    @app.on_event("startup")
    def on_startup():
        print("METADATA TABLES:", Base.metadata.tables.keys())
        Base.metadata.create_all(bind=engine)

    app.include_router(core_router)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(fire_risk_router)
    app.include_router(air_accessibility_router)
    app.include_router(resource_proximity_router)
    app.include_router(accessibility_router)


    static_path = Path(__file__).parent.parent / "static"

    if static_path.exists():

        app.mount(
            "/static",
            StaticFiles(directory=str(static_path), html=False),
            name="static"
        )

        @app.get("/", response_class=FileResponse)
        async def root():
            return FileResponse(str(static_path / "index.html"))

        @app.get("/{path:path}", response_class=FileResponse)
        async def serve_html(path: str):
            file_path = static_path / f"{path}.html"
            if file_path.exists():
                return FileResponse(str(file_path))
            return FileResponse(str(static_path / "index.html"))

    return app


app = create_app()

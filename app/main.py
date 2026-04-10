from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.routers.integrated_layer import router as integrated_layer_router
from app.api.routers.routing import router as routing_router
from app.api.routers.mobile_ui import router as mobile_ui_router
from app.api.routers.accessibility import router as accessibility_router


def create_app() -> FastAPI:

    app = FastAPI(
        title="Koru Bitirme",
        version="1.0.0",
        description="KORU – Orman Yangını Risk Analizi ve Yönetim Sistemi"
    )

    # Dev ortaminda Flutter web/mobile istemcilerinden gelen istekler icin CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup():
        print("METADATA TABLES:", Base.metadata.tables.keys())
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"DB table creation skipped: {e}")

    app.include_router(core_router)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(fire_risk_router)
    app.include_router(air_accessibility_router)
    app.include_router(resource_proximity_router)
    app.include_router(integrated_layer_router)
    app.include_router(routing_router)
    app.include_router(mobile_ui_router)
    app.include_router(accessibility_router)

    static_path = Path(__file__).parent.parent / "static"

    if static_path.exists():

        # Mount MUST come before the catch-all GET route.
        # Otherwise /{path:path} intercepts /static/... requests and the files are never served.
        app.mount(
            "/static",
            StaticFiles(directory=str(static_path), html=False),
            name="static"
        )

        @app.get("/", response_class=FileResponse)
        async def root():
            """Landing page — new KORU home design"""
            return FileResponse(str(static_path / "home.html"))

        @app.get("/app", response_class=FileResponse)
        async def app_entry():
            """Uygulama harita ekranı."""
            return FileResponse(str(static_path / "index.html"))

        @app.get("/{path:path}", response_class=FileResponse)
        async def serve_html(path: str):
            file_path = static_path / f"{path}.html"
            if file_path.exists():
                return FileResponse(str(file_path))
            # Fallback to home page (landing)
            return FileResponse(str(static_path / "home.html"))

    return app


app = create_app()
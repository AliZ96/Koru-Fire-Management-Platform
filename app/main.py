import logging
import time

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import app.models
from app.api.routers.accessibility import router as accessibility_router
from app.api.routers.air_accessibility import router as air_accessibility_router
from app.api.routers.auth import router as auth_router
from app.api.routers.core import router as core_router
from app.api.routers.fire_risk import router as fire_risk_router
from app.api.routers.health_router import router as health_router
from app.api.routers.integrated_layer import router as integrated_layer_router
from app.api.routers.mobile_ui import router as mobile_ui_router
from app.api.routers.optimization import router as optimization_router
from app.api.routers.resource_proximity import router as resource_proximity_router
from app.api.routers.routing import router as routing_router
from app.core.config import settings
from app.core.database import engine
from app.db.base import Base
from app.scenario.router import router as scenario_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Koru Bitirme",
        version="1.0.0",
        description="KORU – Orman Yangını Risk Analizi ve Yönetim Sistemi"
    )

    cors_origins = settings.cors_origins_list
    allow_all = cors_origins == ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    perf_logger = logging.getLogger("app.performance")

    @app.middleware("http")
    async def add_request_timing(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"

        if elapsed_ms > 800:
            perf_logger.warning(
                "Slow request detected: %s %s took %.2fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )

        return response

    @app.on_event("startup")
    def on_startup():
        print(f"APP_ENV={settings.APP_ENV}")
        print(f"DATABASE_CONFIGURED={bool(settings.DATABASE_URL)}")
        print("METADATA TABLES:", Base.metadata.tables.keys())
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables checked/created successfully.")
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
    app.include_router(optimization_router)
    app.include_router(mobile_ui_router)
    app.include_router(accessibility_router)
    app.include_router(scenario_router)

    static_path = Path(__file__).resolve().parent.parent / "static"

    if static_path.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(static_path), html=False),
            name="static"
        )

        @app.get("/", response_class=FileResponse)
        async def root():
            return FileResponse(str(static_path / "home.html"))

        @app.get("/app", response_class=FileResponse)
        async def app_entry():
            return FileResponse(str(static_path / "index.html"))

        @app.get("/{path:path}", response_class=FileResponse)
        async def serve_html(path: str):
            file_path = static_path / f"{path}.html"
            if file_path.exists():
                return FileResponse(str(file_path))
            return FileResponse(str(static_path / "home.html"))
    else:
        @app.get("/")
        async def root_without_static():
            return JSONResponse({
                "message": "KORU API is running",
                "environment": settings.APP_ENV
            })

    return app


app = create_app()
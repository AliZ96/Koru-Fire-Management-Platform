from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Router imports
from app.api.routers.core import router as core_router
from app.api.routers.auth import router as auth_router
from app.api.routers.health_router import router as health_router
from app.api.routers.fire_risk import router as fire_risk_router
from app.api.routers.air_accessibility import router as air_accessibility_router


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
    
    # Yangın risk endpointleri
    app.include_router(fire_risk_router)
    
    # Hava erişilebilirliği endpointleri (LLF-2.3)
    app.include_router(air_accessibility_router)
    
    # Statik dosyaları sunma
    static_path = Path(__file__).parent.parent / "static"
    if static_path.exists():
        # /static yolundaki tüm dosyaları sun
        app.mount("/static", StaticFiles(directory=str(static_path), html=False), name="static")
        
        # Root "/" için index.html'i sun
        @app.get("/", response_class=FileResponse)
        async def root():
            return FileResponse(str(static_path / "index.html"))
        
        # HTML dosyaları için catch-all: /login, /welcome vb.
        @app.get("/{path:path}", response_class=FileResponse)
        async def serve_html(path: str):
            file_path = static_path / f"{path}.html"
            if file_path.exists():
                return FileResponse(str(file_path))
            # Eğer .html dosyası yoksa index.html'i döndür (SPA davranışı)
            return FileResponse(str(static_path / "index.html"))
            return FileResponse(str(static_path / "index.html"))

    return app


# Uvicorn'un göreceği app
app = create_app()

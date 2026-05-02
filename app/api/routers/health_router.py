from fastapi import APIRouter

from app.services.geo_service_client import GeoServiceClient
from app.services.firestore_store import FirestoreStore

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db")
def health_db():
    store = FirestoreStore()
    store.db.collection("_health").document("ping").set({"at": "ok"}, merge=True)
    return {"ok": True, "db": "connected", "provider": "firestore"}


@router.get("/geo")
def health_geo():
    client = GeoServiceClient()
    if not client.enabled:
        return {"ok": True, "geo": "disabled"}
    return {"ok": True, "geo": "configured", "base_url": client.base_url}

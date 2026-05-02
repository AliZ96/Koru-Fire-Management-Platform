from fastapi import APIRouter

from app.services.firestore_store import FirestoreStore

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/db")
def health_db():
    store = FirestoreStore()
    store.db.collection("_health").document("ping").set({"at": "ok"}, merge=True)
    return {"ok": True, "db": "connected", "provider": "firestore"}

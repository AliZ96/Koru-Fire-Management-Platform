from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.deps import get_db

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ok": True, "db": "connected"}

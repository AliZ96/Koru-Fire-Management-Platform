from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _get_default_sqlite_url() -> str:
    """
    Local/dev fallback.
    DATABASE_URL yoksa ./database/app.db kullanılır.
    """
    base_dir = Path(__file__).resolve().parents[2]
    db_path = base_dir / "database" / "app.db"
    return f"sqlite:///{db_path}"


def _engine_kwargs(db_url: str) -> dict:
    kwargs = {
        "pool_pre_ping": True,
    }

    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    return kwargs


db_url = settings.DATABASE_URL or _get_default_sqlite_url()

engine = create_engine(
    db_url,
    **_engine_kwargs(db_url),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
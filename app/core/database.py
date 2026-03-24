from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


def _get_default_sqlite_url() -> str:
    """Fallback DB URL for local/dev when DATABASE_URL is not set.

    Uses a file under ./database/app.db so tests ve lokal kurulum
    ortam değişkeni olmadan da çalışabilsin.
    """

    base_dir = Path(__file__).resolve().parents[2]
    db_path = base_dir / "database" / "app.db"
    return f"sqlite:///{db_path}"


db_url = settings.DATABASE_URL or _get_default_sqlite_url()

# Engine
engine = create_engine(
    db_url,
    pool_pre_ping=True,  # bağlantı koparsa otomatik kontrol
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()

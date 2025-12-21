from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Engine
engine = create_engine(
    settings.DATABASE_URL,
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

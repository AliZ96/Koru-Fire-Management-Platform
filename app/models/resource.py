import uuid

from geoalchemy2 import Geography
from sqlalchemy import CHAR, Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator

from app.core.config import settings
from app.db.base import Base


class GUID(TypeDecorator):
    """Use native UUID on PostgreSQL and string UUID elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# app/core/database.py, DATABASE_URL verilmediğinde SQLite fallback kullanıyor.
# Model tipi seçimi de aynı davranışı izlemeli; aksi halde SQLite'ta Geography
# seçilip startup sırasında tablo oluşturma tümüyle kırılıyor.
USING_SQLITE = not settings.DATABASE_URL or settings.DATABASE_URL.startswith("sqlite")
LOCATION_TYPE = String(64) if USING_SQLITE else Geography(geometry_type="POINT", srid=4326)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # fire_station, water, hospital
    location = Column(LOCATION_TYPE, nullable=False)

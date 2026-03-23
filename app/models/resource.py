import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # fire_station, water, hospital
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)

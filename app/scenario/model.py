from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from app.db.base import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status     = Column(String(20), default="pending")

    n_points   = Column(Integer, nullable=False)
    k_clusters = Column(Integer, nullable=False)

    # k_means çıktısı: points, clusters, summary
    pipeline_result = Column(JSON, nullable=True)

    # GA/SA tur rotaları: [{station_id, assigned_fire_points, vehicles}]
    ga_result = Column(JSON, nullable=True)
    sa_result = Column(JSON, nullable=True)

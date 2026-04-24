from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FireScenario(Base):
    __tablename__ = "fire_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lon: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    elapsed_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshots: Mapped[list["SpreadSnapshot"]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="SpreadSnapshot.step",
    )


class SpreadSnapshot(Base):
    __tablename__ = "spread_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("fire_scenarios.id"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    polygon_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    wind_speed_ms: Mapped[float] = mapped_column(Float, nullable=False)
    wind_dir_deg: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scenario: Mapped["FireScenario"] = relationship(back_populates="snapshots")


class UserLocation(Base):
    __tablename__ = "user_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SpreadAlert(Base):
    __tablename__ = "spread_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("fire_scenarios.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    eta_minutes: Mapped[float] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

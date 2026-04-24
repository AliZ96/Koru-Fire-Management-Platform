import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, Set

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.fire_spread import FireScenario, SpreadAlert, SpreadSnapshot, UserLocation
from app.services.fire_spread_engine import compute_eta, compute_spread_polygon, haversine_km
from app.services.weather_service import get_hourly_weather, get_wind

logger = logging.getLogger(__name__)

UPDATE_INTERVAL_SECONDS = 30
STEP_DURATION_MINUTES = 60.0

# scenario_id → set of async send-coroutine callables
_ws_registry: Dict[int, Set[Callable[[str], Awaitable[None]]]] = {}


def register_ws(scenario_id: int, send_fn: Callable) -> None:
    _ws_registry.setdefault(scenario_id, set()).add(send_fn)


def unregister_ws(scenario_id: int, send_fn: Callable) -> None:
    _ws_registry.get(scenario_id, set()).discard(send_fn)


async def broadcast(scenario_id: int, payload: dict) -> None:
    msg = json.dumps(payload, default=str)
    dead: Set[Callable] = set()
    for fn in list(_ws_registry.get(scenario_id, set())):
        try:
            await fn(msg)
        except Exception:
            dead.add(fn)
    for fn in dead:
        _ws_registry.get(scenario_id, set()).discard(fn)


async def refresh_scenario(scenario_id: int) -> None:
    db: Session = SessionLocal()
    try:
        scenario = db.get(FireScenario, scenario_id)
        if not scenario or scenario.status != "active":
            return

        wind = get_wind(scenario.origin_lat, scenario.origin_lon)
        wind_speed = float(wind.get("speed_ms", 6.0))
        wind_dir = float(wind.get("deg", 240.0))

        humidity = 50.0
        temperature_c = 25.0
        try:
            hourly = get_hourly_weather(scenario.origin_lat, scenario.origin_lon)
            h = hourly.get("hourly", {})
            times = h.get("time", [])
            current_hr = datetime.now().strftime("%Y-%m-%dT%H:00")
            idx = times.index(current_hr) if current_hr in times else 0
            humidity = float((h.get("relative_humidity_2m") or [50])[idx])
            temperature_c = float((h.get("temperature_2m") or [25])[idx])
        except Exception:
            pass

        scenario.elapsed_minutes = (scenario.elapsed_minutes or 0.0) + STEP_DURATION_MINUTES
        scenario.updated_at = datetime.now(timezone.utc)

        feature = compute_spread_polygon(
            center_lat=scenario.origin_lat,
            center_lon=scenario.origin_lon,
            wind_dir_deg=wind_dir,
            wind_speed_ms=wind_speed,
            elapsed_minutes=scenario.elapsed_minutes,
            humidity=humidity,
            temperature_c=temperature_c,
        )

        step_num = db.query(SpreadSnapshot).filter_by(scenario_id=scenario.id).count()
        snap = SpreadSnapshot(
            scenario_id=scenario.id,
            step=step_num,
            elapsed_minutes=scenario.elapsed_minutes,
            polygon_geojson=json.dumps(feature),
            wind_speed_ms=wind_speed,
            wind_dir_deg=wind_dir,
            humidity=humidity,
            temperature_c=temperature_c,
        )
        db.add(snap)

        alert_payloads = []
        user_locs = db.query(UserLocation).filter_by(notifications_enabled=True).all()
        for uloc in user_locs:
            dist_km = haversine_km(scenario.origin_lat, scenario.origin_lon, uloc.lat, uloc.lon)
            if dist_km > 80:
                continue

            eta_min = compute_eta(
                fire_lat=scenario.origin_lat,
                fire_lon=scenario.origin_lon,
                user_lat=uloc.lat,
                user_lon=uloc.lon,
                wind_dir_deg=wind_dir,
                wind_speed_ms=wind_speed,
                elapsed_minutes=scenario.elapsed_minutes,
                humidity=humidity,
                temperature_c=temperature_c,
            )
            if eta_min is None:
                continue

            if eta_min == 0.0:
                severity = "critical"
                msg = "TEHLIKE: Yangın konumunuza ulaşmış olabilir! Derhal tahliye edin!"
            elif eta_min < 30:
                severity = "critical"
                msg = f"ACIL: Yangın {eta_min:.0f} dakika içinde konumunuza ulaşabilir! Bölgeyi terk edin!"
            elif eta_min < 90:
                severity = "high"
                msg = f"UYARI: Yangın yaklaşık {eta_min:.0f} dakika içinde konumunuza ulaşabilir."
            elif eta_min < 240:
                severity = "medium"
                msg = f"Dikkat: Yangın {eta_min:.0f} dakika içinde bölgenize yaklaşabilir."
            else:
                severity = "low"
                msg = f"Bilgi: Yangın {dist_km:.1f} km uzakta. Tahmini: {eta_min:.0f} dk."

            existing = (
                db.query(SpreadAlert)
                .filter_by(scenario_id=scenario.id, user_id=uloc.user_id)
                .order_by(SpreadAlert.created_at.desc())
                .first()
            )
            if not existing or existing.severity != severity:
                db.add(SpreadAlert(
                    scenario_id=scenario.id,
                    user_id=uloc.user_id,
                    distance_km=round(dist_km, 2),
                    eta_minutes=round(eta_min, 1),
                    severity=severity,
                    message=msg,
                ))

            alert_payloads.append({
                "user_id": uloc.user_id,
                "distance_km": round(dist_km, 2),
                "eta_minutes": round(eta_min, 1),
                "severity": severity,
                "message": msg,
            })

        db.commit()
        db.refresh(snap)

        await broadcast(scenario.id, {
            "event": "spread_update",
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "origin": {"lat": scenario.origin_lat, "lon": scenario.origin_lon},
            "elapsed_minutes": scenario.elapsed_minutes,
            "step": snap.step,
            "spread_polygon": json.loads(snap.polygon_geojson),
            "weather": {
                "wind_speed_ms": wind_speed,
                "wind_dir_deg": wind_dir,
                "humidity": humidity,
                "temperature_c": temperature_c,
            },
            "alerts": alert_payloads,
        })

    except Exception as e:
        logger.error(f"refresh_scenario error ({scenario_id}): {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


async def monitor_loop() -> None:
    logger.info("Fire spread monitor loop started")
    while True:
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
        db: Session = SessionLocal()
        try:
            ids = [r.id for r in db.query(FireScenario).filter_by(status="active").all()]
        except Exception:
            ids = []
        finally:
            db.close()
        for sid in ids:
            try:
                await refresh_scenario(sid)
            except Exception as e:
                logger.error(f"Monitor loop error for scenario {sid}: {e}")

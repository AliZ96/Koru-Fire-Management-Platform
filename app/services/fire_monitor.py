import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, Set

from app.services.fire_spread_engine import compute_eta, compute_spread_polygon, haversine_km
from app.services.firestore_store import FirestoreStore
from app.services.weather_service import get_hourly_weather, get_wind

logger = logging.getLogger(__name__)

UPDATE_INTERVAL_SECONDS = 15 * 60
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
    store = FirestoreStore()
    try:
        scenario = store.get_fire_scenario(str(scenario_id))
        if not scenario or scenario.get("status") != "active":
            return

        origin_lat = float(scenario.get("origin_lat", 0.0))
        origin_lon = float(scenario.get("origin_lon", 0.0))
        wind = get_wind(origin_lat, origin_lon)
        wind_speed = float(wind.get("speed_ms", 6.0))
        wind_dir = float(wind.get("deg", 240.0))

        humidity = 50.0
        temperature_c = 25.0
        try:
            hourly = get_hourly_weather(origin_lat, origin_lon)
            h = hourly.get("hourly", {})
            times = h.get("time", [])
            current_hr = datetime.now().strftime("%Y-%m-%dT%H:00")
            idx = times.index(current_hr) if current_hr in times else 0
            humidity = float((h.get("relative_humidity_2m") or [50])[idx])
            temperature_c = float((h.get("temperature_2m") or [25])[idx])
        except Exception:
            pass

        elapsed_minutes = float(scenario.get("elapsed_minutes", 0.0)) + STEP_DURATION_MINUTES
        store.update_fire_scenario(str(scenario_id), {"elapsed_minutes": elapsed_minutes})

        feature = compute_spread_polygon(
            center_lat=origin_lat,
            center_lon=origin_lon,
            wind_dir_deg=wind_dir,
            wind_speed_ms=wind_speed,
            elapsed_minutes=elapsed_minutes,
            humidity=humidity,
            temperature_c=temperature_c,
        )

        step_num = store.count_spread_snapshots(str(scenario_id))
        store.create_spread_snapshot(str(scenario_id), {
            "step": step_num,
            "elapsed_minutes": elapsed_minutes,
            "polygon_geojson": json.dumps(feature),
            "wind_speed_ms": wind_speed,
            "wind_dir_deg": wind_dir,
            "humidity": humidity,
            "temperature_c": temperature_c,
        })
        snap = store.get_latest_spread_snapshot(str(scenario_id)) or {"step": step_num}

        alert_payloads = []
        user_locs = store.get_enabled_user_locations()
        for uloc in user_locs:
            user_lat = float(uloc.get("lat", 0.0))
            user_lon = float(uloc.get("lon", 0.0))
            user_key = str(uloc.get("user_key"))
            if not user_key:
                continue
            dist_km = haversine_km(origin_lat, origin_lon, user_lat, user_lon)
            if dist_km > 80:
                continue

            eta_min = compute_eta(
                fire_lat=origin_lat,
                fire_lon=origin_lon,
                user_lat=user_lat,
                user_lon=user_lon,
                wind_dir_deg=wind_dir,
                wind_speed_ms=wind_speed,
                elapsed_minutes=elapsed_minutes,
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

            existing = store.get_latest_alert(str(scenario_id), user_key)
            if not existing or existing.get("severity") != severity:
                store.create_alert(
                    {
                        "scenario_id": str(scenario_id),
                        "user_key": user_key,
                        "distance_km": round(dist_km, 2),
                        "eta_minutes": round(eta_min, 1),
                        "severity": severity,
                        "message": msg,
                        "is_read": False,
                    }
                )

            alert_payloads.append({
                "user_id": user_key,
                "distance_km": round(dist_km, 2),
                "eta_minutes": round(eta_min, 1),
                "severity": severity,
                "message": msg,
            })

        await broadcast(str(scenario_id), {
            "event": "spread_update",
            "scenario_id": str(scenario_id),
            "scenario_name": scenario.get("name"),
            "origin": {"lat": origin_lat, "lon": origin_lon},
            "elapsed_minutes": elapsed_minutes,
            "step": snap.get("step", step_num),
            "spread_polygon": json.loads(snap.get("polygon_geojson", "{}")),
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


async def monitor_loop() -> None:
    logger.info("Fire spread monitor loop started")
    while True:
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
        store = FirestoreStore()
        ids = store.list_active_scenario_ids()
        for sid in ids:
            try:
                await refresh_scenario(sid)
            except Exception as e:
                logger.error(f"Monitor loop error for scenario {sid}: {e}")

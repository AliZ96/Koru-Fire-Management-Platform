import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import requests

from app.core.config import settings

_weather_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}


def get_hourly_weather(lat: float, lon: float) -> Dict[str, Any]:
    cache_ttl_s = float(os.getenv("WEATHER_CACHE_TTL", "300"))
    cache_key = (round(lat, 3), round(lon, 3))
    now = time.time()
    cached_item = _weather_cache.get(cache_key)
    if cached_item and now - cached_item["ts"] < cache_ttl_s:
        return cached_item["data"]

    base = settings.OPEN_METEO_BASE
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(
            [
                "wind_speed_10m",
                "wind_direction_10m",
                "relative_humidity_2m",
                "temperature_2m",
                "precipitation",
            ]
        ),
        "timezone": settings.TZ,
    }

    timeout_s = float(os.getenv("WEATHER_TIMEOUT", "6"))
    r = requests.get(base, params=params, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    _weather_cache[cache_key] = {"ts": now, "data": data}
    return data


def get_wind(lat: float, lon: float, when_iso: Optional[str] = None) -> Dict[str, Any]:
    try:
        data = get_hourly_weather(lat, lon)
    except requests.RequestException as e:
        return {"speed_ms": 6.0, "deg": 240.0, "source": f"open-meteo_error:{e}", "time": None}

    hourly = data.get("hourly", {})
    times = hourly.get("time") or []
    spd = hourly.get("wind_speed_10m") or []
    deg = hourly.get("wind_direction_10m") or []

    if not times or not spd or not deg:
        return {"speed_ms": 6.0, "deg": 240.0, "source": "open-meteo_empty_fallback", "time": None}

    if when_iso is None:
        target = datetime.now().strftime("%Y-%m-%dT%H:00")
    else:
        target = when_iso if len(when_iso) == 16 else when_iso + ":00"

    def to_dt(s: str) -> datetime:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M")

    try:
        if target in times:
            idx = times.index(target)
        else:
            tgt = to_dt(target)
            diffs = [abs((to_dt(t) - tgt).total_seconds()) for t in times]
            idx = diffs.index(min(diffs))
    except Exception:
        idx = 0

    return {
        "speed_ms": float(spd[idx]),
        "deg": float(deg[idx]),
        "source": "open-meteo",
        "time": times[idx],
    }

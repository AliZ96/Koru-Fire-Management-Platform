# app/weather.py
import requests, os
from datetime import datetime
from typing import Dict, Any, Optional

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/ecmwf"
TZ = "Europe/Istanbul"

def get_hourly_weather(lat: float, lon: float) -> Dict[str, Any]:
    base = OPEN_METEO_BASE
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "wind_speed_10m","wind_direction_10m",
            "relative_humidity_2m","temperature_2m","precipitation"
        ]),
        "timezone": TZ
    }
    timeout_s = float(os.getenv("WEATHER_TIMEOUT", "6"))
    r = requests.get(base, params=params, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

def get_wind(lat: float, lon: float, when_iso: Optional[str] = None) -> Dict[str, Any]:
    """
    Verilen koordinat için rüzgâr hızı (m/s) ve yönü (0..360°) döndürür.
    when_iso: 'YYYY-MM-DDTHH:00' formatında saat (opsiyonel). Boşsa 'şu an'a en yakın saat döner.
    """
    try:
        data = get_hourly_weather(lat, lon)
    except requests.RequestException as e:
        # demo fallback
        return {"speed_ms": 6.0, "deg": 240.0, "source": f"open-meteo_error:{e}", "time": None}

    hourly = data.get("hourly", {})
    times = hourly.get("time") or []
    spd = hourly.get("wind_speed_10m") or []
    deg = hourly.get("wind_direction_10m") or []
    if not times or not spd or not deg:
        return {"speed_ms": 6.0, "deg": 240.0, "source": "open-meteo_empty_fallback", "time": None}

    # hedef saat
    if when_iso is None:
        target = datetime.now().strftime("%Y-%m-%dT%H:00")  # yerel saat (TZ)
    else:
        target = when_iso if len(when_iso) == 16 else when_iso + ":00"

    # en yakın index
    def to_dt(s: str): return datetime.strptime(s, "%Y-%m-%dT%H:%M")
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

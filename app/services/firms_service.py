import csv
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests

from app.core.config import settings

API_TIMEOUT = 30
_CACHE_TTL_SECONDS = int(os.getenv("FIRMS_CACHE_TTL_SECONDS", "120"))
_firms_cache: Dict[str, Any] = {}


def _fallback_firms_geojson(reason: str, status: int = 200) -> Dict[str, Any]:
    """Return bundled fallback FIRMS data so demo flows stay stable offline."""
    fallback_path = Path(__file__).resolve().parent.parent.parent / "data" / "firms.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("meta", {})
                data["meta"].update({"fallback": True, "reason": reason})
                return data
        except Exception:
            pass

    return {
        "type": "FeatureCollection",
        "features": [],
        "meta": {"fallback": True, "reason": reason, "status": status},
    }


def fetch_firms_geojson(day_range: int = 3) -> Dict[str, Any]:
    """
    NASA FIRMS API'den Izmir bbox bölgesi için CSV verisini çekip GeoJSON FeatureCollection döndürür.
    settings üzerinden MAP_KEY, SOURCE, IZMIR_BBOX okunur.
    """

    # 1) Config doğrulama
    if not settings.MAP_KEY:
        return _fallback_firms_geojson("MAP_KEY not set (.env missing?)")

    source = settings.SOURCE
    bbox = settings.IZMIR_BBOX

    if not source:
        return _fallback_firms_geojson("SOURCE not set (.env missing?)")
    if not bbox:
        return _fallback_firms_geojson("IZMIR_BBOX not set (.env missing?)")

    # 2) URL oluşturma
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.MAP_KEY}/{source}/{bbox}/{day_range}"

    # 2.1) Kısa süreli cache (aynı day_range ve kaynak için)
    cache_key = f"{source}|{bbox}|{day_range}"
    now = time.time()
    cached_item = _firms_cache.get(cache_key)
    if cached_item and now - cached_item["ts"] < _CACHE_TTL_SECONDS:
        return cached_item["data"]

    # 3) İstek
    try:
        r = requests.get(url, timeout=API_TIMEOUT)
    except requests.RequestException as e:
        return _fallback_firms_geojson(f"Network error: {e}", status=502)

    # 4) Hata kodları
    if r.status_code == 401:
        return _fallback_firms_geojson("Unauthorized (401): MAP_KEY invalid or not permitted", status=401)
    if r.status_code == 404:
        return _fallback_firms_geojson("Not Found (404): Check SOURCE or endpoint", status=404)
    if r.status_code >= 400:
        return _fallback_firms_geojson(f"FIRMS error {r.status_code}", status=r.status_code)

    # 5) CSV -> GeoJSON
    reader = csv.DictReader(io.StringIO(r.text))
    feats = []

    for row in reader:
        try:
            lat = float(row.get("latitude") or 0.0)
            lon = float(row.get("longitude") or 0.0)
        except Exception:
            continue

        props = {k: v for k, v in row.items() if k not in ("latitude", "longitude")}

        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )

    data = {"type": "FeatureCollection", "features": feats}
    _firms_cache[cache_key] = {"ts": now, "data": data}
    return data

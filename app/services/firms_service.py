import csv
import io
from typing import Any, Dict

import requests

from app.core.config import settings

API_TIMEOUT = 30


def fetch_firms_geojson(day_range: int = 3) -> Dict[str, Any]:
    """
    NASA FIRMS API'den Izmir bbox bölgesi için CSV verisini çekip GeoJSON FeatureCollection döndürür.
    settings üzerinden MAP_KEY, SOURCE, IZMIR_BBOX okunur.
    """

    # 1) Config doğrulama
    if not settings.MAP_KEY:
        return {"error": "MAP_KEY not set (.env missing?)", "status": 500}

    source = settings.SOURCE
    bbox = settings.IZMIR_BBOX

    if not source:
        return {"error": "SOURCE not set (.env missing?)", "status": 500}
    if not bbox:
        return {"error": "IZMIR_BBOX not set (.env missing?)", "status": 500}

    # 2) URL oluşturma
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.MAP_KEY}/{source}/{bbox}/{day_range}"

    # 3) İstek
    try:
        r = requests.get(url, timeout=API_TIMEOUT)
    except requests.RequestException as e:
        return {"error": f"Network error: {e}", "status": 502}

    # 4) Hata kodları
    if r.status_code == 401:
        return {"error": "Unauthorized (401): MAP_KEY invalid or not permitted", "status": 401, "url": url}
    if r.status_code == 404:
        return {"error": "Not Found (404): Check SOURCE or endpoint", "status": 404, "url": url}
    if r.status_code >= 400:
        return {
            "error": f"FIRMS error {r.status_code}",
            "status": r.status_code,
            "preview": r.text[:200],
            "url": url
        }

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

    return {"type": "FeatureCollection", "features": feats}

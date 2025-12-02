import os, csv, io, requests
from pathlib import Path
from dotenv import load_dotenv

# Proje kökü = app klasörünün iki seviye üstü
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# .env dosyasını o yoldan yükle (override=True: mevcut ortama yaz)
load_dotenv(dotenv_path=ENV_PATH, override=True)

MAP_KEY = os.getenv("MAP_KEY")
IZMIR_BBOX = "26.230389,37.818402,28.495245,39.392935"
SOURCE = "VIIRS_SNPP_NRT"  # alternatif: VIIRS_NOAA20_NRT, MODIS_C6_1

def fetch_firms_geojson(day_range: int = 3):
    if not MAP_KEY:
        return {"error": "MAP_KEY not set (.env missing?)", "status": 500}

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{IZMIR_BBOX}/{day_range}"
    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException as e:
        return {"error": f"Network error: {e}", "status": 502}

    if r.status_code == 401:
        return {"error": "Unauthorized (401): MAP_KEY invalid or not permitted", "status": 401, "url": url}
    if r.status_code == 404:
        return {"error": "Not Found (404): Check SOURCE or endpoint", "status": 404, "url": url}
    if r.status_code >= 400:
        return {"error": f"FIRMS error {r.status_code}", "status": r.status_code, "preview": r.text[:200], "url": url}

    reader = csv.DictReader(io.StringIO(r.text))
    feats = []
    for row in reader:
        try:
            lat = float(row.get("latitude") or 0.0)
            lon = float(row.get("longitude") or 0.0)
        except Exception:
            continue
        props = {k: v for k, v in row.items() if k not in ("latitude", "longitude")}
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props
        })
    return {"type": "FeatureCollection", "features": feats}
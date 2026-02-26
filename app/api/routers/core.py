from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
from ...services.firms_service import fetch_firms_geojson
from ...services.weather_service import get_wind

router = APIRouter(prefix="/api", tags=["api"])

# GeoJSON dosyalarını yükleme
def load_geojson(filename: str):
    """Statik verilerden GeoJSON dosyasını yükle"""
    try:
        geojson_path = Path(__file__).parent.parent.parent.parent / "static" / "data" / filename
        with open(geojson_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {
            "type": "FeatureCollection",
            "features": [],
            "error": str(e)
        }

@router.get("/firms", response_class=JSONResponse)
def get_firms(day_range: int = Query(3, ge=1, le=10)):
    res = fetch_firms_geojson(day_range)
    if isinstance(res, dict) and res.get("status", 200) >= 400 and "error" in res:
        raise HTTPException(status_code=res.get("status", 500), detail=res.get("error"))
    return res

@router.get("/fires", response_class=JSONResponse)
def get_fires(day_range: int = Query(3, ge=1, le=10)):
    """Alias for /firms endpoint - NASA FIRMS fire data"""
    res = fetch_firms_geojson(day_range)
    if isinstance(res, dict) and res.get("status", 200) >= 400 and "error" in res:
        raise HTTPException(status_code=res.get("status", 500), detail=res.get("error"))
    return res

@router.get("/fires_cached", response_class=JSONResponse)
def get_fires_cached(day_range: int = Query(3, ge=1, le=10)):
    """Alias for /firms endpoint - NASA FIRMS fire data (live tracking)"""
    res = fetch_firms_geojson(day_range)
    if isinstance(res, dict) and res.get("status", 200) >= 400 and "error" in res:
        raise HTTPException(status_code=res.get("status", 500), detail=res.get("error"))
    return res

@router.get("/wind", response_class=JSONResponse)
def api_get_wind(lat: float = Query(...), lon: float = Query(...), when_iso: str = Query(None)):
    res = get_wind(lat, lon, when_iso)
    return res

@router.get("/dams", response_class=JSONResponse)
def get_dams():
    """İzmir bölgesindeki barajlar - barajlar.geojson'dan yüklendi"""
    return load_geojson("barajlar.geojson")

@router.get("/water_sources", response_class=JSONResponse)
def get_water_sources():
    """İzmir bölgesindeki su kaynakları - water-sources.geojson'dan yüklendi"""
    return load_geojson("water-sources.geojson")

@router.get("/water_tanks", response_class=JSONResponse)
def get_water_tanks():
    """İzmir bölgesindeki su tankları - water-tank.geojson'dan yüklendi"""
    return load_geojson("water-tank.geojson")


@router.get("/fire_stations", response_class=JSONResponse)
def get_fire_stations():
    """İzmir bölgesindeki itfaiye istasyonları - fire-stations.geojson'dan yüklendi"""
    return load_geojson("fire-stations.geojson")

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from ...services.firms_service import fetch_firms_geojson
from ...services.weather_service import get_wind

router = APIRouter(prefix="/core", tags=["core"])

@router.get("/firms", response_class=JSONResponse)
def get_firms(day_range: int = Query(3, ge=1, le=16)):
    res = fetch_firms_geojson(day_range)
    if isinstance(res, dict) and res.get("status", 200) >= 400 and "error" in res:
        raise HTTPException(status_code=res.get("status", 500), detail=res.get("error"))
    return res

@router.get("/weather/wind", response_class=JSONResponse)
def api_get_wind(lat: float = Query(...), lon: float = Query(...), when_iso: str = Query(None)):
    res = get_wind(lat, lon, when_iso)
    return res

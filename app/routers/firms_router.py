from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from ..services.firms_service import fetch_firms_geojson
# Back-compat: eski importlar için alias
from ..api.routers.core import router as core_router  # re-export core router (avoid shadowing)

router = APIRouter(prefix="/firms", tags=["firms"])

@router.get("", response_class=JSONResponse)
def get_firms(day_range: int = Query(3, ge=1, le=16)):
	"""Query param: day_range (1-16). Service çağrılır, hata maplenir."""
	res = fetch_firms_geojson(day_range)
	if isinstance(res, dict) and res.get("status", 200) >= 400 and "error" in res:
		raise HTTPException(status_code=res.get("status", 500), detail=res.get("error"))
	return res

__all__ = ["router", "core_router"]

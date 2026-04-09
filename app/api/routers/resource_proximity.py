from typing import Optional, Tuple

from fastapi import APIRouter, Query

from app.services.resource_proximity_service import ResourceProximityService

router = APIRouter(prefix="/api/proximity", tags=["proximity"])

service = ResourceProximityService()


def _build_bbox(
    min_lat: Optional[float],
    min_lon: Optional[float],
    max_lat: Optional[float],
    max_lon: Optional[float],
) -> Optional[Tuple[float, float, float, float]]:
    if (
        min_lat is None
        or min_lon is None
        or max_lat is None
        or max_lon is None
    ):
        return None

    return float(min_lon), float(min_lat), float(max_lon), float(max_lat)


@router.get("/high-medium-grid")
async def get_high_medium_proximity_grid(
    cell_size: float = Query(
        0.02,
        gt=0,
        description="Grid hücresi boyutu (derece cinsinden)",
    ),
    min_lat: Optional[float] = Query(
        None, description="Minimum enlem (opsiyonel filtre)"
    ),
    min_lon: Optional[float] = Query(
        None, description="Minimum boylam (opsiyonel filtre)"
    ),
    max_lat: Optional[float] = Query(
        None, description="Maksimum enlem (opsiyonel filtre)"
    ),
    max_lon: Optional[float] = Query(
        None, description="Maksimum boylam (opsiyonel filtre)"
    ),
):
    """
    HIGH/MEDIUM risk noktalarından oluşturulan grid hücreleri için,
    her hücreyi en yakın su kaynağı ve itfaiye istasyonu ile eşleştirir.

    Dönen veri GeoJSON FeatureCollection formatındadır ve
    harita katmanı olarak doğrudan kullanılabilir.
    """
    bbox = _build_bbox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    cells = service.build_high_medium_grid_with_proximity(
        cell_size=cell_size,
        bbox=bbox,
    )

    return ResourceProximityService.to_geojson(cells=cells, cell_size=cell_size)


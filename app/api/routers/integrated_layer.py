from typing import Optional, Tuple

from fastapi import APIRouter, Query

from app.schemas.air_accessibility import AircraftType as ApiAircraftType
from app.services.air_accessibility_service import (
    AircraftType as ServiceAircraftType,
)
from app.services.integrated_layer_service import IntegratedLayerService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

service = IntegratedLayerService()


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


@router.get("/integrated-layer")
async def get_integrated_layer(
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
    aircraft_type: ApiAircraftType = Query(
        ApiAircraftType.HELICOPTER,
        description="Hava aracı tipi (hava erişilebilirlik hesabı için)",
    ),
):
    """
    Dashboard için entegre GIS katmanı döndürür.

    Her grid hücresinde:
      - ML yangın risk skoru
      - En yakın su kaynağı ve itfaiye istasyonu
      - Hava erişilebilirlik seviyesi ve skoru
    bilgileri birleştirilmiştir.

    Çıktı GeoJSON FeatureCollection formatındadır.
    """
    bbox = _build_bbox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    cells = service.build_integrated_grid(
        cell_size=cell_size,
        bbox=bbox,
        aircraft_type=ServiceAircraftType(aircraft_type.value),
    )

    return IntegratedLayerService.to_geojson(cells=cells, cell_size=cell_size)


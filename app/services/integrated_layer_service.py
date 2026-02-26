from typing import Any, Dict, List, Optional, Tuple

from app.services.resource_proximity_service import (
    ResourceProximityService,
    RiskGridCell,
)
from app.services.air_accessibility_service import (
    AirAccessibilityService,
    AircraftType as ServiceAircraftType,
    TerrainType as ServiceTerrainType,
)


class IntegratedLayerService:
    """
    Dashboard görselleştirmesi için entegre GIS katmanı üreten servis.

    Her grid hücresi için:
      - Yangın risk özeti
      - En yakın su kaynağı / itfaiye istasyonu
      - Hava erişilebilirlik skoru ve seviyesi
    bilgilerini tek bir GeoJSON katmanında birleştirir.
    """

    def __init__(self) -> None:
        self._proximity_service = ResourceProximityService()
        self._air_service = AirAccessibilityService()

    def build_integrated_grid(
        self,
        cell_size: float = 0.02,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        aircraft_type: ServiceAircraftType = ServiceAircraftType.HELICOPTER,
    ) -> List[RiskGridCell]:
        """
        Proximity + hava erişilebilirlik bilgilerini birleştirilmiş grid üzerinde hesaplar.

        :param cell_size: Grid hücresi boyutu (derece)
        :param bbox: (min_lon, min_lat, max_lon, max_lat)
        :param aircraft_type: Hava aracı tipi
        """
        # Önce risk + proximity hücrelerini üret
        cells = self._proximity_service.build_high_medium_grid_with_proximity(
            cell_size=cell_size,
            bbox=bbox,
        )

        if not cells:
            return []

        # Her hücre merkezinde hava erişilebilirliği değerlendir
        for cell in cells:
            try:
                result = self._air_service.classify_air_accessibility(
                    latitude=cell.center_lat,
                    longitude=cell.center_lon,
                    elevation=0,
                    terrain_type=ServiceTerrainType.FLAT,
                    vegetation_density=0.5,
                    aircraft_type=aircraft_type,
                )
            except Exception:
                # Hata durumunda hava alanlarını boş bırak
                continue

            cell.air_access_level = str(result.get("accessibility_level"))
            cell.air_access_score = float(result.get("score", 0.0))
            cell.air_distance_to_base_km = float(
                result.get("distance_to_base_km", 0.0)
            )
            eta = result.get("eta_minutes")
            cell.air_eta_minutes = float(eta) if eta is not None else None
            cell.air_nearest_base = str(result.get("nearest_base"))

        return cells

    @staticmethod
    def to_geojson(cells: List[RiskGridCell], cell_size: float) -> Dict[str, Any]:
        """
        ResourceProximityService'in GeoJSON çıktısını yeniden kullan.
        """
        return ResourceProximityService.to_geojson(cells=cells, cell_size=cell_size)


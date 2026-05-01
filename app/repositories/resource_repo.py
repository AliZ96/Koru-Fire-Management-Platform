from app.services.geo_service_client import GeoServiceClient
from app.services.resource_proximity_service import ResourceProximityService


class ResourceRepository:

    def __init__(self, db=None):
        self.db = db
        self.geo_client = GeoServiceClient()
        self.local_service = ResourceProximityService()

    def find_nearest(self, lat: float, lon: float, limit: int = 5):
        if self.geo_client.enabled:
            payload = self.geo_client.get_high_medium_grid(
                cell_size=0.02,
                min_lat=lat - 0.2,
                min_lon=lon - 0.2,
                max_lat=lat + 0.2,
                max_lon=lon + 0.2,
            )
            features = payload.get("features", []) if isinstance(payload, dict) else []
            rows = []
            for idx, item in enumerate(features[:limit]):
                props = item.get("properties", {})
                rows.append(
                    {
                        "id": idx + 1,
                        "name": props.get("nearest_water_name") or props.get("nearest_fire_station_name") or "Resource",
                        "type": "resource",
                        "distance": props.get("nearest_water_distance_km") or props.get("nearest_fire_station_distance_km"),
                    }
                )
            return rows
        # fallback local approximation
        cells = self.local_service.build_high_medium_grid_with_proximity(cell_size=0.02)
        rows = []
        for idx, cell in enumerate(cells[:limit]):
            rows.append(
                {
                    "id": idx + 1,
                    "name": cell.nearest_water_name or cell.nearest_fire_station_name or "Resource",
                    "type": "resource",
                    "distance": cell.nearest_water_distance_km or cell.nearest_fire_station_distance_km,
                }
            )
        return rows

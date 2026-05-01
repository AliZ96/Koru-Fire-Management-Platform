from __future__ import annotations

from typing import Any, Optional

import requests

from app.core.config import settings


class GeoServiceClient:
    def __init__(self):
        self.base_url = (settings.GEO_SERVICE_BASE_URL or "").rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def get_high_medium_grid(
        self,
        *,
        cell_size: float,
        min_lat: Optional[float],
        min_lon: Optional[float],
        max_lat: Optional[float],
        max_lon: Optional[float],
    ) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        params = {
            "cell_size": cell_size,
            "min_lat": min_lat,
            "min_lon": min_lon,
            "max_lat": max_lat,
            "max_lon": max_lon,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(
            f"{self.base_url}/proximity/high-medium-grid",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_integrated_layer(
        self,
        *,
        cell_size: float,
        min_lat: Optional[float],
        min_lon: Optional[float],
        max_lat: Optional[float],
        max_lon: Optional[float],
        aircraft_type: Optional[str],
    ) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        params = {
            "cell_size": cell_size,
            "min_lat": min_lat,
            "min_lon": min_lon,
            "max_lat": max_lat,
            "max_lon": max_lon,
            "aircraft_type": aircraft_type,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(
            f"{self.base_url}/dashboard/integrated-layer",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

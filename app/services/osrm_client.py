from __future__ import annotations

from functools import lru_cache
from typing import Any

import requests

from app.core.config import settings


class OSRMError(RuntimeError):
    pass


class OSRMClient:
    def __init__(self, base_url: str | None = None, profile: str | None = None, timeout: float = 20.0) -> None:
        self.base_url = (base_url or settings.OSRM_BASE_URL).rstrip("/")
        self.profile = profile or settings.OSRM_PROFILE
        self.timeout = timeout

    def _coord_string(self, coords: list[tuple[float, float]]) -> str:
        return ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in coords)

    def healthcheck(self) -> dict[str, Any]:
        try:
            url = f"{self.base_url}/nearest/v1/{self.profile}/27.14,38.42"
            response = requests.get(url, params={"number": 1}, timeout=5)
            response.raise_for_status()
            payload = response.json()
            return {"ok": payload.get("code") == "Ok", "code": payload.get("code"), "base_url": self.base_url}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "base_url": self.base_url}

    def distance_table_km(self, coords: list[tuple[float, float]]) -> list[list[float]]:
        if len(coords) < 2:
            return [[0.0 for _ in coords] for _ in coords]
        url = f"{self.base_url}/table/v1/{self.profile}/{self._coord_string(coords)}"
        response = requests.get(
            url,
            params={"annotations": "distance", "fallback_speed": 30},
            timeout=self.timeout,
        )
        if not response.ok:
            raise OSRMError(f"OSRM table HTTP {response.status_code}: {response.text[:200]}")
        payload = response.json()
        if payload.get("code") != "Ok":
            raise OSRMError(f"OSRM table error: {payload.get('code') or payload}")
        distances = payload.get("distances")
        if not isinstance(distances, list):
            raise OSRMError("OSRM table response missing distances")
        return [[float(v or 0.0) / 1000.0 for v in row] for row in distances]

    @lru_cache(maxsize=4096)
    def route_segment(self, from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict[str, Any]:
        url = f"{self.base_url}/route/v1/{self.profile}/{from_lon:.7f},{from_lat:.7f};{to_lon:.7f},{to_lat:.7f}"
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "alternatives": "false", "steps": "false"},
            timeout=self.timeout,
        )
        if not response.ok:
            raise OSRMError(f"OSRM route HTTP {response.status_code}: {response.text[:200]}")
        payload = response.json()
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise OSRMError(f"OSRM route error: {payload.get('code') or payload}")
        route = payload["routes"][0]
        return {
            "distance_km": float(route.get("distance") or 0.0) / 1000.0,
            "duration_min": float(route.get("duration") or 0.0) / 60.0,
            "coordinates": route.get("geometry", {}).get("coordinates") or [],
        }

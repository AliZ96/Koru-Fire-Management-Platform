from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json
import math

import pandas as pd

from app.services.air_accessibility_service import haversine_distance


@dataclass
class RiskGridCell:
    """
    Yangın risk grid hücresi ile yakınlık bilgileri.
    
    SCRUM-58: Mesafe ölçütü = Haversine (Air distance in km)
    Koordinatlar 4 ondalık basamakta tutulur.
    """
    lat_grid: float
    lon_grid: float
    center_lat: float
    center_lon: float
    risk_class: str
    combined_risk_score: float
    count: int
    polygon: List[List[List[float]]]
    nearest_water_name: Optional[str] = None
    nearest_water_distance_km: Optional[float] = None
    nearest_water_lat: Optional[float] = None
    nearest_water_lon: Optional[float] = None
    nearest_fire_station_name: Optional[str] = None
    nearest_fire_station_distance_km: Optional[float] = None
    # Entegre katman için hava erişilebilirlik alanları
    air_access_level: Optional[str] = None
    air_access_score: Optional[float] = None
    air_distance_to_base_km: Optional[float] = None
    air_eta_minutes: Optional[float] = None
    air_nearest_base: Optional[str] = None


class ResourceProximityService:
    """
    HIGH/MEDIUM yangın risk grid hücrelerini en yakın su kaynağı
    ve en yakın itfaiye istasyonu ile eşleştiren servis.
    """

    def __init__(self) -> None:
        self._root_path = Path(__file__).parent.parent.parent
        self._risk_df: Optional[pd.DataFrame] = None
        self._water_sources: Optional[List[Dict[str, Any]]] = None
        self._fire_stations: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Veri yükleyiciler
    # ------------------------------------------------------------------
    def _load_risk_data(self) -> pd.DataFrame:
        if self._risk_df is not None:
            return self._risk_df

        risk_path = self._root_path / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"
        df = pd.read_csv(risk_path)
        self._risk_df = df
        return df

    def _load_geojson_features(self, filename: str) -> List[Dict[str, Any]]:
        base_path = self._root_path / "static" / "data"
        file_path = base_path / filename
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        features = data.get("features", [])
        return [f for f in features if isinstance(f, dict)]

    def _load_water_sources(self) -> List[Dict[str, Any]]:
        if self._water_sources is not None:
            return self._water_sources

        files = [
            "barajlar.geojson",
            "ponds-lakes.geojson",
            "water-reservoirs.geojson",
            "water-sources.geojson",
            "water-tank.geojson",
        ]

        sources: List[Dict[str, Any]] = []
        for name in files:
            sources.extend(self._load_geojson_features(name))

        self._water_sources = sources
        return sources

    def _load_fire_stations(self) -> List[Dict[str, Any]]:
        if self._fire_stations is not None:
            return self._fire_stations

        stations = self._load_geojson_features("fire-stations.geojson")
        self._fire_stations = stations
        return stations

    # ------------------------------------------------------------------
    # Grid oluşturma
    # ------------------------------------------------------------------
    def build_high_medium_grid(
        self,
        cell_size: float = 0.02,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[RiskGridCell]:
        """
        HIGH/MEDIUM risk noktalarından grid tabanlı hücreler üretir.

        :param cell_size: Derece cinsinden grid hücresi boyutu
        :param bbox: (min_lon, min_lat, max_lon, max_lat) şeklinde opsiyonel sınır kutusu
        """
        if cell_size <= 0 or math.isnan(cell_size):
            raise ValueError("cell_size must be positive")

        df = self._load_risk_data()

        # Yalnızca HIGH/MEDIUM risk sınıfları
        df = df[df["predicted_risk_class"].isin(["HIGH_RISK", "MEDIUM_RISK"])]

        if df.empty:
            return []

        # BBox filtresi (opsiyonel)
        if bbox is not None:
            min_lon, min_lat, max_lon, max_lat = bbox
            df = df[
                (df["longitude"] >= min_lon)
                & (df["longitude"] <= max_lon)
                & (df["latitude"] >= min_lat)
                & (df["latitude"] <= max_lat)
            ]

        if df.empty:
            return []

        # Grid koordinatları
        df = df.copy()
        df["lat_grid"] = (df["latitude"] / cell_size).astype(int) * cell_size
        df["lon_grid"] = (df["longitude"] / cell_size).astype(int) * cell_size

        grouped = df.groupby(["lat_grid", "lon_grid"])

        cells: List[RiskGridCell] = []
        half_size = cell_size / 2.0

        for (lat_grid, lon_grid), group in grouped:
            # Risk sınıfı için mode
            mode_series = group["predicted_risk_class"].mode()
            if not mode_series.empty:
                risk_class = str(mode_series.iloc[0])
            else:
                risk_class = "MEDIUM_RISK"

            combined_score = float(group["combined_risk_score"].mean())
            count = int(len(group))

            lat = float(lat_grid)
            lon = float(lon_grid)

            coordinates = [
                [
                    [lon - half_size, lat - half_size],
                    [lon + half_size, lat - half_size],
                    [lon + half_size, lat + half_size],
                    [lon - half_size, lat + half_size],
                    [lon - half_size, lat - half_size],
                ]
            ]

            cells.append(
                RiskGridCell(
                    lat_grid=lat,
                    lon_grid=lon,
                    center_lat=lat,
                    center_lon=lon,
                    risk_class=risk_class,
                    combined_risk_score=combined_score,
                    count=count,
                    polygon=coordinates,
                )
            )

        return cells

    # ------------------------------------------------------------------
    # Proximity hesapları
    # ------------------------------------------------------------------
    @staticmethod
    def _is_valid_coordinate(lon: float, lat: float) -> bool:
        """
        Koordinatın geçerli aralıkta olup olmadığını kontrol et.
        SCRUM-58: İzmir bölgesi ~ İzmir (37.5° - 39.5°N, 26.5° - 27.5°E)
        """
        return (26.5 <= lon <= 27.5) and (37.5 <= lat <= 39.5)

    @staticmethod
    def _extract_feature_coords(feature: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """
        GeoJSON Feature içinden temsili (lon, lat) koordinatı çıkarır.
        Point için doğrudan, Polygon/MultiPolygon için ilk köşeyi alır.
        
        SCRUM-58: Koordinat validasyonu + hata yönetimi
        """
        try:
            geom = feature.get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates")

            if not gtype or coords is None:
                return None

            if gtype == "Point":
                lon, lat = coords
            elif gtype == "Polygon":
                lon, lat = coords[0][0]
            elif gtype == "MultiPolygon":
                lon, lat = coords[0][0][0]
            else:
                return None

            lon = float(lon)
            lat = float(lat)
            
            # Koordinat doğrulaması
            if not ResourceProximityService._is_valid_coordinate(lon, lat):
                return None
                
            return lon, lat
        except Exception:
            return None

    def _find_nearest(
        self,
        lat: float,
        lon: float,
        features: List[Dict[str, Any]],
        default_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        SCRUM-58: En yakın kaynağı haversine distances ile bul.
        
        Mesafe ölçütü: Haversine (koordinatlar arasında doğrudan air distance)
        Birim: Kilometre
        Koordinat Doğrulaması: İzmir sınırları içinde
        """
        best: Optional[Dict[str, Any]] = None

        for feature in features:
            coords = self._extract_feature_coords(feature)
            if coords is None:
                continue

            flon, flat = coords
            
            # Mesafe hesabı (haversine)
            distance_km = haversine_distance(lat, lon, flat, flon)

            props = feature.get("properties", {}) or {}
            name = props.get("name") or props.get("name:tr") or default_type

            if best is None or distance_km < best["distance_km"]:
                best = {
                    "name": str(name),
                    "distance_km": float(round(distance_km, 3)),
                    "lat": float(round(flat, 4)),
                    "lon": float(round(flon, 4)),
                }

        return best

    def build_high_medium_grid_with_proximity(
        self,
        cell_size: float = 0.02,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[RiskGridCell]:
        """
        Grid hücrelerini oluşturur ve her hücre için en yakın
        su kaynağı ve itfaiye istasyonunu hesaplar.
        
        SCRUM-58: Koordinat doğrulaması + tutarlılık kontrolleri
        """
        cells = self.build_high_medium_grid(cell_size=cell_size, bbox=bbox)
        if not cells:
            return []

        water_sources = self._load_water_sources()
        fire_stations = self._load_fire_stations()

        validation_issues = []

        for i, cell in enumerate(cells):
            # Su kaynağı yakınlığı
            nearest_water = self._find_nearest(
                lat=cell.center_lat,
                lon=cell.center_lon,
                features=water_sources,
                default_type="Water source",
            )
            if nearest_water is not None:
                cell.nearest_water_name = nearest_water["name"]
                cell.nearest_water_distance_km = nearest_water["distance_km"]
                cell.nearest_water_lat = nearest_water["lat"]
                cell.nearest_water_lon = nearest_water["lon"]
            else:
                validation_issues.append(
                    f"Cell[{i}]: Su kaynağı bulunamadı (lat={cell.center_lat}, lon={cell.center_lon})"
                )

            # İtfaiye istasyonu yakınlığı
            nearest_fs = self._find_nearest(
                lat=cell.center_lat,
                lon=cell.center_lon,
                features=fire_stations,
                default_type="Fire station",
            )
            if nearest_fs is not None:
                cell.nearest_fire_station_name = nearest_fs["name"]
                cell.nearest_fire_station_distance_km = nearest_fs["distance_km"]
                cell.nearest_fire_station_lat = nearest_fs["lat"]
                cell.nearest_fire_station_lon = nearest_fs["lon"]
            else:
                validation_issues.append(
                    f"Cell[{i}]: İtfaiye istasyonu bulunamadı (lat={cell.center_lat}, lon={cell.center_lon})"
                )

        return cells

    @staticmethod
    def to_geojson(cells: List[RiskGridCell], cell_size: float) -> Dict[str, Any]:
        """
        RiskGridCell listesini GeoJSON FeatureCollection formatına çevirir.
        
        SCRUM-58: Tam eşleme şeması:
        - nearest_water_id: Su kaynağının adı
        - nearest_water_distance: Haversine mesafesi (km)
        - nearest_water_lat/lon: Kaynak koordinatları
        - nearest_station_id: İtfaiye istasyonunun adı
        - nearest_station_distance: Haversine mesafesi (km)
        - nearest_station_lat/lon: İstasyon koordinatları
        """
        features: List[Dict[str, Any]] = []

        for cell in cells:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": cell.polygon,
                    },
                    "properties": {
                        "center_lat": round(cell.center_lat, 4),
                        "center_lon": round(cell.center_lon, 4),
                        "risk_class": cell.risk_class,
                        "combined_risk_score": round(cell.combined_risk_score, 4),
                        "point_count": cell.count,
                        "nearest_water_name": cell.nearest_water_name,
                        "nearest_water_distance_km": round(cell.nearest_water_distance_km, 3)
                        if cell.nearest_water_distance_km is not None
                        else None,
                        "nearest_fire_station_name": cell.nearest_fire_station_name,
                        "nearest_fire_station_distance_km": round(
                            cell.nearest_fire_station_distance_km, 3
                        )
                        if cell.nearest_fire_station_distance_km is not None
                        else None,
                        # Hava erişilebilirlik özet alanları (opsiyonel)
                        "air_access_level": cell.air_access_level,
                        "air_access_score": round(cell.air_access_score, 1)
                        if cell.air_access_score is not None
                        else None,
                        "air_distance_to_base_km": round(
                            cell.air_distance_to_base_km, 2
                        )
                        if cell.air_distance_to_base_km is not None
                        else None,
                        "air_eta_minutes": round(cell.air_eta_minutes, 1)
                        if cell.air_eta_minutes is not None
                        else None,
                        "air_nearest_base": cell.air_nearest_base,
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
            "total_cells": len(features),
            "cell_size": cell_size,
            "distance_metric": "haversine_km",
            "schema_version": "scrum58_finalized",
        }


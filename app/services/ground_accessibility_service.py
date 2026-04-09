"""
Kara Erişilebilirlik Servisi (Sprint 6 / LLF-2.2)

Sorumluluklar:
  - izmir_ground_accessibility_v1.csv üzerinden kara erişilebilirlik verisini sunar
  - izmir_future_fire_risk_dataset.csv ile spatial join yaparak entegre görünüm üretir
  - GeoJSON, nokta listesi ve özet istatistik formatlarını destekler
  - Tek nokta sınıflandırması (en yakın komşu) sağlar
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

GROUND_ACCESS_COLORS: Dict[str, str] = {
    "HIGH": "#2ecc71",
    "MEDIUM": "#f39c12",
    "LOW": "#e74c3c",
    "NO_ACCESS": "#8b0000",
}

PRIORITY_COLORS: Dict[str, str] = {
    "CRITICAL": "#8b0000",
    "HIGH": "#e74c3c",
    "MEDIUM": "#f39c12",
    "LOW": "#2ecc71",
}

# (fire_risk_class, ground_access_class) → priority_level
PRIORITY_MAP: Dict[Tuple[str, str], str] = {
    ("HIGH_RISK", "NO_ACCESS"): "CRITICAL",
    ("HIGH_RISK", "LOW"):       "HIGH",
    ("HIGH_RISK", "MEDIUM"):    "HIGH",
    ("HIGH_RISK", "HIGH"):      "MEDIUM",
    ("MEDIUM_RISK", "NO_ACCESS"): "HIGH",
    ("MEDIUM_RISK", "LOW"):       "MEDIUM",
    ("MEDIUM_RISK", "MEDIUM"):    "MEDIUM",
    ("MEDIUM_RISK", "HIGH"):      "LOW",
    ("LOW_RISK", "NO_ACCESS"):    "MEDIUM",
    ("LOW_RISK", "LOW"):          "LOW",
    ("LOW_RISK", "MEDIUM"):       "LOW",
    ("LOW_RISK", "HIGH"):         "LOW",
    ("SAFE_UNBURNABLE", "NO_ACCESS"): "LOW",
    ("SAFE_UNBURNABLE", "LOW"):       "LOW",
    ("SAFE_UNBURNABLE", "MEDIUM"):    "LOW",
    ("SAFE_UNBURNABLE", "HIGH"):      "LOW",
}

# Hava müdahalesi gereken durum: kara erişimi yetersiz + yüksek/orta risk
AIR_REQUIRED_GROUND = {"NO_ACCESS", "LOW"}
AIR_REQUIRED_FIRE   = {"HIGH_RISK", "MEDIUM_RISK"}


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _polygon_coords(
    center_lat: float, center_lon: float, cell_size: float
) -> List[List[List[float]]]:
    """GeoJSON Polygon koordinatları (kare hücre)."""
    h = cell_size / 2
    return [[
        [center_lon - h, center_lat - h],
        [center_lon + h, center_lat - h],
        [center_lon + h, center_lat + h],
        [center_lon - h, center_lat + h],
        [center_lon - h, center_lat - h],
    ]]


def _safe_float(val: Any) -> Optional[float]:
    """NaN / None güvenli float dönüşümü."""
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Ana Servis
# ---------------------------------------------------------------------------

class GroundAccessibilityService:
    """
    Kara erişilebilirlik ve entegre risk-erişilebilirlik verilerini sunar.

    Veri kaynakları
    ---------------
    - scripts/llf22/output/izmir_ground_accessibility_v1.csv
        Kara erişilebilirlik sınıflandırması (dist_to_road_m, slope_deg,
        ground_access_class, ground_access_score)
    - database/ml-map/izmir_future_fire_risk_dataset.csv
        ML tabanlı yangın risk tahminleri (fire_probability,
        combined_risk_score, predicted_risk_class)
    """

    def __init__(self) -> None:
        self._root = Path(__file__).parent.parent.parent
        self._ground_df: Optional[pd.DataFrame] = None
        self._fire_df: Optional[pd.DataFrame] = None
        # Vektörel nearest-neighbor için önbellek
        self._ground_lats: Optional[np.ndarray] = None
        self._ground_lons: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Veri yükleyiciler
    # ------------------------------------------------------------------

    def _load_ground(self) -> pd.DataFrame:
        if self._ground_df is not None:
            return self._ground_df
        path = (
            self._root
            / "scripts" / "llf22" / "output"
            / "izmir_ground_accessibility_v1.csv"
        )
        df = pd.read_csv(path)
        self._ground_df = df
        self._ground_lats = df["center_lat"].to_numpy(dtype=float)
        self._ground_lons = df["center_lon"].to_numpy(dtype=float)
        return df

    def _load_fire(self) -> pd.DataFrame:
        if self._fire_df is not None:
            return self._fire_df
        path = (
            self._root
            / "database" / "ml-map"
            / "izmir_future_fire_risk_dataset.csv"
        )
        df = pd.read_csv(path)
        self._fire_df = df
        return df

    # ------------------------------------------------------------------
    # Yardımcı metodlar
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_bbox(
        df: pd.DataFrame,
        bbox: Optional[Tuple[float, float, float, float]],
        lat_col: str = "center_lat",
        lon_col: str = "center_lon",
    ) -> pd.DataFrame:
        if bbox is None:
            return df
        min_lon, min_lat, max_lon, max_lat = bbox
        return df[
            (df[lon_col] >= min_lon) & (df[lon_col] <= max_lon)
            & (df[lat_col] >= min_lat) & (df[lat_col] <= max_lat)
        ]

    def _nearest_ground_idx(self, lat: float, lon: float) -> int:
        """Vektörel NN – en yakın ground-access hücresinin indeksini döndürür."""
        # Ensure loaded
        self._load_ground()
        dlat = self._ground_lats - lat  # type: ignore[operator]
        dlon = self._ground_lons - lon  # type: ignore[operator]
        return int(np.argmin(dlat ** 2 + dlon ** 2))

    # ------------------------------------------------------------------
    # Kara Erişilebilirlik Endpoint'leri
    # ------------------------------------------------------------------

    def get_ground_map(
        self,
        access_class: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cell_size: float = 0.03,
    ) -> Dict[str, Any]:
        """
        Kara erişilebilirlik haritasını GeoJSON FeatureCollection olarak döndürür.
        Her hücre bir Polygon özelliğidir.
        """
        df = self._apply_bbox(self._load_ground().copy(), bbox)
        if access_class:
            df = df[df["ground_access_class"] == access_class.upper()]

        features: List[Dict[str, Any]] = []
        for row in df.itertuples(index=False):
            clat = float(row.center_lat)
            clon = float(row.center_lon)
            cls_ = str(row.ground_access_class)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": _polygon_coords(clat, clon, cell_size),
                },
                "properties": {
                    "center_lat": clat,
                    "center_lon": clon,
                    "ground_access_class": cls_,
                    "ground_access_score": int(row.ground_access_score),
                    "dist_to_road_m": _safe_float(getattr(row, "dist_to_road_m", None)),
                    "slope_deg": _safe_float(getattr(row, "slope_deg", None)),
                    "color": GROUND_ACCESS_COLORS.get(cls_, "#95a5a6"),
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "total": len(features),
            "metadata": {
                "cell_size": cell_size,
                "access_class_filter": access_class,
            },
        }

    def get_ground_points(
        self,
        access_class: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        limit: int = 5000,
    ) -> Dict[str, Any]:
        """
        Kara erişilebilirlik noktalarını liste formatında döndürür.
        Tablo/analiz araçları için uygundur.
        """
        df = self._apply_bbox(self._load_ground().copy(), bbox)
        if access_class:
            df = df[df["ground_access_class"] == access_class.upper()]
        df = df.head(limit)

        cols = [
            "center_lat", "center_lon",
            "ground_access_class", "ground_access_score",
            "dist_to_road_m", "slope_deg",
        ]
        available = [c for c in cols if c in df.columns]
        records = (
            df[available]
            .where(pd.notna(df[available]), None)
            .to_dict("records")
        )

        return {
            "points": records,
            "total": len(records),
            "access_class_filter": access_class,
        }

    def get_ground_summary(self) -> Dict[str, Any]:
        """
        Kara erişilebilirlik özet istatistiklerini döndürür.

        Dönüş
        -----
        - Erişilebilirlik sınıfı dağılımı
        - Ortalama yol mesafesi ve eğim
        - Erişilemeyen alan yüzdesi
        """
        df = self._load_ground()

        dist_valid = pd.to_numeric(df.get("dist_to_road_m", pd.Series()), errors="coerce").dropna()
        slope_valid = pd.to_numeric(df.get("slope_deg", pd.Series()), errors="coerce").dropna()
        distribution: Dict[str, int] = df["ground_access_class"].value_counts().to_dict()
        no_access = int(distribution.get("NO_ACCESS", 0))
        n = len(df)

        return {
            "total_cells": n,
            "ground_access_distribution": distribution,
            "average_dist_to_road_m": round(float(dist_valid.mean()), 2) if len(dist_valid) else None,
            "average_slope_deg": round(float(slope_valid.mean()), 3) if len(slope_valid) else None,
            "no_access_count": no_access,
            "no_access_percentage": round(no_access / n * 100, 2) if n else 0.0,
        }

    def classify_point(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Verilen koordinata en yakın grid hücresini bulur ve kara
        erişilebilirlik sınıfını döndürür (en yakın komşu interpolasyonu).
        """
        df = self._load_ground()
        idx = self._nearest_ground_idx(lat, lon)
        row = df.iloc[idx]

        clat = float(row["center_lat"])
        clon = float(row["center_lon"])
        dist_km = _haversine_km(lat, lon, clat, clon)
        cls_ = str(row["ground_access_class"])

        return {
            "input": {"lat": lat, "lon": lon},
            "nearest_cell": {"lat": clat, "lon": clon},
            "distance_to_cell_km": round(dist_km, 3),
            "ground_access_class": cls_,
            "ground_access_score": int(row["ground_access_score"]),
            "dist_to_road_m": _safe_float(row.get("dist_to_road_m")),
            "slope_deg": _safe_float(row.get("slope_deg")),
            "color": GROUND_ACCESS_COLORS.get(cls_, "#95a5a6"),
        }

    # ------------------------------------------------------------------
    # Entegre Risk-Erişilebilirlik Endpoint'leri
    # ------------------------------------------------------------------

    def get_integrated_map(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cell_size: float = 0.03,
        min_fire_risk: Optional[str] = None,
        air_required_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Her yangın-risk grid hücresine en yakın kara erişilebilirlik hücresini
        eşleştirir; entegre GeoJSON FeatureCollection döndürür.

        Parametreler
        ------------
        bbox            : (min_lon, min_lat, max_lon, max_lat) filtresi
        cell_size       : Poligon boyutu (derece)
        min_fire_risk   : Minimum yangın riski filtresi (ör. "MEDIUM_RISK")
        air_required_only: Sadece hava müdahalesi gereken hücreleri getir

        Her özelliğin properties alanı
        -------------------------------
        fire_risk_class, fire_probability, high_fire_probability,
        combined_risk_score, ground_access_class, ground_access_score,
        dist_to_road_m, slope_deg, air_access_required, priority_level, color
        """
        fire_df = self._apply_bbox(
            self._load_fire().copy(),
            bbox,
            lat_col="latitude",
            lon_col="longitude",
        )

        # Risk eşiği filtresi
        if min_fire_risk:
            risk_order = {
                "SAFE_UNBURNABLE": 0, "LOW_RISK": 1,
                "MEDIUM_RISK": 2, "HIGH_RISK": 3,
            }
            threshold = risk_order.get(min_fire_risk.upper(), 0)
            fire_df = fire_df[
                fire_df["predicted_risk_class"].map(
                    lambda x: risk_order.get(x, 0) >= threshold
                )
            ]

        if fire_df.empty:
            return {
                "type": "FeatureCollection",
                "features": [],
                "total": 0,
                "metadata": {"cell_size": cell_size},
            }

        # Vektörel NN için ground array'lerini yükle
        ground_df = self._load_ground()
        g_lats = self._ground_lats  # type: ignore[assignment]
        g_lons = self._ground_lons  # type: ignore[assignment]

        features: List[Dict[str, Any]] = []
        fire_dist: Dict[str, int] = {}
        access_dist: Dict[str, int] = {}
        air_count = 0

        for row in fire_df.itertuples(index=False):
            flat = float(row.latitude)
            flon = float(row.longitude)

            # En yakın kara-erişim hücresi (vektörel)
            dlat = g_lats - flat
            dlon = g_lons - flon
            g_idx = int(np.argmin(dlat ** 2 + dlon ** 2))
            g_row = ground_df.iloc[g_idx]

            fire_risk = str(row.predicted_risk_class)
            g_access = str(g_row["ground_access_class"])

            air_required = (
                g_access in AIR_REQUIRED_GROUND
                and fire_risk in AIR_REQUIRED_FIRE
            )
            priority = PRIORITY_MAP.get((fire_risk, g_access), "LOW")

            if air_required_only and not air_required:
                continue

            fire_dist[fire_risk] = fire_dist.get(fire_risk, 0) + 1
            access_dist[g_access] = access_dist.get(g_access, 0) + 1
            if air_required:
                air_count += 1

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": _polygon_coords(flat, flon, cell_size),
                },
                "properties": {
                    "center_lat": flat,
                    "center_lon": flon,
                    "fire_risk_class": fire_risk,
                    "fire_probability": round(float(row.fire_probability), 4),
                    "high_fire_probability": round(float(row.high_fire_probability), 4),
                    "combined_risk_score": round(float(row.combined_risk_score), 4),
                    "ground_access_class": g_access,
                    "ground_access_score": int(g_row["ground_access_score"]),
                    "dist_to_road_m": _safe_float(g_row.get("dist_to_road_m")),
                    "slope_deg": _safe_float(g_row.get("slope_deg")),
                    "air_access_required": air_required,
                    "priority_level": priority,
                    "color": PRIORITY_COLORS.get(priority, "#95a5a6"),
                },
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "total": len(features),
            "metadata": {
                "cell_size": cell_size,
                "air_access_required_count": air_count,
                "fire_risk_distribution": fire_dist,
                "ground_access_distribution": access_dist,
                "min_fire_risk_filter": min_fire_risk,
                "air_required_only": air_required_only,
            },
        }

    def get_integrated_summary(self) -> Dict[str, Any]:
        """
        Yangın riski ve kara erişilebilirliğinin kombine dağılımını döndürür.

        Performans: 5184 yangın hücresi × 2076 kara hücresi için vektörel NN
        kullanılır; tüm tablo tek geçişte hesaplanır.
        """
        fire_df = self._load_fire()
        ground_df = self._load_ground()
        g_lats = self._ground_lats  # type: ignore[assignment]
        g_lons = self._ground_lons  # type: ignore[assignment]

        fire_lats = fire_df["latitude"].to_numpy(dtype=float)
        fire_lons = fire_df["longitude"].to_numpy(dtype=float)
        fire_risks = fire_df["predicted_risk_class"].to_numpy()

        fire_dist: Dict[str, int] = {}
        access_dist: Dict[str, int] = {}
        critical_count = 0
        air_only_count = 0
        joint_high_no_access = 0

        for i in range(len(fire_df)):
            dlat = g_lats - fire_lats[i]
            dlon = g_lons - fire_lons[i]
            g_idx = int(np.argmin(dlat ** 2 + dlon ** 2))
            g_access = str(ground_df.iloc[g_idx]["ground_access_class"])
            fire_risk = str(fire_risks[i])

            fire_dist[fire_risk] = fire_dist.get(fire_risk, 0) + 1
            access_dist[g_access] = access_dist.get(g_access, 0) + 1

            if fire_risk == "HIGH_RISK" and g_access == "NO_ACCESS":
                joint_high_no_access += 1
            if PRIORITY_MAP.get((fire_risk, g_access)) == "CRITICAL":
                critical_count += 1
            if g_access in AIR_REQUIRED_GROUND and fire_risk in AIR_REQUIRED_FIRE:
                air_only_count += 1

        return {
            "total_cells": len(fire_df),
            "fire_risk_distribution": fire_dist,
            "ground_access_distribution": access_dist,
            "critical_zones_count": critical_count,
            "air_only_access_count": air_only_count,
            "joint_high_risk_no_access": joint_high_no_access,
        }

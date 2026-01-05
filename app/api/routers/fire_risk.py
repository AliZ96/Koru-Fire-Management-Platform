"""
Yangın risk verileri için API router ve kümeleme yardımcıları.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from sklearn.cluster import DBSCAN

router = APIRouter(prefix="/api/fire-risk", tags=["fire-risk"])

# Veri konumu (repo kökünden) – birden fazla olası dosya için fallback listesi
BASE_DIR = Path(__file__).resolve().parents[3]
RISK_DATA_PATHS = [
    BASE_DIR / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv",
    BASE_DIR / "data" / "ml-trained-data" / "izmir_risk_map.csv",
]
# İzmir kabaca bbox (lon_min, lat_min, lon_max, lat_max)
IZMIR_BBOX = (26.0, 37.5, 28.8, 39.5)


@lru_cache()
def _load_risk_dataframe() -> pd.DataFrame:
    """
    Risk verisini tek seferlik yükle ve cache'le.
    Birden fazla olası path varsa ilk bulunanı kullan.
    """
    for path in RISK_DATA_PATHS:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception:
                continue
    return pd.DataFrame()


def load_risk_data() -> pd.DataFrame:
    """
    Cache'lenmiş risk verisinin bir kopyasını döndür.
    """
    return _load_risk_dataframe().copy()


def _normalize_points(df: pd.DataFrame, limit: int) -> List[dict]:
    """
    Farklı kolon adlarını tek bir nokta yapısına dönüştür.
    """
    if df.empty:
        return []

    cols = {
        "lat": "center_lat" if "center_lat" in df.columns else "latitude",
        "lon": "center_lon" if "center_lon" in df.columns else "longitude",
    }

    score_cols = [c for c in ["high_risk_score", "combined_risk_score", "fire_prob"] if c in df.columns]
    class_col = "predicted_risk" if "predicted_risk" in df.columns else "predicted_risk_class"

    points: List[dict] = []
    for row in df.head(limit).itertuples():
        lat = getattr(row, cols["lat"], None)
        lon = getattr(row, cols["lon"], None)
        if lat is None or lon is None:
            continue

        score = 0.0
        for col in score_cols:
            value = getattr(row, col, None)
            if value is not None:
                score = float(value)
                break

        points.append(
            {
                "lat": float(lat),
                "lon": float(lon),
                "risk_score": float(score),
                "risk_class": getattr(row, class_col, "") if class_col in df.columns else "",
            }
        )
    return points


def _cluster_to_zones(
    points: List[dict],
    eps_km: float = 5.0,
    min_samples: int = 3,
    min_cluster_size: int = 5,
) -> List[dict]:
    """
    Noktaları DBSCAN ile kümelere ayırıp bölge özetleri çıkar.
    """
    if not points:
        return []

    coords = np.array([[p["lat"], p["lon"]] for p in points], dtype=float)
    coords_rad = np.radians(coords)
    eps_rad = eps_km / 6371.0  # Dünya yarıçapı ~6371 km

    model = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
    labels = model.fit_predict(coords_rad)

    zones: List[dict] = []
    for label in set(labels):
        if label == -1:
            continue

        idx = np.where(labels == label)[0]
        if len(idx) < min_cluster_size:
            continue

        cluster_pts = [points[i] for i in idx]
        lats = [p["lat"] for p in cluster_pts]
        lons = [p["lon"] for p in cluster_pts]
        risks = [p.get("risk_score", 0.0) or 0.0 for p in cluster_pts]

        zones.append(
            {
                "zone_id": int(label),
                "bbox": [float(min(lons)), float(min(lats)), float(max(lons)), float(max(lats))],
                "avg_risk": float(np.mean(risks)),
                "count": int(len(cluster_pts)),
            }
        )

    return zones


@router.get("/points")
async def get_fire_risk_points(
    risk_class: Optional[str] = Query(None),
    limit: int = Query(50000, ge=1, le=100000),
):
    """
    Yangın risk noktalarını GeoJSON FeatureCollection olarak döndür.
    Frontend beklediği için geometry=Point, properties içinde risk_class ve skorlar sağlanır.
    """
    df = load_risk_data()
    if df.empty:
        return {"type": "FeatureCollection", "features": [], "total": 0}

    if risk_class:
        class_col = "predicted_risk" if "predicted_risk" in df.columns else "predicted_risk_class"
        if class_col in df.columns:
            df = df[df[class_col] == risk_class]

    points = _normalize_points(df, limit)
    features = []
    for p in points:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                "properties": {
                    "risk_class": p.get("risk_class", ""),
                    "fire_probability": p.get("risk_score", 0.0),
                    "high_fire_probability": p.get("risk_score", 0.0),
                    "combined_risk_score": p.get("risk_score", 0.0),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features, "total": len(features)}


@router.get("/zones")
async def get_fire_risk_zones(
    eps_km: float = Query(5.0, gt=0),
    min_samples: int = Query(3, ge=1),
    min_cluster_size: int = Query(5, ge=1),
    limit: int = Query(5000, ge=1, le=50000),
):
    """
    Noktaları kümelere ayırarak risk bölgelerini döndür.
    """
    df = load_risk_data()
    if df.empty:
        return {"zones": [], "total": 0}

    points = _normalize_points(df, limit)
    zones = _cluster_to_zones(points, eps_km=eps_km, min_samples=min_samples, min_cluster_size=min_cluster_size)
    return {"zones": zones, "total": len(zones)}


@router.get("/zones/top")
async def get_top_risk_zones(
    n: int = Query(5, ge=1, le=50),
    eps_km: float = Query(5.0, gt=0),
    min_samples: int = Query(3, ge=1),
    min_cluster_size: int = Query(5, ge=1),
    limit: int = Query(5000, ge=1, le=50000),
):
    """
    Ortalama riskine göre en yüksek n bölgeyi döndür.
    """
    zone_payload = await get_fire_risk_zones(eps_km, min_samples, min_cluster_size, limit)  # type: ignore[arg-type]
    zones = zone_payload["zones"]
    sorted_zones = sorted(zones, key=lambda z: z["avg_risk"], reverse=True)
    return {"zones": sorted_zones[:n], "total": len(sorted_zones)}


@router.get("/heatmap-data")
async def get_heatmap_data(
    limit: int = Query(50000, ge=1, le=50000),
    cell_size: float = Query(0.05, gt=0),
):
    """
    Heatmap için küçük kare poligonlardan oluşan FeatureCollection döndür.
    Frontend polygon beklediği için her nokta etrafında küçük kare üretiyoruz.
    """
    df = load_risk_data()
    if df.empty:
        return {"type": "FeatureCollection", "features": [], "total_cells": 0, "cell_size": cell_size}

    # Normalize ve bbox filtresi
    points = _normalize_points(df, limit=limit)
    lon_min, lat_min, lon_max, lat_max = IZMIR_BBOX
    points = [
        p for p in points
        if lon_min <= p["lon"] <= lon_max and lat_min <= p["lat"] <= lat_max
    ]
    points = points[:limit]
    half = cell_size / 2.0
    features = []
    for p in points:
        lat = p["lat"]
        lon = p["lon"]
        score = p.get("risk_score", 0.0)
        coords = [
            [
                [lon - half, lat - half],
                [lon + half, lat - half],
                [lon + half, lat + half],
                [lon - half, lat + half],
                [lon - half, lat - half],
            ]
        ]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": coords},
                "properties": {
                    "combined_risk_score": float(score),
                    "fire_probability": float(score),
                    "risk_class": p.get("risk_class", ""),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features, "total_cells": len(features), "cell_size": cell_size}


@router.get("/statistics")
async def get_risk_statistics():
    """
    Risk verisi için temel istatistikler.
    """
    df = load_risk_data()
    if df.empty:
        return {"total_points": 0}

    return {
        "total_points": int(len(df)),
    }

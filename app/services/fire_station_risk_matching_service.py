"""
S8-4 Fire Station <-> Risk Point Matching
=========================================
Her risk noktasını en yakın itfaiye istasyonu ile eşleştirir (nearest neighbour).
"""

import csv
import math
from pathlib import Path
from typing import Any, Dict, List


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)), 4)


def _load_fire_stations(root: Path) -> List[Dict[str, Any]]:
    """izmir_itfaiye_master_dataset.csv'den itfaiye listesi yükle."""
    path = root / "scripts" / "llf22" / "output" / "izmir_itfaiye_master_dataset.csv"
    if not path.exists():
        return []
    stations = []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r, 1):
            try:
                stations.append({
                    "id": i,
                    "name": row.get("station_name", "Bilinmiyor"),
                    "lat": float(row["latitude"]),
                    "lon": float(row["longitude"]),
                })
            except (ValueError, KeyError):
                continue
    return stations


def _load_risk_points(root: Path) -> List[Dict[str, Any]]:
    """izmir_fire_points_filtered2.csv'den risk noktalarını yükle."""
    path = root / "scripts" / "llf22" / "output" / "izmir_fire_points_filtered2.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                rows.append({
                    "id": int(row["id"]),
                    "risk_class": row["risk_class"],
                    "center_lat": float(row["center_lat"]),
                    "center_lon": float(row["center_lon"]),
                })
            except (ValueError, KeyError):
                continue
    return rows


def build_matching(root: Path | None = None) -> List[Dict[str, Any]]:
    """
    Tüm risk noktalarını en yakın itfaiye ile eşleştir.

    Returns
    -------
    list[dict]  Her eleman: risk_id, risk_class, center_lat, center_lon,
                station_id, station_name, station_lat, station_lon, distance_km
    """
    if root is None:
        root = Path(__file__).resolve().parent.parent.parent

    stations = _load_fire_stations(root)
    if not stations:
        return []

    risk_points = _load_risk_points(root)
    if not risk_points:
        return []

    results = []
    for row in risk_points:
        risk_lat = row["center_lat"]
        risk_lon = row["center_lon"]
        best = None
        best_dist = float("inf")

        for st in stations:
            d = _haversine_km(risk_lat, risk_lon, st["lat"], st["lon"])
            if d < best_dist:
                best_dist = d
                best = st

        if best:
            results.append({
                "risk_id": row["id"],
                "risk_class": row["risk_class"],
                "center_lat": risk_lat,
                "center_lon": risk_lon,
                "station_id": best["id"],
                "station_name": best["name"],
                "station_lat": best["lat"],
                "station_lon": best["lon"],
                "distance_km": round(best_dist, 4),
            })

    return results


def matching_to_geojson(matching: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Eşleşmeyi GeoJSON FeatureCollection olarak döndür.
    Her feature: risk noktası + properties'ta station bilgisi ve distance_km.
    """
    features = []
    # Her istasyon için tutarlı bir cluster_id üretelim ki harita tarafında
    # "cluster coloring" yapılabilsin. Burada küme kimliği olarak istasyon ID
    # kullanılıyor (örn. cluster_3 -> station 3'ün hizmet kümesi gibi).
    station_cluster_ids: Dict[Any, str] = {}

    for m in matching:
        station_id = m["station_id"]
        if station_id not in station_cluster_ids:
            station_cluster_ids[station_id] = f"cluster_{station_id}"
        cluster_id = station_cluster_ids[station_id]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [m["center_lon"], m["center_lat"]],
            },
            "properties": {
                "risk_id": m["risk_id"],
                "risk_class": m["risk_class"],
                # Talebe (demand) karşılık gelen her risk noktası için şimdilik
                # 1 birimlik talep varsayıyoruz; ileride pipeline'dan gerçek
                # demand değeri beslenebilir.
                "demand": 1,
                "cluster_id": cluster_id,
                "station_id": station_id,
                "station_name": m["station_name"],
                "distance_km": m["distance_km"],
            },
        })
    return {"type": "FeatureCollection", "features": features}

"""Yangın risk verileri için API router ve yardımcı fonksiyonlar."""

from pathlib import Path
from typing import List, Optional
from functools import lru_cache

from fastapi import APIRouter, Query
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

router = APIRouter(prefix="/api/fire-risk", tags=["fire-risk"])

# CSV dosya yolları
# 1) Sprint-8/9 pipeline kaynağı (öncelikli)
PIPELINE_RISK_DATA_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "llf22"
    / "output"
    / "izmir_fire_points_filtered2.csv"
)
# 2) ML map kaynağı (fallback)
ML_RISK_DATA_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "database"
    / "ml-map"
    / "izmir_future_fire_risk_dataset.csv"
)

# Risk sınıflarına göre renkler
RISK_COLORS = {
    "SAFE_UNBURNABLE": "#2ecc71",      # Yeşil - Güvenli
    "LOW_RISK": "#f39c12",              # Turuncu - Düşük Risk
    "MEDIUM_RISK": "#e74c3c",           # Kırmızı - Orta Risk
    "HIGH_RISK": "#8b0000",             # Koyu Kırmızı - Yüksek Risk
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Iki koordinat arasindaki yaklasik mesafeyi (km) hesapla."""

    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def _cluster_to_zones(
    points: List[dict],
    eps_km: float = 1.0,
    min_samples: int = 2,
    min_cluster_size: int = 2,
) -> List[dict]:
    """Basit DBSCAN-benzeri clustering ile risk zonlari üret.

    Bu fonksiyon test_fire_risk_zones icin gereklidir ve sadece
    gelen noktalara göre bbox, ortalama risk ve sayi döndürür.
    """

    if not points:
        return []

    # DBSCAN benzeri etiketleme
    labels: List[int] = [-1] * len(points)
    cluster_id = 0

    for i, p in enumerate(points):
        if labels[i] != -1:
            continue

        # Komşuları bul
        neighbors = []
        for j, q in enumerate(points):
            dist = _haversine_km(p["lat"], p["lon"], q["lat"], q["lon"])
            if dist <= eps_km:
                neighbors.append(j)

        if len(neighbors) < min_samples:
            # Gürültü
            continue

        # Yeni cluster
        labels[i] = cluster_id
        queue = neighbors[:]

        while queue:
            j = queue.pop()
            if labels[j] == -1:
                labels[j] = cluster_id
            if labels[j] != cluster_id:
                continue

            # j noktasinin komsularini da ekle
            j_neighbors = []
            for k, r in enumerate(points):
                dist = _haversine_km(points[j]["lat"], points[j]["lon"], r["lat"], r["lon"])
                if dist <= eps_km:
                    j_neighbors.append(k)

            if len(j_neighbors) >= min_samples:
                for k in j_neighbors:
                    if labels[k] == -1:
                        labels[k] = cluster_id
                        queue.append(k)

        cluster_id += 1

    zones: List[dict] = []
    for cid in range(cluster_id):
        idxs = [i for i, lbl in enumerate(labels) if lbl == cid]
        if len(idxs) < min_cluster_size:
            continue

        lats = [points[i]["lat"] for i in idxs]
        lons = [points[i]["lon"] for i in idxs]
        risks = [points[i].get("risk_score", 0.0) for i in idxs]

        zone = {
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
            "avg_risk": sum(risks) / len(risks) if risks else 0.0,
            "count": len(idxs),
        }
        zones.append(zone)

    return zones

@lru_cache(maxsize=1)
def load_risk_data():
    """CSV'den yangın risk verilerini yükle ve ortak şemaya normalize et."""
    df = None

    # Kullanıcı isteğine göre öncelik: izmir_fire_points_filtered2.csv
    if PIPELINE_RISK_DATA_PATH.exists():
        df = pd.read_csv(PIPELINE_RISK_DATA_PATH)
    elif ML_RISK_DATA_PATH.exists():
        df = pd.read_csv(ML_RISK_DATA_PATH)
    else:
        return None

    # Ortak kolon adlandırması
    if "predicted_risk_class" not in df.columns and "risk_class" in df.columns:
        df["predicted_risk_class"] = df["risk_class"]

    if "latitude" not in df.columns and "center_lat" in df.columns:
        df["latitude"] = df["center_lat"]
    if "longitude" not in df.columns and "center_lon" in df.columns:
        df["longitude"] = df["center_lon"]

    # Pipeline dosyasında olmayan skor alanları için varsayılanlar
    if "fire_probability" not in df.columns:
        df["fire_probability"] = 0.0
    if "high_fire_probability" not in df.columns:
        # HIGH sınıfı için basit ikili gösterim
        df["high_fire_probability"] = (df["predicted_risk_class"] == "HIGH_RISK").astype(float)
    if "combined_risk_score" not in df.columns:
        # Basit sınıf bazlı skorlandırma (sunum/demoda tutarlı görsel için)
        class_scores = {
            "SAFE_UNBURNABLE": 0.1,
            "LOW_RISK": 0.35,
            "MEDIUM_RISK": 0.65,
            "HIGH_RISK": 0.9,
            "LOW": 0.35,
            "MEDIUM": 0.65,
            "HIGH": 0.9,
        }
        df["combined_risk_score"] = (
            df["predicted_risk_class"].map(class_scores).fillna(0.2)
        )

    # Risk sınıfı değerlerini standartlaştır (LOW/HIGH -> *_RISK)
    replacements = {
        "LOW": "LOW_RISK",
        "HIGH": "HIGH_RISK",
        "MEDIUM": "MEDIUM_RISK",
    }
    df["predicted_risk_class"] = df["predicted_risk_class"].replace(replacements)

    return df

@router.get("/points")
async def get_fire_risk_points(
    risk_class: Optional[str] = None,
    limit: int = Query(10000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
):
    """
    Yangın risk noktalarını döndür
    
    Parameters:
    - risk_class: Risk sınıfı (SAFE_UNBURNABLE, LOW_RISK, MEDIUM_RISK, HIGH_RISK)
    - limit: Döndürülecek maksimum nokta sayısı (default: 50000)
    """
    df = load_risk_data()
    
    if df is None:
        return {"error": "Veri bulunamadı", "points": []}
    
    # Risk sınıfına göre filtrele
    if risk_class:
        df = df[df["predicted_risk_class"] == risk_class]
    
    total_before_pagination = len(df)

    # Veriyi sınırla (offset + limit)
    if offset:
        df = df.iloc[offset:]
    df = df.head(limit)
    
    # GeoJSON formatına çevir
    points = []
    for _, row in df.iterrows():
        points.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "risk_class": row["predicted_risk_class"],
                "fire_probability": round(row["fire_probability"], 4),
                "high_fire_probability": round(row["high_fire_probability"], 4),
                "combined_risk_score": round(row["combined_risk_score"], 4),
                "color": RISK_COLORS.get(row["predicted_risk_class"], "#95a5a6")
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": points,
        "total": len(points),
        "offset": offset,
        "limit": limit,
        "total_available": total_before_pagination,
    }

@router.get("/statistics")
async def get_risk_statistics():
    """
    Yangın risk istatistiklerini döndür
    """
    df = load_risk_data()
    
    if df is None:
        return {"error": "Veri bulunamadı"}
    
    stats = {
        "total_points": len(df),
        "risk_distribution": df["predicted_risk_class"].value_counts().to_dict(),
        "average_fire_probability": round(df["fire_probability"].mean(), 4),
        "average_combined_risk_score": round(df["combined_risk_score"].mean(), 4),
        "high_risk_count": len(df[df["predicted_risk_class"] == "HIGH_RISK"]),
        "medium_risk_count": len(df[df["predicted_risk_class"] == "MEDIUM_RISK"]),
        "low_risk_count": len(df[df["predicted_risk_class"] == "LOW_RISK"]),
        "safe_count": len(df[df["predicted_risk_class"] == "SAFE_UNBURNABLE"]),
    }
    
    return stats

@router.get("/heatmap-data")
async def get_heatmap_data(cell_size: float = 0.05):
    """
    Gridlendirilmiş heatmap verisi döndür - Poligon olarak
    
    - cell_size: Grid hücresi boyutu (derece cinsinden, default: 0.05)
    """
    df = load_risk_data()
    
    if df is None:
        return {"error": "Veri bulunamadı"}
    
    # Grid oluştur - latitude ve longitude'u cell_size'a göre grupla
    df_copy = df.copy()
    df_copy['lat_grid'] = (df_copy['latitude'] / cell_size).astype(int) * cell_size
    df_copy['lon_grid'] = (df_copy['longitude'] / cell_size).astype(int) * cell_size
    
    # Grid hücrelerine göre ortalamaları hesapla
    grid_data = df_copy.groupby(['lat_grid', 'lon_grid']).agg({
        'combined_risk_score': 'mean',
        'fire_probability': 'mean',
        'predicted_risk_class': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'SAFE_UNBURNABLE'
    }).reset_index()
    
    # GeoJSON FeatureCollection formatında döndür - poligonlar olarak
    features = []
    for _, row in grid_data.iterrows():
        lat = row['lat_grid']
        lon = row['lon_grid']
        risk_score = row['combined_risk_score']
        
        # Kare poligon oluştur
        half_size = cell_size / 2
        coordinates = [[
            [lon - half_size, lat - half_size],
            [lon + half_size, lat - half_size],
            [lon + half_size, lat + half_size],
            [lon - half_size, lat + half_size],
            [lon - half_size, lat - half_size]
        ]]
        
        # Risk skoruna göre renk (sarı -> turuncı -> kırmızı)
        if risk_score >= 0.8:
            color = "#8b0000"  # Koyu kırmızı
        elif risk_score >= 0.6:
            color = "#d70000"  # Kırmızı
        elif risk_score >= 0.4:
            color = "#ff4500"  # Turuncu-kırmızı
        elif risk_score >= 0.2:
            color = "#ffa500"  # Turuncu
        else:
            color = "#ffff00"  # Sarı
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": coordinates
            },
            "properties": {
                "combined_risk_score": round(risk_score, 4),
                "fire_probability": round(row['fire_probability'], 4),
                "risk_class": row['predicted_risk_class'],
                "color": color
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": features,
        "total_cells": len(features),
        "cell_size": cell_size
    }

"""
Yangın risk verileri için API router
"""
from fastapi import APIRouter
from typing import List, Optional
import pandas as pd
from pathlib import Path

router = APIRouter(prefix="/api/fire-risk", tags=["fire-risk"])

# CSV dosyasını yükle
RISK_DATA_PATH = Path(__file__).parent.parent.parent.parent / "database" / "task1" / "izmir_future_fire_risk_dataset.csv"

# Risk sınıflarına göre renkler
RISK_COLORS = {
    "SAFE_UNBURNABLE": "#2ecc71",      # Yeşil - Güvenli
    "LOW_RISK": "#f39c12",              # Turuncu - Düşük Risk
    "MEDIUM_RISK": "#e74c3c",           # Kırmızı - Orta Risk
    "HIGH_RISK": "#8b0000",             # Koyu Kırmızı - Yüksek Risk
}

def load_risk_data():
    """CSV'den yangın risk verilerini yükle"""
    if RISK_DATA_PATH.exists():
        return pd.read_csv(RISK_DATA_PATH)
    return None

@router.get("/points")
async def get_fire_risk_points(
    risk_class: Optional[str] = None,
    limit: int = 50000
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
    
    # Veriyi sınırla
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
        "total": len(points)
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

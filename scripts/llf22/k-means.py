"""
Pipeline: Rastgele Noktalar → İtfaiye Bazlı K-Means Kümeleme
==============================================================
1. Kullanıcı kaç nokta istediğini girer (n)
2. Kullanıcı kaç küme istediğini girer (k)
3. Rastgele n nokta seçilir
4. K-Means bu noktaları k kümeye ayırır
5. Her küme için en yakın itfaiye bulunur
6. Demand değeri risk sınıfına göre atanır (HIGH: 60-100, LOW: 10-50)
7. Sonuçlar CSV olarak kaydedilir
"""

import csv
import json
import os
import random
import sys
import numpy as np
from sklearn.cluster import KMeans
from math import radians, sin, cos, sqrt, atan2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from random_fire_points import randomList, get_available_counts


# =====================================================================
# Sabitler
# =====================================================================

STATIONS_CSV = os.path.join(SCRIPT_DIR, "output", "izmir_itfaiye_master_dataset.csv")


# =====================================================================
# Haversine mesafe (km)
# =====================================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# =====================================================================
# Demand hesapla (risk bazlı)
# =====================================================================

def assign_demand(risk_class):
    """HIGH noktalarına 60-100, LOW noktalarına 10-50 arası demand atar."""
    if risk_class == "HIGH":
        return random.randint(60, 100)
    else:
        return random.randint(10, 50)


# =====================================================================
# İtfaiye istasyonlarını yükle
# =====================================================================

def load_fire_stations():
    stations = []
    with open(STATIONS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations.append({
                "id": reader.line_num - 1,
                "name": row["station_name"],
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "district": row["verified_district"],
            })
    return stations


# =====================================================================
# Pipeline
# =====================================================================

def run_pipeline(n, k):
    stations = load_fire_stations()

    # --- ADIM 1: Rastgele n nokta seç ---
    points = randomList(n)

    # --- ADIM 2: K-Means kümeleme ---
    coords = np.array([[p["center_lat"], p["center_lon"]] for p in points])
    actual_k = min(k, n)
    kmeans = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    kmeans.fit(coords)

    for i, p in enumerate(points):
        p["cluster_id"] = int(kmeans.labels_[i])

    # --- ADIM 3: Her küme için itfaiye eşleştir ---
    clusters = []
    for cid in range(actual_k):
        cluster_points = [p for p in points if p["cluster_id"] == cid]
        center_lat = float(kmeans.cluster_centers_[cid][0])
        center_lon = float(kmeans.cluster_centers_[cid][1])

        # En yakın itfaiyeyi bul
        min_dist = float("inf")
        nearest_station = None
        for station in stations:
            dist = haversine(center_lat, center_lon, station["lat"], station["lon"])
            if dist < min_dist:
                min_dist = dist
                nearest_station = station

        # Her noktaya itfaiye mesafesi ve demand ata
        for p in cluster_points:
            p["station_distance_km"] = round(
                haversine(p["center_lat"], p["center_lon"],
                          nearest_station["lat"], nearest_station["lon"]), 2
            )
            p["demand"] = assign_demand(p["risk_class"])
            p["fire_station_id"] = nearest_station["id"]
            p["fire_station_name"] = nearest_station["name"]

        high_count = sum(1 for p in cluster_points if p["risk_class"] == "HIGH")
        low_count = len(cluster_points) - high_count
        high_pct = round((high_count / len(cluster_points) * 100), 1) if cluster_points else 0

        clusters.append({
            "cluster_id": cid,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "station_id": nearest_station["id"],
            "station_name": nearest_station["name"],
            "station_district": nearest_station["district"],
            "station_lat": nearest_station["lat"],
            "station_lon": nearest_station["lon"],
            "station_distance_km": round(min_dist, 2),
            "total_count": len(cluster_points),
            "high_count": high_count,
            "low_count": low_count,
            "high_pct": high_pct,
            "risk_level": "KRITIK" if high_pct > 60 else ("YUKSEK" if high_pct > 40 else "NORMAL"),
            "points": cluster_points,
        })

    # --- Özet ---
    high_total = sum(1 for p in points if p["risk_class"] == "HIGH")
    critical_count = sum(1 for c in clusters if c["risk_level"] == "KRITIK")
    avg_dist = sum(c["station_distance_km"] for c in clusters) / len(clusters) if clusters else 0

    return {
        "points": points,
        "clusters": clusters,
        "summary": {
            "total_points": n,
            "total_clusters": actual_k,
            "high_count": high_total,
            "low_count": n - high_total,
            "critical_clusters": critical_count,
            "avg_station_distance_km": round(avg_dist, 2),
        },
    }


# =====================================================================
# CSV çıktısı (fotoğraftaki format)
# =====================================================================

def pipeline_to_csv(result, output_path):
    """
    Çıktı formatı:
    ID; Lat; Lon; Demand; FireStation; Risk
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID", " Lat", " Lon", " Demand", " FireStation", " Risk"])
        for p in result["points"]:
            writer.writerow([
                p["id"],
                f" {p['center_lat']:.2f}",
                f" {p['center_lon']:.2f}",
                f" {p['demand']}",
                f" {p['fire_station_id']}",
                f" {p['risk_class']}",
            ])
    print(f"  CSV kaydedildi: {output_path}")


# =====================================================================
# GeoJSON çıktısı
# =====================================================================

def pipeline_to_geojson(result):
    features = []

    for p in result["points"]:
        features.append({
            "type": "Feature",
            "properties": {
                "type": "fire_point",
                "id": p["id"],
                "risk_class": p["risk_class"],
                "cluster_id": p["cluster_id"],
                "demand": p["demand"],
                "fire_station_id": p["fire_station_id"],
                "fire_station_name": p.get("fire_station_name", ""),
                "station_distance_km": p.get("station_distance_km"),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [p["center_lon"], p["center_lat"]],
            },
        })

    for c in result["clusters"]:
        features.append({
            "type": "Feature",
            "properties": {
                "type": "fire_station",
                "cluster_id": c["cluster_id"],
                "station_id": c["station_id"],
                "name": c["station_name"],
                "district": c["station_district"],
                "total_points": c["total_count"],
                "high_count": c["high_count"],
                "low_count": c["low_count"],
                "high_pct": c["high_pct"],
                "risk_level": c["risk_level"],
                "distance_km": c["station_distance_km"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [c["station_lon"], c["station_lat"]],
            },
        })

    for c in result["clusters"]:
        features.append({
            "type": "Feature",
            "properties": {
                "type": "cluster_center",
                "cluster_id": c["cluster_id"],
                "total_points": c["total_count"],
                "high_count": c["high_count"],
                "low_count": c["low_count"],
                "risk_level": c["risk_level"],
                "station_id": c["station_id"],
                "station_name": c["station_name"],
                "station_district": c["station_district"],
                "station_distance_km": c["station_distance_km"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [c["center_lon"], c["center_lat"]],
            },
        })

    return {"type": "FeatureCollection", "features": features}


# =====================================================================
# Terminal
# =====================================================================

if __name__ == "__main__":

    counts = get_available_counts()
    print(f"Dataset: {counts['total']} nokta ({counts['high']} HIGH, {counts['low']} LOW)")
    print()

    n = int(input("Kac nokta istiyorsunuz? "))
    k = int(input("Kac kume istiyorsunuz? "))

    print()
    print("=" * 75)
    print(f"  {n} nokta, {k} kume")
    print("=" * 75)

    result = run_pipeline(n, k)

    # Özet
    s = result["summary"]
    print(f"\n  Toplam: {s['total_points']} nokta ({s['high_count']} HIGH, {s['low_count']} LOW)")
    print(f"  Kume sayisi: {s['total_clusters']}")
    print(f"  Kritik kume: {s['critical_clusters']}")
    print(f"  Ort. itfaiye mesafesi: {s['avg_station_distance_km']} km")

    # Her kümenin detayı
    for c in result["clusters"]:
        print()
        print(f"  ┌─ Kume {c['cluster_id']} ─ {c['station_name']} ({c['station_district']})")
        print(f"  │  Merkez: ({c['center_lat']:.4f}, {c['center_lon']:.4f})")
        print(f"  │  Itfaiye mesafesi: {c['station_distance_km']} km")
        print(f"  │  Nokta: {c['total_count']} ({c['high_count']} HIGH, {c['low_count']} LOW) → {c['risk_level']}")
        print(f"  │")
        print(f"  │  {'ID':>4s} | {'Lat':>9s} | {'Lon':>9s} | {'Demand':>6s} | {'Station':>7s} | {'Risk':>5s} | {'Mesafe':>7s}")
        print(f"  │  {'-'*4} | {'-'*9} | {'-'*9} | {'-'*6} | {'-'*7} | {'-'*5} | {'-'*7}")
        for p in c["points"]:
            print(f"  │  {p['id']:>4d} | {p['center_lat']:>9.4f} | {p['center_lon']:>9.4f} | "
                  f"{p['demand']:>6d} | {p['fire_station_id']:>7d} | "
                  f"{p['risk_class']:>5s} | {p['station_distance_km']:>5.1f}km")
        print(f"  └{'─' * 68}")

    # CSV kaydet
    output_dir = os.path.join(SCRIPT_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "pipeline_result.csv")
    pipeline_to_csv(result, csv_path)

    # GeoJSON kaydet
    geojson = pipeline_to_geojson(result)
    geojson_dir = os.path.join(ROOT_DIR, "static", "data")
    os.makedirs(geojson_dir, exist_ok=True)
    geojson_path = os.path.join(geojson_dir, "pipeline_result.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"  GeoJSON kaydedildi: {geojson_path}")
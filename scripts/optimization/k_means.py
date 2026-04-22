"""
Pipeline: Rastgele Noktalar → Mesafe Bazlı K-Medoids Kümeleme
==============================================================
1. Kullanıcı kaç nokta istediğini girer (n)
2. Kullanıcı kaç küme istediğini girer (k)
3. Rastgele n nokta seçilir (dist_all.csv'den)
4. K-Medoids bu noktaları k kümeye ayırır (precomputed mesafe ile)
5. Her küme için en yakın itfaiye bulunur (matris'ten)
6. Demand değeri risk sınıfına göre atanır (HIGH: 60-100, LOW: 10-50)
7. Sonuçlar CSV olarak kaydedilir

Dataset formatı: dist_all.csv (603x603, delimiter=';')
  - ID 0-553   → fire point
  - ID 554-602 → station
"""

import csv
import json
import os
import random
import numpy as np

from random_func import (
    randomList,
    get_available_counts,
    get_fire_fire_distances,
    get_fire_station_distances,
    get_station_ids,
    get_distance,
)


# =====================================================================
# Sabitler
# =====================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# =====================================================================
# K-Medoids (PAM algoritması — precomputed mesafe ile)
# =====================================================================

def kmedoids(distance_matrix: np.ndarray, k: int, max_iter: int = 300,
             random_state: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """
    K-Medoids (PAM) kümeleme — precomputed mesafe matrisi üzerinde.

    Parameters
    ----------
    distance_matrix : np.ndarray   NxN mesafe matrisi
    k : int                        küme sayısı
    max_iter : int                 max iterasyon
    random_state : int             seed

    Returns
    -------
    labels : np.ndarray            her noktanın küme etiketi (0..k-1)
    medoid_indices : np.ndarray    medoid olan noktaların indeksleri
    """
    rng = np.random.RandomState(random_state)
    n = distance_matrix.shape[0]
    k = min(k, n)

    # Başlangıç medoid'lerini rastgele seç
    medoid_indices = rng.choice(n, size=k, replace=False)

    for _ in range(max_iter):
        # Her noktayı en yakın medoid'e ata
        dists_to_medoids = distance_matrix[:, medoid_indices]  # (n, k)
        labels = np.argmin(dists_to_medoids, axis=1)

        # Her küme için yeni medoid bul (küme içi toplam mesafesi en düşük)
        new_medoids = np.copy(medoid_indices)
        for cid in range(k):
            cluster_mask = labels == cid
            cluster_indices = np.where(cluster_mask)[0]
            if len(cluster_indices) == 0:
                continue
            sub_dist = distance_matrix[np.ix_(cluster_indices, cluster_indices)]
            total_dists = sub_dist.sum(axis=1)
            best = cluster_indices[np.argmin(total_dists)]
            new_medoids[cid] = best

        if np.array_equal(new_medoids, medoid_indices):
            break
        medoid_indices = new_medoids

    # Son etiketler
    dists_to_medoids = distance_matrix[:, medoid_indices]
    labels = np.argmin(dists_to_medoids, axis=1)

    return labels, medoid_indices


# =====================================================================
# Demand hesapla (risk bazlı)
# =====================================================================

def assign_demand(risk_class: str) -> int:
    """HIGH noktalarına 60-100, LOW noktalarına 10-50 arası demand atar."""
    if risk_class == "HIGH":
        return random.randint(60, 100)
    else:
        return random.randint(10, 50)


# =====================================================================
# Pipeline
# =====================================================================

def run_pipeline(n: int, k: int) -> dict:
    station_ids = get_station_ids()

    # --- ADIM 1: Rastgele n nokta seç ---
    points = randomList(n)
    fire_ids = [p["id"] for p in points]

    # --- ADIM 2: K-Medoids kümeleme (precomputed mesafe) ---
    dist_matrix = get_fire_fire_distances(fire_ids)
    actual_k = min(k, n)
    labels, medoid_indices = kmedoids(dist_matrix, actual_k, random_state=42)

    for i, p in enumerate(points):
        p["cluster_id"] = int(labels[i])

    # --- ADIM 3: Her küme için en yakın itfaiye eşleştir ---
    clusters = []
    for cid in range(actual_k):
        cluster_points = [p for p in points if p["cluster_id"] == cid]
        if not cluster_points:
            continue

        # Medoid noktanın ID'si
        medoid_id = fire_ids[medoid_indices[cid]]

        # Medoid'den en yakın istasyonu bul
        medoid_station_dists = {
            sid: get_distance(medoid_id, sid) for sid in station_ids
        }
        nearest_station_id = min(medoid_station_dists, key=medoid_station_dists.get)
        nearest_station_dist = medoid_station_dists[nearest_station_id]

        # Her noktaya demand + istasyon mesafesi ata
        for p in cluster_points:
            p["station_distance_km"] = round(
                get_distance(p["id"], nearest_station_id), 4
            )
            p["demand"] = assign_demand(p["risk_class"])
            p["fire_station_id"] = nearest_station_id

        high_count = sum(1 for p in cluster_points if p["risk_class"] == "HIGH")
        low_count = len(cluster_points) - high_count
        high_pct = round((high_count / len(cluster_points) * 100), 1)

        clusters.append({
            "cluster_id": cid,
            "medoid_id": medoid_id,
            "station_id": nearest_station_id,
            "station_distance_km": round(nearest_station_dist, 4),
            "total_count": len(cluster_points),
            "high_count": high_count,
            "low_count": low_count,
            "high_pct": high_pct,
            "risk_level": (
                "KRITIK" if high_pct > 60
                else ("YUKSEK" if high_pct > 40 else "NORMAL")
            ),
            "points": cluster_points,
        })

    # --- Özet ---
    high_total = sum(1 for p in points if p["risk_class"] == "HIGH")
    critical_count = sum(1 for c in clusters if c["risk_level"] == "KRITIK")
    avg_dist = (
        sum(c["station_distance_km"] for c in clusters) / len(clusters)
        if clusters else 0
    )

    return {
        "points": points,
        "clusters": clusters,
        "summary": {
            "total_points": n,
            "total_clusters": actual_k,
            "high_count": high_total,
            "low_count": n - high_total,
            "critical_clusters": critical_count,
            "avg_station_distance_km": round(avg_dist, 4),
        },
    }


# =====================================================================
# CSV çıktısı
# =====================================================================

def pipeline_to_csv(result: dict, output_path: str):
    """
    Çıktı formatı:
    ID; Demand; FireStation; Risk; StationDist_km
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ID", " Demand", " FireStation", " Risk", " StationDist_km"])
        for p in result["points"]:
            writer.writerow([
                p["id"],
                f" {p['demand']}",
                f" {p['fire_station_id']}",
                f" {p['risk_class']}",
                f" {p['station_distance_km']}",
            ])
    print(f"  CSV kaydedildi: {output_path}")


# =====================================================================
# GeoJSON çıktısı
# =====================================================================

def pipeline_to_geojson(result: dict) -> dict:
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
                "station_distance_km": p["station_distance_km"],
            },
        })

    for c in result["clusters"]:
        features.append({
            "type": "Feature",
            "properties": {
                "type": "cluster_info",
                "cluster_id": c["cluster_id"],
                "medoid_id": c["medoid_id"],
                "station_id": c["station_id"],
                "total_points": c["total_count"],
                "high_count": c["high_count"],
                "low_count": c["low_count"],
                "high_pct": c["high_pct"],
                "risk_level": c["risk_level"],
                "station_distance_km": c["station_distance_km"],
            },
        })

    return {"type": "FeatureCollection", "features": features}


# =====================================================================
# Terminal
# =====================================================================

if __name__ == "__main__":

    counts = get_available_counts()
    print(f"Dataset: {counts['total']} nokta ({counts['high']} HIGH, {counts['low']} LOW)")
    print(f"Station: {len(get_station_ids())} itfaiye istasyonu (ID {get_station_ids()[0]}-{get_station_ids()[-1]})")
    print()

    n = int(input("Kac nokta istiyorsunuz? "))
    k = int(input("Kac kume istiyorsunuz? "))

    print()
    print("=" * 75)
    print(f"  {n} nokta, {k} kume (K-Medoids, precomputed mesafe matrisi)")
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
        print(f"  +- Kume {c['cluster_id']} - Station {c['station_id']} (medoid: {c['medoid_id']})")
        print(f"  |  Itfaiye mesafesi: {c['station_distance_km']} km")
        print(f"  |  Nokta: {c['total_count']} ({c['high_count']} HIGH, {c['low_count']} LOW) -> {c['risk_level']}")
        print(f"  |")
        print(f"  |  {'ID':>4s} | {'Demand':>6s} | {'Station':>7s} | {'Risk':>5s} | {'Mesafe':>8s}")
        print(f"  |  {'-'*4} | {'-'*6} | {'-'*7} | {'-'*5} | {'-'*8}")
        for p in c["points"]:
            print(
                f"  |  {p['id']:>4d} | "
                f"{p['demand']:>6d} | {p['fire_station_id']:>7d} | "
                f"{p['risk_class']:>5s} | {p['station_distance_km']:>6.4f}km"
            )
        print(f"  +{'-' * 55}")

    # CSV kaydet
    csv_path = os.path.join(SCRIPT_DIR, "pipeline_result.csv")
    pipeline_to_csv(result, csv_path)

    # GeoJSON kaydet
    geojson = pipeline_to_geojson(result)
    geojson_path = os.path.join(SCRIPT_DIR, "pipeline_result.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"  GeoJSON kaydedildi: {geojson_path}")

    # SA ve GA algoritmalarini otomatik tetikle
    import sys
    import subprocess
    print()
    print("=" * 75)
    print("  SA ve GA optimizasyon algoritmalari baslatiliyor...")
    print("=" * 75)
    subprocess.run([sys.executable, "main.py"], cwd=SCRIPT_DIR, check=True)
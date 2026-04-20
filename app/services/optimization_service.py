"""
Optimization Service – Hocanın SA/GA Motorlarını API'ye Bağlar

Akış:
  1) k_means.py → pipeline_result.csv (K-Medoids kümeleme + demand + station)
  2) main.py   → SA/GA çalıştırır, *_All_Stations_Best_Solutions.json üretir
  3) Bu servis → JSON sonuçlarını okur + koordinat bilgisi ekler → frontend-ready

dist_all.csv (603×603): ID 0-553 fire point, ID 554-602 station
"""
from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Dosya Yolları ─────────────────────────────────────────────────────────────

_OPTIMIZATION_DIR = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "optimization"
)
_DIST_ALL_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts" / "llf22" / "output" / "dist_all.csv"
)
_FIRE_POINTS_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts" / "llf22" / "output" / "izmir_fire_points_filtered2.csv"
)
_FIRE_STATIONS_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts" / "llf22" / "output" / "izmir_itfaiye_master_dataset.csv"
)

SA_RESULT_JSON = _OPTIMIZATION_DIR / "SA_All_Stations_Best_Solutions.json"
GA_RESULT_JSON = _OPTIMIZATION_DIR / "GA_All_Stations_Best_Solutions.json"
PIPELINE_RESULT_CSV = _OPTIMIZATION_DIR / "pipeline_result.csv"


# ── Koordinat Yükleme ────────────────────────────────────────────────────────

_coordinates: Dict[int, Dict[str, float]] = {}


def _load_coordinates() -> None:
    """Yangın noktaları ve istasyon koordinatlarını yükler."""
    global _coordinates
    if _coordinates:
        return

    # Fire points
    if _FIRE_POINTS_CSV.exists():
        with open(_FIRE_POINTS_CSV, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=",")
            idx = 0
            for row in reader:
                if row[0].isalpha():
                    continue
                lat = float(row[4])
                lon = float(row[5])
                _coordinates[idx] = {"lat": lat, "lon": lon, "type": "fire_point"}
                idx += 1

    # Stations
    if _FIRE_STATIONS_CSV.exists():
        with open(_FIRE_STATIONS_CSV, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=",")
            station_idx = 554  # Station ID'ler 554'ten başlıyor
            for row in reader:
                if row[0] == "station_name":
                    continue
                lat = float(row[1])
                lon = float(row[2])
                _coordinates[station_idx] = {
                    "lat": lat,
                    "lon": lon,
                    "type": "station",
                    "name": row[0] if row[0] else f"Station {station_idx}",
                }
                station_idx += 1


def _get_coord(node_id: int) -> Dict[str, float]:
    """Bir node ID'nin koordinatını döndürür."""
    _load_coordinates()
    return _coordinates.get(node_id, {"lat": 0.0, "lon": 0.0, "type": "unknown"})


# ── Pipeline Çalıştırma ──────────────────────────────────────────────────────

def run_pipeline(n: int, k: int) -> Dict:
    """
    k_means.py'yi çalıştırarak pipeline_result.csv üretir.
    Ardından main.py'yi çalıştırarak SA/GA sonuçlarını üretir.
    """
    start = time.perf_counter()

    # ADIM 1: k_means.py → pipeline_result.csv
    kmeans_script = _OPTIMIZATION_DIR / "k_means.py"
    if not kmeans_script.exists():
        return {"success": False, "error": "k_means.py bulunamadı"}

    try:
        proc = subprocess.run(
            [sys.executable, str(kmeans_script)],
            input=f"{n}\n{k}\n",
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_OPTIMIZATION_DIR),
        )
        if proc.returncode != 0:
            logger.error("k_means.py stderr: %s", proc.stderr)
            return {
                "success": False,
                "error": f"Pipeline hatası: {proc.stderr[:500]}",
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Pipeline zaman aşımı (120s)"}

    elapsed = (time.perf_counter() - start) * 1000
    return {
        "success": True,
        "pipeline_output": proc.stdout[-2000:] if proc.stdout else "",
        "computation_time_ms": round(elapsed, 2),
    }


def run_sa_ga_optimization() -> Dict:
    """
    scripts/optimization/main.py'yi çalıştırarak SA ve GA sonuçlarını üretir.
    Önkoşul: pipeline_result.csv mevcut olmalı.
    """
    if not PIPELINE_RESULT_CSV.exists():
        return {"success": False, "error": "pipeline_result.csv bulunamadı. Önce pipeline çalıştırın."}

    start = time.perf_counter()
    main_script = _OPTIMIZATION_DIR / "main.py"

    try:
        proc = subprocess.run(
            [sys.executable, str(main_script)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_OPTIMIZATION_DIR),
        )
        if proc.returncode != 0:
            logger.error("main.py stderr: %s", proc.stderr)
            return {
                "success": False,
                "error": f"SA/GA hatası: {proc.stderr[:500]}",
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "SA/GA zaman aşımı (300s)"}

    elapsed = (time.perf_counter() - start) * 1000
    return {
        "success": True,
        "output": proc.stdout[-2000:] if proc.stdout else "",
        "computation_time_ms": round(elapsed, 2),
    }


# ── Sonuç Okuma ──────────────────────────────────────────────────────────────

def _load_json_results(path: Path) -> Optional[List[Dict]]:
    """SA/GA sonuç JSON'unu yükler."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_station_response(station_data: Dict) -> Dict:
    """
    Tek bir istasonun SA/GA sonucunu frontend-ready formata çevirir.

    Giriş formatı (hocanın JSON'u):
    {
      "station_id": 600,
      "assigned_fire_points": [106, 308, ...],
      "total_distance": 1.2025,
      "vehicles": [
        {"vehicle_index": 0, "tour": [600, 279, 308, ...], "load": 200, "distance": 0.85},
        ...
      ]
    }
    """
    station_id = station_data["station_id"]
    station_coord = _get_coord(station_id)

    vehicles_response: List[Dict] = []
    all_polylines: List[List[List[float]]] = []

    for v in station_data.get("vehicles", []):
        tour = v.get("tour", [])
        polyline: List[List[float]] = []
        tour_nodes: List[Dict] = []

        for node_id in tour:
            coord = _get_coord(node_id)
            node_info: Dict[str, Any] = {
                "node_id": node_id,
                "lat": coord.get("lat", 0.0),
                "lon": coord.get("lon", 0.0),
                "node_type": coord.get("type", "unknown"),
            }
            if coord.get("type") == "station":
                node_info["name"] = coord.get("name", "")
            tour_nodes.append(node_info)
            polyline.append([coord.get("lat", 0.0), coord.get("lon", 0.0)])

        vehicles_response.append({
            "vehicle_index": v.get("vehicle_index", 0),
            "tour": tour_nodes,
            "polyline": polyline,
            "load": v.get("load", 0),
            "distance": v.get("distance", 0.0),
        })
        all_polylines.append(polyline)

    return {
        "station_id": station_id,
        "station_lat": station_coord.get("lat", 0.0),
        "station_lon": station_coord.get("lon", 0.0),
        "station_name": station_coord.get("name", f"Station {station_id}"),
        "assigned_fire_points": station_data.get("assigned_fire_points", []),
        "total_distance": station_data.get("total_distance", 0.0),
        "vehicle_count": len(vehicles_response),
        "vehicles": vehicles_response,
    }


def get_optimization_results(algorithm: str) -> Dict:
    """
    SA veya GA sonuçlarını okuyup frontend'e normalize edilmiş response döndürür.

    Kurallar:
      - Rota yoksa → best_route: null, harita hiçbir şey çizmez
      - success: false → frontend hiçbir şey render etmez
    """
    _load_coordinates()

    if algorithm.upper() == "SA":
        json_path = SA_RESULT_JSON
    elif algorithm.upper() == "GA":
        json_path = GA_RESULT_JSON
    else:
        return {
            "success": False,
            "error": f"Geçersiz algoritma: {algorithm}. 'SA' veya 'GA' kullanın.",
            "best_route": None,
        }

    data = _load_json_results(json_path)
    if data is None:
        return {
            "success": False,
            "error": f"{algorithm.upper()} sonuçları bulunamadı. Önce optimizasyon çalıştırın.",
            "best_route": None,
            "algorithm": algorithm.upper(),
        }

    if not data:
        return {
            "success": False,
            "error": "Sonuç dosyası boş — rota üretilemedi.",
            "best_route": None,
            "algorithm": algorithm.upper(),
        }

    stations_response: List[Dict] = []
    total_distance = 0.0
    total_vehicles = 0

    for station_data in data:
        sr = _build_station_response(station_data)
        stations_response.append(sr)
        total_distance += station_data.get("total_distance", 0.0)
        total_vehicles += len(station_data.get("vehicles", []))

    return {
        "success": True,
        "algorithm": algorithm.upper(),
        "stations": stations_response,
        "summary": {
            "total_stations": len(stations_response),
            "total_vehicles": total_vehicles,
            "total_distance": round(total_distance, 4),
            "total_fire_points": sum(
                len(s.get("assigned_fire_points", [])) for s in data
            ),
        },
    }


def get_scenario_info() -> Dict:
    """Mevcut pipeline durumu ve senaryo bilgisi."""
    _load_coordinates()

    pipeline_exists = PIPELINE_RESULT_CSV.exists()
    sa_exists = SA_RESULT_JSON.exists()
    ga_exists = GA_RESULT_JSON.exists()

    # Pipeline sonuçlarını oku
    pipeline_points: List[Dict] = []
    if pipeline_exists:
        with open(PIPELINE_RESULT_CSV, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                if row[0].strip().isalpha():
                    continue
                try:
                    pid = int(row[0].strip())
                    coord = _get_coord(pid)
                    pipeline_points.append({
                        "id": pid,
                        "demand": int(row[1].strip()),
                        "fire_station_id": int(row[2].strip()),
                        "risk": row[3].strip(),
                        "station_distance_km": float(row[4].strip()),
                        "lat": coord.get("lat", 0.0),
                        "lon": coord.get("lon", 0.0),
                    })
                except (ValueError, IndexError):
                    continue

    # Station listesi
    stations: List[Dict] = []
    for nid, coord in _coordinates.items():
        if coord.get("type") == "station":
            stations.append({
                "id": nid,
                "name": coord.get("name", ""),
                "lat": coord["lat"],
                "lon": coord["lon"],
            })

    return {
        "pipeline_ready": pipeline_exists,
        "sa_results_ready": sa_exists,
        "ga_results_ready": ga_exists,
        "pipeline_points": pipeline_points,
        "pipeline_point_count": len(pipeline_points),
        "station_count": len(stations),
        "stations": stations,
        "available_algorithms": ["SA", "GA"],
    }

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "optimization"
_SCENARIO_JSON = _SCRIPTS_DIR / "scenario.json"


def _read_pipeline_csv() -> List[Dict[str, Any]]:
    csv_path = _SCRIPTS_DIR / "pipeline_result.csv"
    if not csv_path.exists():
        raise FileNotFoundError("pipeline_result.csv bulunamadı. Önce k_means.py çalıştırın.")

    points = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if row[0].strip().isalpha():
                continue
            points.append({
                "id": int(row[0].strip()),
                "demand": int(row[1].strip()),
                "fire_station_id": int(row[2].strip()),
                "risk_class": row[3].strip(),
                "station_distance_km": float(row[4].strip()),
            })
    return points


def _read_optimization_json(filename: str) -> Optional[List[Dict]]:
    path = _SCRIPTS_DIR / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_clusters_from_geojson() -> List[Dict]:
    path = _SCRIPTS_DIR / "pipeline_result.geojson"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        f["properties"]
        for f in data.get("features", [])
        if f.get("properties", {}).get("type") == "cluster_info"
    ]


def build_and_save(name: str) -> dict:
    points = _read_pipeline_csv()
    clusters = _read_clusters_from_geojson()

    ga_result = _read_optimization_json("GA_All_Stations_Best_Solutions.json")
    sa_result = _read_optimization_json("SA_All_Stations_Best_Solutions.json")

    high_count = sum(1 for p in points if p["risk_class"] == "HIGH")
    stations = list({p["fire_station_id"] for p in points})
    critical_clusters = sum(1 for c in clusters if c.get("risk_level") in ("HIGH", "CRITICAL"))

    scenario = {
        "scenario_id": 1,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_points": len(points),
            "high_count": high_count,
            "low_count": len(points) - high_count,
            "total_stations": len(stations),
            "total_clusters": len(clusters),
            "critical_clusters": critical_clusters,
        },
        "points": points,
        "clusters": clusters,
        "ga_result": ga_result,
        "sa_result": sa_result,
    }

    with open(_SCENARIO_JSON, "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)

    return scenario


def load_scenario(scenario_id: int) -> Optional[dict]:
    if not _SCENARIO_JSON.exists():
        return None
    with open(_SCENARIO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("scenario_id") != scenario_id:
        return None
    return data

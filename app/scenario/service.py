from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.api_core.exceptions import FailedPrecondition

from app.services.optimization_service import get_scenario_info
from app.services.firestore_store import FirestoreStore

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "optimization"
_SCENARIO_JSON = _SCRIPTS_DIR / "scenario.json"
_COLLECTION = "scenarios"
_COUNTER_COLLECTION = "_meta"
_COUNTER_DOC = "scenario_counter"


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


def _next_scenario_id(store: FirestoreStore) -> int:
    counter_ref = store.db.collection(_COUNTER_COLLECTION).document(_COUNTER_DOC)
    snapshot = counter_ref.get()
    if snapshot.exists:
        current = int((snapshot.to_dict() or {}).get("value", 0))
    else:
        current = 0
    new_value = current + 1
    counter_ref.set({"value": new_value}, merge=True)
    return new_value


def build_and_save(
    name: str,
    *,
    owner_username: str | None = None,
    owner_role: str | None = None,
) -> dict:
    store = FirestoreStore()
    scenario_id = _next_scenario_id(store)
    points = _read_pipeline_csv()
    clusters = _read_clusters_from_geojson()

    ga_result = _read_optimization_json("GA_All_Stations_Best_Solutions.json")
    sa_result = _read_optimization_json("SA_All_Stations_Best_Solutions.json")
    optimize_scenario = get_scenario_info()

    high_count = sum(1 for p in points if p["risk_class"] == "HIGH")
    stations = list({p["fire_station_id"] for p in points})
    critical_clusters = sum(1 for c in clusters if c.get("risk_level") in ("HIGH", "CRITICAL"))

    scenario = {
        "scenario_id": scenario_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner_username": owner_username,
        "owner_role": owner_role,
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
        "pipeline_snapshot": {
            "pipeline_points": optimize_scenario.get("pipeline_points") or [],
            "stations": optimize_scenario.get("stations") or [],
            "n": len(points),
            "k": len(clusters),
        },
    }

    with open(_SCENARIO_JSON, "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)

    store.db.collection(_COLLECTION).document(str(scenario_id)).set(scenario)

    return scenario


def load_scenario(scenario_id: int | str) -> Optional[dict]:
    scenario_id = int(scenario_id)
    store = FirestoreStore()
    doc = store.db.collection(_COLLECTION).document(str(scenario_id)).get()
    if doc.exists:
        return doc.to_dict()

    if not _SCENARIO_JSON.exists():
        return None
    with open(_SCENARIO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("scenario_id") != scenario_id:
        return None
    return data


def patch_scenario(
    scenario_id: int | str,
    patch: dict[str, Any],
) -> Optional[dict[str, Any]]:
    sid = int(scenario_id)
    store = FirestoreStore()
    ref = store.db.collection(_COLLECTION).document(str(sid))
    doc = ref.get()
    if not doc.exists:
        return None
    ref.set(patch, merge=True)
    updated = ref.get().to_dict() or {}
    return updated


def list_user_scenarios(username: str, limit: int = 50) -> list[dict[str, Any]]:
    store = FirestoreStore()
    rows: list[dict[str, Any]] = []
    try:
        docs = (
            store.db.collection(_COLLECTION)
            .where("owner_username", "==", username)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            rows.append(
                {
                    "scenario_id": data.get("scenario_id"),
                    "name": data.get("name"),
                    "created_at": data.get("created_at"),
                    "summary": data.get("summary") or {},
                }
            )
    except FailedPrecondition:
        docs = store.db.collection(_COLLECTION).stream()
        for doc in docs:
            data = doc.to_dict() or {}
            if data.get("owner_username") != username:
                continue
            rows.append(
                {
                    "scenario_id": data.get("scenario_id"),
                    "name": data.get("name"),
                    "created_at": data.get("created_at"),
                    "summary": data.get("summary") or {},
                }
            )
    rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    rows = rows[:limit]
    return rows

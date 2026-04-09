"""
Pipeline API: `scripts/llf22/k-means.py` içindeki run_pipeline + pipeline_to_geojson
ile aynı mantık ve GeoJSON şeması (tek kaynak).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict


def _load_kmeans_module(root: Path):
    script_path = root / "scripts" / "llf22" / "k-means.py"
    if not script_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("koru_kmeans_pipeline", script_path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pipeline_geojson(root: Path, n: int, k: int) -> Dict[str, Any]:
    mod = _load_kmeans_module(root)
    if mod is None:
        return {"type": "FeatureCollection", "features": [], "meta": {"error": "k-means.py bulunamadı"}}

    try:
        counts = mod.get_available_counts()
        max_n = int(counts["total"])
    except Exception:
        max_n = 554

    n = max(1, min(int(n), max_n))
    k = max(1, min(int(k), 100))

    try:
        result = mod.run_pipeline(n, k)
        geo = mod.pipeline_to_geojson(result)
    except Exception as e:
        return {
            "type": "FeatureCollection",
            "features": [],
            "meta": {"error": str(e)},
        }

    summary = result.get("summary") or {}
    clusters = result.get("clusters") or []
    points = result.get("points") or []
    geo["meta"] = {
        **summary,
        "risk_sample_features": len(points),
        "centroid_features": len(clusters),
        "station_marker_features": len(clusters),
    }
    return geo

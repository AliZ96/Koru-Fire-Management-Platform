"""
Dataset assembly for wildfire risk scoring.
Takes FIRMS GeoJSON (FeatureCollection) and generates a simple tabular set with
positive samples (fires) and synthetic negative samples within the İzmir bbox.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from .features import apply_basic_features

# Default bbox for İzmir (lon_min, lat_min, lon_max, lat_max)
IZMIR_BBOX = (26.230389, 37.818402, 28.495245, 39.392935)


def load_firms_geojson(path: Path) -> pd.DataFrame:
    """
    Load FIRMS GeoJSON (FeatureCollection) into a DataFrame.
    Expected geometry: Point with coordinates [lon, lat].
    """
    if not path.exists():
        raise FileNotFoundError(f"FIRMS file not found: {path}")
    gj = json.loads(path.read_text(encoding="utf-8"))
    feats = gj.get("features") or []
    rows = []
    for f in feats:
        geom = f.get("geometry") or {}
        props = f.get("properties") or {}
        coords = geom.get("coordinates") or [None, None]
        lon, lat = (coords + [None, None])[:2]
        if lat is None or lon is None:
            continue
        acq_date = props.get("acq_date") or props.get("date")
        raw_time = props.get("acq_time")
        acq_time = str(raw_time) if raw_time is not None else None
        ts = None
        if acq_date and acq_time:
            try:
                ts = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")
            except Exception:
                ts = None
        elif acq_date:
            try:
                ts = datetime.strptime(acq_date, "%Y-%m-%d")
            except Exception:
                ts = None

        row = {
            "lat": float(lat),
            "lon": float(lon),
            "confidence": _safe_float(props.get("confidence")),
            "brightness": _safe_float(props.get("bright_ti4") or props.get("brightness")),
            "acq_time": acq_time,
            "acq_date": acq_date,
            "timestamp": ts,
            "label": 1,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["timestamp"]
    df["month"] = ts.dt.month.fillna(0).astype(int)
    df["dayofyear"] = ts.dt.dayofyear.fillna(0).astype(int)
    df["hour"] = ts.dt.hour.fillna(0).astype(int)
    return df


def _generate_negatives(n: int, bbox: Tuple[float, float, float, float]) -> pd.DataFrame:
    """
    Generate simple negative samples uniformly in bbox.
    """
    lon_min, lat_min, lon_max, lat_max = bbox
    rng = random.Random(42)
    rows: List[dict] = []
    for _ in range(max(1, n)):
        lat = rng.uniform(lat_min, lat_max)
        lon = rng.uniform(lon_min, lon_max)
        rows.append(
            {
                "lat": lat,
                "lon": lon,
                "confidence": 0.0,
                "brightness": 0.0,
                "acq_time": None,
                "acq_date": None,
                "timestamp": None,
                "label": 0,
            }
        )
    return pd.DataFrame(rows)


def build_dataset(firms_path: Path, out_path: Path, neg_ratio: float = 2.0) -> Path:
    """
    Build dataset from FIRMS GeoJSON and synthetic negatives.
    """
    df_pos = load_firms_geojson(firms_path)
    if df_pos.empty:
        raise ValueError("No positive samples found in FIRMS data.")

    n_neg = int(len(df_pos) * neg_ratio)
    df_neg = _generate_negatives(n_neg, IZMIR_BBOX)

    df_all = pd.concat([df_pos, df_neg], ignore_index=True)
    df_all["timestamp"] = pd.to_datetime(df_all["timestamp"])
    # Ensure time-like strings for parquet compatibility
    df_all["acq_time"] = df_all["acq_time"].astype(str)
    df_all["acq_date"] = df_all["acq_date"].astype(str)
    df_all = _add_time_features(df_all)

    # Feature engineering (Phase 1)
    df_all = apply_basic_features(df_all)

    # Replace NaNs
    df_all = df_all.fillna(0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() in (".parquet", ".pq"):
        df_all.to_parquet(out_path, index=False)
    else:
        df_all.to_csv(out_path, index=False)
    return out_path


def parse_args():
    p = argparse.ArgumentParser(description="Build wildfire risk dataset from FIRMS GeoJSON.")
    p.add_argument(
        "--firms",
        type=Path,
        default=Path("data/firms.json"),
        help="Path to FIRMS GeoJSON (FeatureCollection).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/risk_dataset.parquet"),
        help="Output path (.parquet or .csv).",
    )
    p.add_argument(
        "--neg-ratio",
        type=float,
        default=2.0,
        help="Number of negatives per positive.",
    )
    return p.parse_args()


def main():
    args = parse_args()
    out = build_dataset(args.firms, args.out, args.neg_ratio)
    print(f"[OK] Dataset saved to {out}")


if __name__ == "__main__":
    main()



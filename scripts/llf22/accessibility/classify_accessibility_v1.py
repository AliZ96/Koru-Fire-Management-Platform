#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path

import pandas as pd


def score_to_class(score: int) -> str:
    # LOW = zorluk düşük (iyi), HIGH = zorluk yüksek (kötü)
    return {1: "LOW", 2: "MEDIUM", 3: "HIGH"}.get(int(score), "HIGH")


def road_score(dist_m):
    """dist_to_road_m -> (score, road_dist_class, reason)"""
    if pd.isna(dist_m):
        return 3, "UNKNOWN", "dist_to_road_m missing => road_score=3"
    d = float(dist_m)
    if d <= 250:
        return 1, "NEAR", "dist<=250m"
    if d <= 1000:
        return 2, "MID", "250m<dist<=1000m"
    return 3, "FAR", "dist>1000m"


def slope_score(slope_deg):
    """slope_deg -> (score, slope_class, reason)"""
    if pd.isna(slope_deg):
        # temkinli
        return 2, "UNKNOWN", "slope_deg missing => slope_score=2"
    s = float(slope_deg)
    if s <= 10:
        return 1, "LOW", "slope<=10°"
    if s <= 20:
        return 2, "MEDIUM", "10°<slope<=20°"
    return 3, "HIGH", "slope>20°"


def export_geojson(df: pd.DataFrame, out_path: Path) -> None:
    """center_lon, center_lat ile Point GeoJSON export eder."""
    required = {"center_lat", "center_lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"GeoJSON export için eksik kolon(lar): {missing}")

    features = []
    for _, row in df.iterrows():
        lon = float(row["center_lon"])
        lat = float(row["center_lat"])
        props = row.to_dict()
        for k, v in list(props.items()):
            if pd.isna(v):
                props[k] = None

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="SCRUM-57: ground/air accessibility v1 classification")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--geojson", default=None, help="Optional GeoJSON output path")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        raise FileNotFoundError(f"Input dosyası bulunamadı: {in_path}")

    df = pd.read_csv(in_path)

    # gerekli kolonlar
    needed = {"dist_to_road_m", "slope_deg"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Gerekli kolon(lar) yok: {missing}")

    # hesapla
    road_dist_class_col = []
    slope_class_col = []

    ground_scores = []
    ground_classes = []
    ground_reasons = []

    air_scores = []
    air_classes = []
    air_reasons = []

    for _, row in df.iterrows():
        r_score, r_class, r_reason = road_score(row.get("dist_to_road_m"))
        s_score, s_class, s_reason = slope_score(row.get("slope_deg"))

        # Ground: max(road, slope)
        g_score = max(r_score, s_score)
        g_class = score_to_class(g_score)
        g_reason = f"ground: {r_reason}, {s_reason} => score=max(road,slope)={g_score}"

        # Air(v1): slope-based (landing/base yok varsayımı)
        a_score = s_score
        a_class = score_to_class(a_score)
        a_reason = f"air(v1): {s_reason} => score={a_score} (slope-based; no landing/base data)"

        road_dist_class_col.append(r_class)
        slope_class_col.append(s_class)

        ground_scores.append(g_score)
        ground_classes.append(g_class)
        ground_reasons.append(g_reason)

        air_scores.append(a_score)
        air_classes.append(a_class)
        air_reasons.append(a_reason)

    # standard output kolonları (v1 suffix ile çakışmayı engeller)
    df["road_dist_class"] = road_dist_class_col
    df["slope_class"] = slope_class_col

    df["ground_access_score_v1"] = ground_scores
    df["ground_access_class_v1"] = ground_classes
    df["ground_reason_v1"] = ground_reasons

    df["air_access_score_v1"] = air_scores
    df["air_access_class_v1"] = air_classes
    df["air_reason_v1"] = air_reasons

    # coverage report
    total = len(df)
    g_empty = int(df["ground_access_class_v1"].isna().sum())
    a_empty = int(df["air_access_class_v1"].isna().sum())

    print("=== COVERAGE REPORT ===")
    print(f"rows_total: {total}")
    print(f"ground_class_empty: {g_empty}")
    print(f"air_class_empty: {a_empty}")
    print(f"ground_score_unique: {sorted(df['ground_access_score_v1'].unique().tolist())}")
    print(f"air_score_unique: {sorted(df['air_access_score_v1'].unique().tolist())}")

    # save csv
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"CSV written: {out_path}")

    # optional geojson
    if args.geojson:
        export_geojson(df, Path(args.geojson))
        print(f"GeoJSON written: {args.geojson}")


if __name__ == "__main__":
    main()
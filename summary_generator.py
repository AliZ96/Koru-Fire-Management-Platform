import json
from pathlib import Path

import pandas as pd


def generate_summary(
    csv_path: str = "pipeline_result.csv",
    output_path: str = "pipeline_summary.json",
) -> dict:
    # Auto-detect delimiter (comma/semicolon) and normalize header spacing.
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = [str(col).strip() for col in df.columns]
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    required_columns = ["ID", "Demand", "FireStation", "Risk", "StationDist_km"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in CSV: {missing_columns}")

    # Use FireStation as cluster proxy when explicit cluster column is absent.
    group_col = "FireStation"

    points_per_cluster = df.groupby(group_col).size().to_dict()
    risk_distribution = df["Risk"].value_counts().to_dict()
    assigned_station_per_cluster = df.groupby(group_col)["FireStation"].first().to_dict()
    total_demand_per_cluster = df.groupby(group_col)["Demand"].sum().to_dict()

    distance_stats_per_cluster = (
        df.groupby(group_col)["StationDist_km"]
        .agg(["mean", "median", "max"])
        .round(6)
        .rename(columns={"mean": "avg"})
        .to_dict(orient="index")
    )

    overall_distance_stats = {
        "avg": round(float(df["StationDist_km"].mean()), 6),
        "median": round(float(df["StationDist_km"].median()), 6),
        "max": round(float(df["StationDist_km"].max()), 6),
    }

    summary = {
        "source_file": str(csv_path),
        "total_points": int(len(df)),
        "points_per_cluster": points_per_cluster,
        "risk_distribution": risk_distribution,
        "assigned_station_per_cluster": assigned_station_per_cluster,
        "distance_stats_overall_km": overall_distance_stats,
        "distance_stats_per_cluster_km": distance_stats_per_cluster,
        "total_demand_per_cluster": total_demand_per_cluster,
    }

    Path(output_path).write_text(json.dumps(summary, indent=4), encoding="utf-8")
    return summary

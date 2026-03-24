"""
SCRUM-83 / Sprint-8 random fire point selection + demand generation
==================================================================

Bu script:
1. HIGH / LOW yangın risk noktalarından rastgele seçim yapar
2. Her seçilen nokta için combined_risk_score bulur
3. Score-based demand hesaplar
4. CSV ve GeoJSON çıktısı üretir

Acceptance Criteria karşılıkları:
- Every selected point has a computed demand in CSV and GeoJSON
- With the same seed, demand values are identical across runs
- Model parameters are documented and adjustable
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from app.services.demand_service import DemandConfig, DemandService


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

_POINTS_DATA_PATH = Path(
    os.environ.get(
        "KORU_GRID_CSV",
        _SCRIPT_DIR / "llf22" / "output" / "izmir_fire_points_filtered2.csv",
    )
)

_RISK_DATA_PATH = Path(
    os.environ.get(
        "KORU_RISK_DATASET_CSV",
        _PROJECT_ROOT / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv",
    )
)

_DEFAULT_OUTPUT_DIR = _SCRIPT_DIR / "llf22" / "output"

_df: Optional[pd.DataFrame] = None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_data() -> None:
    global _df
    if _df is not None:
        return

    points_df = pd.read_csv(_POINTS_DATA_PATH)
    risk_df = pd.read_csv(_RISK_DATA_PATH)

    risk_df = risk_df[
        ["latitude", "longitude", "combined_risk_score", "fire_probability", "predicted_risk_class"]
    ].copy()

    # Exact coordinate match
    merged = points_df.merge(
        risk_df,
        left_on=["center_lat", "center_lon"],
        right_on=["latitude", "longitude"],
        how="left",
    )

    merged = merged.drop(columns=["latitude", "longitude"], errors="ignore")

    # Fallback if some rows do not match
    def _fallback_score(row) -> float:
        rc = str(row.get("risk_class", "")).upper()
        if rc == "HIGH":
            return 0.85
        if rc == "LOW":
            return 0.35
        return 0.10

    merged["combined_risk_score"] = merged["combined_risk_score"].fillna(
        merged.apply(_fallback_score, axis=1)
    )

    _df = merged


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_available_counts() -> Dict[str, int]:
    _load_data()
    assert _df is not None

    high = len(_df[_df["risk_class"] == "HIGH"])
    low = len(_df[_df["risk_class"] == "LOW"])

    return {
        "high": high,
        "low": low,
        "total": len(_df),
    }


def randomList(
    n: int,
    seed: Optional[int] = None,
    demand_config: Optional[DemandConfig] = None,
) -> List[Dict]:
    """
    Rastgele n adet yangın noktası seçer ve her point'e demand ekler.

    Parameters
    ----------
    n : int
        Seçilecek nokta sayısı
    seed : Optional[int]
        Aynı seed ile aynı seçim + aynı demand elde edilir
    demand_config : Optional[DemandConfig]
        Demand model parametreleri

    Returns
    -------
    list[dict]
        Her point:
        {
          "id",
          "risk_class",
          "center_lat",
          "center_lon",
          "combined_risk_score",
          "fire_probability",
          "predicted_risk_class",
          "demand"
        }
    """
    _load_data()
    assert _df is not None

    if not isinstance(n, int):
        raise TypeError(f"n integer olmalıdır, {type(n).__name__} verildi.")
    if n < 0:
        raise ValueError("n negatif olamaz.")
    if n > len(_df):
        raise ValueError(f"n ({n}) toplam nokta sayısından ({len(_df)}) büyük olamaz.")

    selected = _df.sample(n=n, random_state=seed)

    points: List[Dict] = []
    for _, row in selected.iterrows():
        points.append(
            {
                "id": int(row["id"]),
                "risk_class": str(row["risk_class"]),
                "center_lat": float(row["center_lat"]),
                "center_lon": float(row["center_lon"]),
                "combined_risk_score": float(row["combined_risk_score"]),
                "fire_probability": (
                    None if pd.isna(row.get("fire_probability")) else float(row["fire_probability"])
                ),
                "predicted_risk_class": (
                    None
                    if pd.isna(row.get("predicted_risk_class"))
                    else str(row["predicted_risk_class"])
                ),
            }
        )

    demand_service = DemandService(config=demand_config)
    return demand_service.attach_demands(points, seed=seed)


def export_random_points(
    n: int,
    seed: Optional[int] = None,
    csv_path: Optional[str | Path] = None,
    geojson_path: Optional[str | Path] = None,
    demand_config: Optional[DemandConfig] = None,
) -> Dict:
    """
    Random point selection + demand üretimi + export
    """
    points = randomList(n=n, seed=seed, demand_config=demand_config)

    csv_path = Path(csv_path) if csv_path else _DEFAULT_OUTPUT_DIR / "selected_fire_points_with_demand.csv"
    geojson_path = Path(geojson_path) if geojson_path else _DEFAULT_OUTPUT_DIR / "selected_fire_points_with_demand.geojson"

    demand_service = DemandService(config=demand_config)
    demand_service.write_csv(points, csv_path)
    demand_service.write_geojson(points, geojson_path)

    return {
        "count": len(points),
        "seed": seed,
        "csv_path": str(csv_path),
        "geojson_path": str(geojson_path),
        "points": points,
        "demand_config": demand_service.get_config_dict(),
    }


# ---------------------------------------------------------------------------
# Example run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config = DemandConfig(
        min_demand=1,
        max_demand=10,
        noise_min=0,
        noise_max=2,
    )

    result = export_random_points(
        n=10,
        seed=42,
        demand_config=config,
    )

    print("Selection completed.")
    print(f"Seed: {result['seed']}")
    print(f"CSV: {result['csv_path']}")
    print(f"GeoJSON: {result['geojson_path']}")
    print()

    for p in result["points"][:5]:
        print(
            f"ID={p['id']} | Risk={p['risk_class']} | "
            f"Score={p['combined_risk_score']:.3f} | Demand={p['demand']}"
        )
"""
Feature engineering helpers for wildfire risk dataset.
Phase 1: lightweight, based only on existing tabular columns (no external data).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_log1p(series: pd.Series) -> pd.Series:
    return np.log1p(series.clip(lower=0.0))


def _cyclical(series: pd.Series, period: float) -> tuple[pd.Series, pd.Series]:
    radians = 2 * np.pi * series.fillna(0) / period
    return np.sin(radians), np.cos(radians)


def apply_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds simple engineered features:
    - brightness_log: log1p of brightness
    - confidence_scaled: confidence/100
    - month_sin/cos and hour_sin/cos for seasonality/cycle
    - lat/lon normalization (zero-mean)
    - is_daytime flag from hour
    """
    df = df.copy()

    df["brightness_log"] = _safe_log1p(df.get("brightness", 0))
    df["confidence_scaled"] = df.get("confidence", 0).fillna(0) / 100.0

    month = df.get("month", 0).fillna(0)
    hour = df.get("hour", 0).fillna(0)
    df["is_daytime"] = ((hour >= 6) & (hour <= 18)).astype(int)

    df["month_sin"], df["month_cos"] = _cyclical(month, 12.0)
    df["hour_sin"], df["hour_cos"] = _cyclical(hour, 24.0)

    # Normalize lat/lon to zero-mean, unit-std (fallback std=1)
    for col in ("lat", "lon"):
        s = df.get(col, 0).fillna(0)
        std = s.std() if s.std() != 0 else 1.0
        df[f"{col}_norm"] = (s - s.mean()) / std

    return df



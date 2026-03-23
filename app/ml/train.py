"""
Baseline model training for wildfire risk.
Loads a tabular dataset (parquet/csv) with a binary `label` column.
Saves a scikit-learn model plus metrics and metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
    auc,
)
from sklearn.model_selection import train_test_split

from .io import save_model


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if path.suffix.lower() in (".parquet", ".pq"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    if "label" not in df.columns:
        raise ValueError("Dataset must contain a 'label' column.")
    y = df["label"].astype(int)

    # Drop non-numeric/datetime columns we don't want to model directly
    drop_cols = ["label"]
    if "timestamp" in df.columns:
        drop_cols.append("timestamp")

    X = df.drop(columns=drop_cols).copy()
    feature_names: List[str] = []
    for col in X.columns:
        if X[col].dtype == object:
            X[col], _ = pd.factorize(X[col])
        feature_names.append(col)
    X = X.fillna(0)
    return X, y, feature_names


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    y_pred = (y_prob >= 0.5).astype(int)
    metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
    metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    except Exception:
        metrics["roc_auc"] = float("nan")
    try:
        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        metrics["pr_auc"] = float(auc(recall, precision))
    except Exception:
        metrics["pr_auc"] = float("nan")
    return metrics


def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[RandomForestClassifier, Dict[str, float]]:
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        n_jobs=-1,
        class_weight="balanced",
        random_state=random_state,
    )
    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_val)[:, 1]
    metrics = compute_metrics(y_val.values, y_prob)
    return model, metrics


def parse_args():
    p = argparse.ArgumentParser(description="Train baseline wildfire risk model.")
    p.add_argument(
        "--data",
        type=Path,
        default=Path("data/processed/risk_dataset.parquet"),
        help="Path to dataset (.parquet or .csv) with 'label' column.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data/models/baseline_v1.joblib"),
        help="Output model path.",
    )
    p.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Validation split ratio.",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    return p.parse_args()


def main():
    args = parse_args()
    df = load_dataset(args.data)
    X, y, feature_names = prepare_features(df)
    model, metrics = train_model(X, y, test_size=args.test_size, random_state=args.seed)

    meta = {
        "feature_names": feature_names,
        "label_name": "label",
        "train_rows": int(len(df)),
        "metrics": metrics,
        "model_type": "RandomForestClassifier",
        "version": "baseline_v1",
    }
    save_model(model, args.out, meta=meta)

    metrics_path = Path(f"{args.out}.metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"[OK] Model saved to {args.out}")
    print(f"[OK] Metrics: {json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    main()



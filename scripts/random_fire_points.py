"""
SCRUM-83 | S8-1 Random Fire Point Generator
============================================
Kullanıcının girdiği sayı kadar rastgele yangın risk noktası seçer.
Dataset: izmir_fire_points_filtered2.csv (554 nokta, sadece HIGH ve LOW)
ID aralığı: 0-553
"""

import random
import os
import pandas as pd


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.environ.get(
    "KORU_GRID_CSV",
    os.path.join(_SCRIPT_DIR, "llf22", "output", "izmir_fire_points_filtered2.csv")
)

_df = None


def _load_data():
    global _df
    if _df is not None:
        return
    _df = pd.read_csv(_DATA_PATH)


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def randomList(n):
    """
    554 yangın risk noktasından rastgele n adet seçer.

    Parameters
    ----------
    n : int
        Kullanıcının istediği nokta sayısı (max 554).

    Returns
    -------
    points : list[dict]
        Her nokta: {"id", "risk_class", "center_lat", "center_lon"}
    """
    _load_data()

    if not isinstance(n, int):
        raise TypeError(f"n integer olmalıdır, {type(n).__name__} verildi.")
    if n < 0:
        raise ValueError("n negatif olamaz.")
    if n > len(_df):
        raise ValueError(f"n ({n}) toplam nokta sayısından ({len(_df)}) büyük olamaz.")

    selected = _df.sample(n=n)

    points = []
    for _, row in selected.iterrows():
        points.append({
            "id": int(row["id"]),
            "risk_class": row["risk_class"],
            "center_lat": float(row["center_lat"]),
            "center_lon": float(row["center_lon"]),
        })

    return points


def get_available_counts():
    _load_data()
    high = len(_df[_df["risk_class"] == "HIGH"])
    low = len(_df[_df["risk_class"] == "LOW"])
    return {"high": high, "low": low, "total": len(_df)}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    counts = get_available_counts()
    print(f"Dataset: {_DATA_PATH}")
    print(f"Toplam: {counts['total']} ({counts['high']} HIGH, {counts['low']} LOW)")
    print()

    points = randomList(10)
    high = sum(1 for p in points if p["risk_class"] == "HIGH")
    print(f"Secilen: {len(points)} nokta ({high} HIGH, {len(points)-high} LOW)")
    print()
    print(f"  {'ID':>4s} | {'Lat':>9s} | {'Lon':>9s} | {'Risk':>5s}")
    print(f"  {'-'*4} | {'-'*9} | {'-'*9} | {'-'*5}")
    for p in points:
        print(f"  {p['id']:>4d} | {p['center_lat']:>9.4f} | {p['center_lon']:>9.4f} | {p['risk_class']:>5s}")
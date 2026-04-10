"""
SCRUM-83 | S8-1 Random Fire Point Generator (dist_all.csv Version)
===================================================================
Kullanıcının girdiği sayı kadar rastgele yangın risk noktası seçer.
Dataset: dist_all.csv (603x603 mesafe matrisi, delimiter=';')
  - Satır/Kolon 0-553   → fire point (554 adet)
  - Satır/Kolon 554-602 → station    (49 adet)
Risk class: ~%40 HIGH, ~%60 LOW (sabit seed ile tutarlı atama)
"""

import random
import os
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Veri yükleme
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.environ.get(
    "KORU_DISTANCE_CSV",
    os.path.join(_SCRIPT_DIR, "..", "llf22", "output", "dist_all.csv"),
)

_df = None           # Tam mesafe matrisi (603x603)
_fire_ids = None     # [0, 1, ..., 553]
_station_ids = None  # [554, 555, ..., 602]
_risk_map = None     # {fire_id: "HIGH"/"LOW"}

FIRE_COUNT = 554
STATION_START = 554
STATION_END = 602


def _load_data():
    global _df, _fire_ids, _station_ids, _risk_map
    if _df is not None:
        return

    _df = pd.read_csv(_DATA_PATH, sep=";", index_col=0)
    # Kolon isimlerini int'e çevir
    _df.columns = _df.columns.astype(int)

    _fire_ids = list(range(0, FIRE_COUNT))                      # 0-553
    _station_ids = list(range(STATION_START, STATION_END + 1))  # 554-602

    # Risk class ataması (%40 HIGH, %60 LOW — sabit seed)
    rng = random.Random(42)
    _risk_map = {}
    for fid in _fire_ids:
        _risk_map[fid] = "HIGH" if rng.random() < 0.40 else "LOW"


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def randomList(n: int) -> list[dict]:
    """
    554 yangın risk noktasından rastgele n adet seçer.

    Parameters
    ----------
    n : int   İstenen nokta sayısı (max 554)

    Returns
    -------
    list[dict]   Her nokta: {"id", "risk_class"}
    """
    _load_data()

    if not isinstance(n, int):
        raise TypeError(f"n integer olmalıdır, {type(n).__name__} verildi.")
    if n < 0:
        raise ValueError("n negatif olamaz.")
    if n > len(_fire_ids):
        raise ValueError(
            f"n ({n}) toplam nokta sayısından ({len(_fire_ids)}) büyük olamaz."
        )

    selected = random.sample(_fire_ids, n)

    return [{"id": fid, "risk_class": _risk_map[fid]} for fid in selected]


# ---------------------------------------------------------------------------
# Mesafe sorgulama yardımcıları
# ---------------------------------------------------------------------------

def get_distance(node_a: int, node_b: int) -> float:
    """İki node arasındaki mesafeyi matris'ten döndürür (km)."""
    _load_data()
    return float(_df.loc[node_a, node_b])


def get_fire_fire_distances(fire_ids: list[int]) -> np.ndarray:
    """Seçilen fire noktaları arasındaki NxN mesafe alt-matrisini döndürür."""
    _load_data()
    return _df.loc[fire_ids, fire_ids].values.astype(float)


def get_fire_station_distances(fire_ids: list[int]) -> pd.DataFrame:
    """Seçilen fire noktalarının tüm station'lara mesafesini döndürür (NxS)."""
    _load_data()
    return _df.loc[fire_ids, _station_ids]


def get_station_ids() -> list[int]:
    _load_data()
    return list(_station_ids)


def get_fire_ids() -> list[int]:
    _load_data()
    return list(_fire_ids)


def get_available_counts() -> dict:
    _load_data()
    high = sum(1 for v in _risk_map.values() if v == "HIGH")
    low = sum(1 for v in _risk_map.values() if v == "LOW")
    return {"high": high, "low": low, "total": len(_fire_ids)}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    counts = get_available_counts()
    print(f"Dataset: {_DATA_PATH}")
    print(f"Toplam: {counts['total']} fire ({counts['high']} HIGH, {counts['low']} LOW)")
    print(f"Station: {len(get_station_ids())} adet ({STATION_START}-{STATION_END})")
    print()

    points = randomList(10)
    high = sum(1 for p in points if p["risk_class"] == "HIGH")
    print(f"Secilen: {len(points)} nokta ({high} HIGH, {len(points)-high} LOW)")
    print()
    print(f"  {'ID':>4s} | {'Risk':>5s}")
    print(f"  {'-'*4} | {'-'*5}")
    for p in points:
        print(f"  {p['id']:>4d} | {p['risk_class']:>5s}")

    # Mesafe testi
    print()
    print(f"  0 → 554 (station): {get_distance(0, 554):.4f} km")
    print(f"  0 → 1   (fire):    {get_distance(0, 1):.4f} km")
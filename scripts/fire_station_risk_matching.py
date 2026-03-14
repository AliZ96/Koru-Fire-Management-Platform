#!/usr/bin/env python3
"""
S8-4 Fire Station <-> Risk Point Matching
=========================================
Her risk noktasını en yakın itfaiye ile eşleştirir (nearest neighbour).
Çıktı: scripts/llf22/output/risk_fire_station_matching.csv
"""

import os
import sys
from pathlib import Path

# Proje kökü
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.fire_station_risk_matching_service import build_matching


def main():
    matching = build_matching(ROOT)
    if not matching:
        print("Hata: Risk noktası veya itfaiye verisi bulunamadı.")
        sys.exit(1)

    out_dir = ROOT / "scripts" / "llf22" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "risk_fire_station_matching.csv"

    import csv
    fieldnames = [
        "risk_id", "risk_class", "center_lat", "center_lon",
        "station_id", "station_name", "station_lat", "station_lon", "distance_km",
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(matching)

    high = sum(1 for m in matching if m["risk_class"] == "HIGH")
    low = sum(1 for m in matching if m["risk_class"] == "LOW")
    print(f"S8-4 Fire Station <-> Risk Point Matching tamamlandı.")
    print(f"  Toplam eşleşme: {len(matching)} (HIGH: {high}, LOW: {low})")
    print(f"  Çıktı: {out_path}")


if __name__ == "__main__":
    main()

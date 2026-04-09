#!/usr/bin/env python3
"""notlar.md (KONUM,LAT,LONG) dosyasından fire-stations.geojson üretir."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = Path(r"C:\Users\Ali\Desktop\notlar.md")
OUT = ROOT / "static" / "data" / "fire-stations.geojson"

def main():
    text = NOTES.read_text(encoding="utf-8")
    features = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("KONUM"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        name = parts[0]
        try:
            lat = float(parts[-2])
            lon = float(parts[-1])
        except ValueError:
            continue
        if len(parts) > 3:
            name = ",".join(parts[:-2]).strip()
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": len(features) + 1,
                "name": name,
                "type": "fire_station",
            }
        })
    fc = {"type": "FeatureCollection", "features": features}
    OUT.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(features)} stations to {OUT}")

if __name__ == "__main__":
    main()

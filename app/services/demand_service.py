from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random
from typing import Any, Dict, List, Optional


@dataclass
class DemandConfig:
    """
    Demand modeli ayarları.

    min_demand / max_demand:
        Üretilecek demand aralığı.

    noise_min / noise_max:
        Risk skoruna eklenen kontrollü rastgele sapma.
        Aynı seed ile aynı sonuçlar üretilir.

    fallback_*_score:
        combined_risk_score eksikse risk_class üzerinden kullanılacak varsayılan skorlar.
    """
    min_demand: int = 1
    max_demand: int = 10
    noise_min: int = 0
    noise_max: int = 2

    fallback_high_score: float = 0.85
    fallback_medium_score: float = 0.60
    fallback_low_score: float = 0.35
    fallback_safe_score: float = 0.10

    def validate(self) -> None:
        if self.min_demand < 0:
            raise ValueError("min_demand negatif olamaz.")
        if self.max_demand < self.min_demand:
            raise ValueError("max_demand, min_demand'den küçük olamaz.")
        if self.noise_min > self.noise_max:
            raise ValueError("noise_min, noise_max'tan büyük olamaz.")


class DemandService:
    """
    Risk skoruna göre demand üreten servis.

    Kullanım:
        service = DemandService()
        enriched_points = service.attach_demands(points, seed=42)
    """

    def __init__(self, config: Optional[DemandConfig] = None) -> None:
        self.config = config or DemandConfig()
        self.config.validate()

    def _fallback_score_from_risk_class(self, risk_class: Optional[str]) -> float:
        if not risk_class:
            return self.config.fallback_safe_score

        rc = str(risk_class).upper().strip()

        if rc in {"HIGH", "HIGH_RISK"}:
            return self.config.fallback_high_score
        if rc in {"MEDIUM", "MEDIUM_RISK"}:
            return self.config.fallback_medium_score
        if rc in {"LOW", "LOW_RISK"}:
            return self.config.fallback_low_score
        return self.config.fallback_safe_score

    def _resolve_score(self, point: Dict[str, Any]) -> float:
        raw_score = point.get("combined_risk_score")

        if raw_score is None:
            return self._fallback_score_from_risk_class(point.get("risk_class"))

        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = self._fallback_score_from_risk_class(point.get("risk_class"))

        return max(0.0, min(1.0, score))

    def compute_demand(
        self,
        point: Dict[str, Any],
        rng: Optional[Random] = None,
    ) -> int:
        """
        Demand = score-based + kontrollü noise
        """
        rng = rng or Random()

        score = self._resolve_score(point)

        base = self.config.min_demand + (
            score * (self.config.max_demand - self.config.min_demand)
        )

        noise = rng.randint(self.config.noise_min, self.config.noise_max)
        demand = int(round(base + noise))

        demand = max(self.config.min_demand, min(self.config.max_demand, demand))
        return demand

    def attach_demands(
        self,
        points: List[Dict[str, Any]],
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rng = Random(seed)

        enriched: List[Dict[str, Any]] = []
        for point in points:
            item = dict(point)
            item["combined_risk_score"] = round(self._resolve_score(item), 6)
            item["demand"] = self.compute_demand(item, rng=rng)
            enriched.append(item)

        return enriched

    def to_geojson(self, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        features = []

        for point in points:
            lon = float(point["center_lon"])
            lat = float(point["center_lat"])

            props = dict(point)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                    "properties": props,
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def write_csv(self, points: List[Dict[str, Any]], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not points:
            raise ValueError("CSV yazmak için en az 1 point gerekli.")

        fieldnames = list(points[0].keys())

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(points)

        return path

    def write_geojson(self, points: List[Dict[str, Any]], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        geojson = self.to_geojson(points)

        with path.open("w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        return path

    def get_config_dict(self) -> Dict[str, Any]:
        return asdict(self.config)
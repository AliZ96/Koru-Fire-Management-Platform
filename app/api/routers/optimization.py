"""
optimization.py – Optimization API Router
==========================================
Senaryo verisini SA ve GA motorlarına bağlayan endpoint'ler.

Endpoints:
  POST /api/optimize/sa         → Simulated Annealing optimizasyonu
  POST /api/optimize/ga         → Genetic Algorithm optimizasyonu
  POST /api/optimize/auto       → Otomatik algoritma seçimi
  GET  /api/optimize/scenario   → Mevcut senaryo verisi (istasyonlar + kümeler)
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.optimization import CostWeights, OptimizationAlgorithm
from app.services.optimization_service import run_optimization
from app.services.routing_service import RoutingService

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


# ── Routing servis singleton (routing.py ile aynı pattern) ───────────────────

@lru_cache(maxsize=1)
def _get_routing_service() -> RoutingService:
    return RoutingService(n_clusters=12)


# ── Request / Response Schemas ───────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    """Optimizasyon isteği."""
    station_id: Optional[str] = Field(
        default=None,
        description="Başlangıç istasyonu ID (verilmezse ilk istasyon kullanılır)",
    )
    cluster_ids: Optional[List[str]] = Field(
        default=None,
        description="Hedef küme ID'leri (verilmezse tüm kümeler kullanılır)",
    )
    max_candidates: int = Field(default=20, ge=1, le=200)
    random_seed: Optional[int] = Field(default=None)
    weights: CostWeights = Field(default_factory=CostWeights)
    average_speed_kmh: float = Field(default=50.0, gt=0)


class OptimizeErrorResponse(BaseModel):
    """Hata durumunda dönen response."""
    success: bool = False
    error: str
    best_route: None = None
    algorithm: str


# ── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.post("/sa", summary="Simulated Annealing Optimizasyonu")
async def optimize_sa(request: OptimizeRequest):
    """
    Simulated Annealing algoritması ile rota optimizasyonu.

    Senaryo verisi (istasyon + HIGH_RISK kümeler) otomatik olarak routing
    servisinden alınır. Sonuç, harita üzerinde çizilecek rota bilgisini içerir.

    **Rota bulunamazsa:** `{ success: false, best_route: null }`
    → Frontend harita üzerinde hiçbir şey çizmez.
    """
    svc = _get_routing_service()
    result = run_optimization(
        routing_svc=svc,
        algorithm=OptimizationAlgorithm.SA,
        station_id=request.station_id,
        cluster_ids=request.cluster_ids,
        max_candidates=request.max_candidates,
        random_seed=request.random_seed,
        weights=request.weights,
        average_speed_kmh=request.average_speed_kmh,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/ga", summary="Genetic Algorithm Optimizasyonu")
async def optimize_ga(request: OptimizeRequest):
    """
    Genetic Algorithm ile rota optimizasyonu.

    Senaryo verisi (istasyon + HIGH_RISK kümeler) otomatik olarak routing
    servisinden alınır. Sonuç, harita üzerinde çizilecek rota bilgisini içerir.

    **Rota bulunamazsa:** `{ success: false, best_route: null }`
    → Frontend harita üzerinde hiçbir şey çizmez.
    """
    svc = _get_routing_service()
    result = run_optimization(
        routing_svc=svc,
        algorithm=OptimizationAlgorithm.GA,
        station_id=request.station_id,
        cluster_ids=request.cluster_ids,
        max_candidates=request.max_candidates,
        random_seed=request.random_seed,
        weights=request.weights,
        average_speed_kmh=request.average_speed_kmh,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/auto", summary="Otomatik Algoritma Seçimi")
async def optimize_auto(request: OptimizeRequest):
    """
    Hedef sayısına göre otomatik algoritma seçimi:
    - ≤7 hedef → Base (exhaustive permutation)
    - 8-15 hedef → SA (Simulated Annealing)
    - >15 hedef → GA (Genetic Algorithm)
    """
    svc = _get_routing_service()

    # Hedef sayısına göre algoritma seç
    if request.cluster_ids:
        target_count = len(request.cluster_ids)
    else:
        target_count = len(svc.clusters)

    if target_count <= 7:
        algo = OptimizationAlgorithm.AUTO
    elif target_count <= 15:
        algo = OptimizationAlgorithm.SA
    else:
        algo = OptimizationAlgorithm.GA

    result = run_optimization(
        routing_svc=svc,
        algorithm=algo,
        station_id=request.station_id,
        cluster_ids=request.cluster_ids,
        max_candidates=request.max_candidates,
        random_seed=request.random_seed,
        weights=request.weights,
        average_speed_kmh=request.average_speed_kmh,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/scenario", summary="Mevcut Senaryo Verisi")
async def get_scenario():
    """
    Optimizasyon için kullanılabilecek senaryo verisini döndürür.
    Frontend bu veriyi kullanarak istasyon ve küme ID'lerini seçebilir.
    """
    svc = _get_routing_service()

    stations = [
        {
            "id": s["id"],
            "name": s.get("name", ""),
            "lat": s["lat"],
            "lon": s["lon"],
        }
        for s in svc.stations
    ]

    clusters = [
        {
            "id": c["id"],
            "lat": c["lat"],
            "lon": c["lon"],
            "combined_risk_score": c.get("combined_risk_score", 0.0),
            "fire_probability": c.get("fire_probability", 0.0),
            "cluster_size": c.get("cluster_size", 0),
        }
        for c in svc.clusters
    ]

    return {
        "stations": stations,
        "clusters": clusters,
        "station_count": len(stations),
        "cluster_count": len(clusters),
        "available_algorithms": [a.value for a in OptimizationAlgorithm],
        "default_weights": CostWeights().model_dump(),
    }

"""
optimization.py – Optimization API Router
==========================================
Hocanın SA/GA optimizasyon motorlarını API'ye bağlar.

Akış:
  1) POST /api/optimize/pipeline → k_means çalıştır, pipeline_result.csv üret
  2) POST /api/optimize/run      → SA + GA çalıştır (main.py)
  3) GET  /api/optimize/sa       → SA sonuçlarını oku (tour'lar, polyline)
  4) GET  /api/optimize/ga       → GA sonuçlarını oku (tour'lar, polyline)
  5) GET  /api/optimize/scenario → Mevcut senaryo durumu
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.optimization_service import (
    get_optimization_results,
    get_scenario_info,
    run_pipeline,
    run_sa_ga_optimization,
)

router = APIRouter(prefix="/api/optimize", tags=["optimization"])


# ── Request Schemas ──────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    """K-Means pipeline isteği."""
    n: int = Field(..., ge=1, le=554, description="Yangın noktası sayısı (max 554)")
    k: int = Field(..., ge=1, le=100, description="Küme sayısı")


# ── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.post("/pipeline", summary="K-Means Pipeline Çalıştır")
async def run_kmeans_pipeline(request: PipelineRequest):
    """
    K-Medoids kümeleme pipeline'ını çalıştırır:
    1. dist_all.csv'den n adet rastgele yangın noktası seçer
    2. K-Medoids ile k kümeye ayırır
    3. Her kümeye en yakın itfaiye istasyonunu eşleştirir
    4. pipeline_result.csv üretir

    Bu adım SA/GA çalıştırmadan önce gereklidir.
    """
    result = run_pipeline(request.n, request.k)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result)
    return result


@router.post("/run", summary="SA + GA Optimizasyon Çalıştır")
async def run_optimization():
    """
    pipeline_result.csv + dist_all.csv kullanarak SA ve GA algoritmalarını çalıştırır.
    Her istasyon için en iyi tour'ları üretir ve JSON olarak kaydeder.

    Önkoşul: Önce /api/optimize/pipeline ile pipeline çalıştırılmalıdır.
    """
    result = run_sa_ga_optimization()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result)
    return result


@router.get("/sa", summary="SA Sonuçlarını Getir")
async def get_sa_results():
    """
    Simulated Annealing sonuçlarını döndürür.
    Her istasyon için: tour (rota), polyline (haritada çizim), mesafe, yük.

    **Rota yoksa**: `{ success: false, best_route: null }` → Map hiçbir şey çizmez.
    """
    result = get_optimization_results("SA")
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/ga", summary="GA Sonuçlarını Getir")
async def get_ga_results():
    """
    Genetic Algorithm sonuçlarını döndürür.
    Her istasyon için: tour (rota), polyline (haritada çizim), mesafe, yük.

    **Rota yoksa**: `{ success: false, best_route: null }` → Map hiçbir şey çizmez.
    """
    result = get_optimization_results("GA")
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.get("/scenario", summary="Mevcut Senaryo Durumu")
async def get_scenario():
    """
    Mevcut optimizasyon senaryosunun durumunu döndürür:
    - Pipeline çalıştırıldı mı?
    - SA/GA sonuçları hazır mı?
    - Pipeline noktaları (koordinatlarla)
    - Mevcut istasyonlar
    """
    return get_scenario_info()

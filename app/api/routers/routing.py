"""
routing.py
==========
İtfaiye istasyonlarından risk noktalarına rota API'si.

Endpoints:
  GET /api/routing/graph-summary       → Graf düğüm/kenar sayısı
  GET /api/routing/stations            → Tüm itfaiye istasyonları
  GET /api/routing/risk-clusters       → K-means HIGH_RISK küme merkezleri
  GET /api/routing/cost-matrix         → Station × Cluster mesafe matrisi
  GET /api/routing/route               → station_id + cluster_id → tek rota
  GET /api/routing/route-nearest       → lat + lon → en yakın ist. → en yakın küme
  GET /api/routing/all-routes          → Tüm istasyonlar → en yakın HIGH_RISK
"""

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.routing_service import RoutingService

router = APIRouter(prefix="/api/routing", tags=["routing"])


# ── Servis singleton (uygulama ömrü boyunca tek örnek) ──────────────────────

@lru_cache(maxsize=1)
def _get_service() -> RoutingService:
    """Graf ilk istekte kurulur, sonra bellekte tutulur."""
    return RoutingService(n_clusters=12)


# ── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.get("/graph-summary")
async def graph_summary():
    """
    Oluşturulan rota grafının özet bilgilerini döndürür.
    (Düğüm sayısı, kenar sayısı, istasyon / LOW / HIGH sayıları)
    """
    svc = _get_service()
    return svc.graph_summary()


@router.get("/stations")
async def list_stations():
    """Tüm itfaiye istasyonlarını döndürür."""
    svc = _get_service()
    return {"stations": svc.stations, "count": len(svc.stations)}


@router.get("/risk-clusters")
async def get_risk_clusters():
    """
    K-means ile üretilmiş HIGH_RISK küme merkezlerini döndürür.
    Her küme → temsilci koordinat, ortalama risk skoru, küme büyüklüğü.
    """
    svc = _get_service()
    return {"clusters": svc.clusters, "count": len(svc.clusters)}


@router.get("/cost-matrix")
async def cost_matrix():
    """
    Station × Cluster mesafe matrisi.
    Her istasyon için tüm kümelere uzaklık (km) ve tahmini süre (dk).
    """
    svc = _get_service()
    return svc.build_cost_matrix()


@router.get("/route")
async def get_route(
    station_id: str = Query(..., description="İtfaiye istasyonu ID'si (örn. station_1)"),
    cluster_id: str = Query(..., description="Hedef HIGH_RISK küme ID'si (örn. cluster_3)"),
):
    """
    Belirtilen istasyondan belirtilen HIGH_RISK kümesine en kısa rotayı döndürür.

    - **station_id**: `/api/routing/stations` listesinden alınabilir
    - **cluster_id**: `/api/routing/risk-clusters` listesinden alınabilir

    Yanıt içeriği:
    - `path`: rota düğümleri (tip + koordinat)
    - `total_distance_km`: toplam mesafe
    - `travel_time_min`: tahmini seyahat süresi
    - `low_to_high_transitions`: LOW→HIGH geçiş noktaları
    """
    svc = _get_service()
    result = svc.route_station_to_target(station_id, cluster_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/route-nearest")
async def route_nearest(
    lat: float = Query(..., description="Enlem"),
    lon: float = Query(..., description="Boylam"),
):
    """
    Verilen koordinata en yakın istasyonu bulur ve en yakın HIGH_RISK kümesine rotalandırır.
    """
    svc = _get_service()

    station = svc.find_nearest_station(lat, lon)
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")

    cluster = svc.find_nearest_cluster(lat, lon)
    if not cluster:
        raise HTTPException(status_code=404, detail="HIGH_RISK kümesi bulunamadı")

    route = svc.route_station_to_target(station["id"], cluster["id"])

    return {
        "query_point": {"lat": lat, "lon": lon},
        "nearest_station": station,
        "nearest_cluster": cluster,
        "route": route,
    }


@router.get("/all-routes")
async def all_routes():
    """
    Tüm itfaiye istasyonlarını en yakın HIGH_RISK kümelerine rotalandırır.
    Her rota için mesafe, süre ve LOW→HIGH geçişleri döndürür.
    """
    svc = _get_service()
    routes = svc.route_all_stations_to_nearest_high()
    valid = [r for r in routes if "error" not in r]
    return {
        "total_stations": len(svc.stations),
        "routed": len(valid),
        "routes": valid,
    }

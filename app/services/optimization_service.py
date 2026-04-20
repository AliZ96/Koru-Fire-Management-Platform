"""
Optimization Service – Senaryo Verisini SA/GA Engine'lere Bağlar

Routing servisi üzerinden istasyon + HIGH_RISK küme verisini alır,
OptimizationInput oluşturur ve SA/GA motorlarına ileterek
frontend'e normalize edilmiş sonuç döndürür.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from app.schemas.optimization import (
    CostWeights,
    OptimizationAlgorithm,
    OptimizationInput,
    OptimizationOutput,
    RouteNode,
)
from app.services.optimization_engine_base import OptimizationEngineBase
from app.services.optimization_ga_engine import GeneticAlgorithmEngine
from app.services.optimization_sa_engine import SimulatedAnnealingEngine
from app.services.routing_service import RoutingService


def _build_route_nodes_from_scenario(
    routing_svc: RoutingService,
    station_id: Optional[str],
    cluster_ids: Optional[List[str]],
) -> tuple[RouteNode, List[RouteNode]]:
    """
    Routing service verisinden start_node ve target_nodes üretir.

    station_id verilmezse ilk istasyon kullanılır.
    cluster_ids verilmezse tüm kümeler hedef olarak alınır.
    """
    # Start node (istasyon)
    station = None
    if station_id:
        for s in routing_svc.stations:
            if s["id"] == station_id:
                station = s
                break
        if station is None:
            raise ValueError(f"İstasyon bulunamadı: {station_id}")
    else:
        if not routing_svc.stations:
            raise ValueError("Hiç istasyon tanımlı değil")
        station = routing_svc.stations[0]

    start_node = RouteNode(
        node_id=station["id"],
        latitude=station["lat"],
        longitude=station["lon"],
        risk_score=0.0,
    )

    # Target nodes (HIGH_RISK küme merkezleri)
    targets: List[RouteNode] = []
    if cluster_ids:
        cluster_map = {c["id"]: c for c in routing_svc.clusters}
        for cid in cluster_ids:
            c = cluster_map.get(cid)
            if c is None:
                raise ValueError(f"Küme bulunamadı: {cid}")
            targets.append(
                RouteNode(
                    node_id=c["id"],
                    latitude=c["lat"],
                    longitude=c["lon"],
                    risk_score=min(c.get("combined_risk_score", 0.5), 1.0),
                )
            )
    else:
        for c in routing_svc.clusters:
            targets.append(
                RouteNode(
                    node_id=c["id"],
                    latitude=c["lat"],
                    longitude=c["lon"],
                    risk_score=min(c.get("combined_risk_score", 0.5), 1.0),
                )
            )

    if not targets:
        raise ValueError("Hedef küme bulunamadı")

    return start_node, targets


def _resolve_detailed_path(
    routing_svc: RoutingService,
    station_id: str,
    ordered_cluster_ids: List[str],
) -> List[Dict]:
    """
    Optimize edilmiş küme sıralamasına göre gerçek graf rotasını (Dijkstra)
    çözer ve her segment için detaylı path bilgisi döndürür.
    """
    segments: List[Dict] = []
    current_id = station_id

    for cluster_id in ordered_cluster_ids:
        route = routing_svc.route_station_to_target(current_id, cluster_id)
        if "error" in route:
            segments.append({
                "from": current_id,
                "to": cluster_id,
                "error": route["error"],
                "path": [],
                "distance_km": 0.0,
                "duration_min": 0.0,
            })
        else:
            segments.append({
                "from": current_id,
                "to": cluster_id,
                "path": route.get("path", []),
                "distance_km": route.get("total_distance_km", 0.0),
                "duration_min": route.get("travel_time_min", 0.0),
                "node_count": route.get("node_count", 0),
            })
    return segments


def _build_visualization_response(
    output: OptimizationOutput,
    routing_svc: RoutingService,
    station_id: str,
    computation_time_ms: float,
) -> Dict:
    """
    Frontend'e normalize edilmiş optimizasyon sonucu üretir.
    Map üzerinde çizilebilecek polyline + segment bilgisi içerir.

    Kurallar:
      - Rota yoksa çizilecek bir şey yok → best_route: null
      - success: false → frontend hiçbir şey render etmez
    """
    candidate = output.optimized_route_candidate
    ordered_ids = candidate.ordered_node_ids

    # Küme bilgileri
    cluster_map = {c["id"]: c for c in routing_svc.clusters}
    station_map = {s["id"]: s for s in routing_svc.stations}

    # Ordered nodes (detaylı bilgi ile)
    ordered_nodes: List[Dict] = []
    polyline: List[List[float]] = []

    # İstasyon başlangıç noktası
    st = station_map.get(station_id)
    if st:
        ordered_nodes.append({
            "node_id": st["id"],
            "lat": st["lat"],
            "lon": st["lon"],
            "node_type": "station",
            "name": st.get("name", ""),
            "risk_score": 0.0,
        })
        polyline.append([st["lat"], st["lon"]])

    for nid in ordered_ids:
        c = cluster_map.get(nid)
        if c:
            ordered_nodes.append({
                "node_id": c["id"],
                "lat": c["lat"],
                "lon": c["lon"],
                "node_type": "HIGH_RISK",
                "risk_score": c.get("combined_risk_score", 0.0),
                "fire_probability": c.get("fire_probability", 0.0),
                "cluster_size": c.get("cluster_size", 0),
            })
            polyline.append([c["lat"], c["lon"]])

    # Detaylı segmentler (graf üzerinden gerçek rota)
    segments = _resolve_detailed_path(routing_svc, station_id, ordered_ids)

    # Detaylı polyline (gerçek graf rotası)
    detailed_polyline: List[List[float]] = []
    for seg in segments:
        for node in seg.get("path", []):
            detailed_polyline.append([node.get("lat", 0), node.get("lon", 0)])

    # Güvenlik skoru (risk'in tersi, 0-100 arası)
    max_possible_risk = len(ordered_ids)  # her hedef max 1.0
    if max_possible_risk > 0:
        safety_score = round(
            (1 - candidate.aggregated_risk_score / max_possible_risk) * 100, 1
        )
    else:
        safety_score = 100.0
    safety_score = max(0.0, min(100.0, safety_score))

    return {
        "success": True,
        "algorithm": candidate.algorithm_hint.value,
        "best_route": {
            "ordered_nodes": ordered_nodes,
            "polyline": polyline,
            "detailed_polyline": detailed_polyline,
            "segments": segments,
            "total_distance_km": candidate.total_distance_km,
            "total_duration_min": candidate.total_duration_min,
            "aggregated_risk_score": candidate.aggregated_risk_score,
            "safety_score": safety_score,
            "cost_score": output.cost_score,
        },
        "candidates_evaluated": output.generated_candidates,
        "computation_time_ms": round(computation_time_ms, 2),
    }


def run_optimization(
    routing_svc: RoutingService,
    algorithm: OptimizationAlgorithm,
    station_id: Optional[str] = None,
    cluster_ids: Optional[List[str]] = None,
    max_candidates: int = 20,
    random_seed: Optional[int] = None,
    weights: Optional[CostWeights] = None,
    average_speed_kmh: float = 50.0,
) -> Dict:
    """
    Senaryo verisini optimizasyon motoruna bağlayıp sonuç döndürür.

    Returns:
        Normalize edilmiş frontend-ready response.
        Rota bulunamazsa: {"success": false, "error": "...", "best_route": null}
    """
    start_time = time.perf_counter()

    try:
        start_node, target_nodes = _build_route_nodes_from_scenario(
            routing_svc, station_id, cluster_ids
        )
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "best_route": None,
            "algorithm": algorithm.value,
        }

    payload = OptimizationInput(
        start_node=start_node,
        target_nodes=target_nodes,
        algorithm=algorithm,
        max_candidates=max_candidates,
        random_seed=random_seed,
        average_speed_kmh=average_speed_kmh,
        weights=weights or CostWeights(),
    )

    try:
        if algorithm == OptimizationAlgorithm.SA:
            engine = SimulatedAnnealingEngine(random_seed=random_seed)
        elif algorithm == OptimizationAlgorithm.GA:
            engine = GeneticAlgorithmEngine(random_seed=random_seed)
        else:
            engine = OptimizationEngineBase(random_seed=random_seed)

        output = engine.optimize(payload)
    except ValueError as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        return {
            "success": False,
            "error": str(e),
            "best_route": None,
            "algorithm": algorithm.value,
            "computation_time_ms": round(elapsed, 2),
        }

    elapsed = (time.perf_counter() - start_time) * 1000
    used_station_id = station_id or routing_svc.stations[0]["id"]

    return _build_visualization_response(output, routing_svc, used_station_id, elapsed)

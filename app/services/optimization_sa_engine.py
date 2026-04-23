"""
Simulated Annealing (SA) Optimization Engine

Mevcut OptimizationEngineBase üzerinde SA tabanlı rota optimizasyonu.
Başlangıç sıcaklığından soğuma ile en iyi rotayı arar.
"""
from __future__ import annotations

import math
import random
import time
from typing import List, Sequence

from app.schemas.optimization import (
    OptimizationAlgorithm,
    OptimizationInput,
    OptimizationOutput,
    OptimizedRouteCandidate,
    RouteNode,
)
from app.services.optimization_engine_base import OptimizationEngineBase, _RouteMetrics


class SimulatedAnnealingEngine(OptimizationEngineBase):
    """Simulated Annealing ile rota optimizasyonu."""

    def __init__(
        self,
        random_seed: int | None = None,
        initial_temperature: float = 100.0,
        cooling_rate: float = 0.95,
        stopping_temperature: float = 0.1,
        max_iterations: int = 300,
    ) -> None:
        super().__init__(random_seed=random_seed)
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.stopping_temperature = stopping_temperature
        self.max_iterations = max_iterations

    def _swap_neighbor(self, route: List[RouteNode]) -> List[RouteNode]:
        """İki rastgele düğümün yerini değiştirerek komşu çözüm üretir."""
        if len(route) < 2:
            return list(route)
        new_route = list(route)
        i, j = self._random.sample(range(len(new_route)), 2)
        new_route[i], new_route[j] = new_route[j], new_route[i]
        return new_route

    def optimize(self, payload: OptimizationInput) -> OptimizationOutput:
        """SA algoritması ile en düşük maliyetli rotayı bulur."""
        if payload.random_seed is not None:
            self._random.seed(payload.random_seed)

        targets = list(payload.target_nodes)
        if not targets:
            raise ValueError("Hedef düğüm listesi boş olamaz")

        # Başlangıç çözümü: base engine'den en iyi aday
        candidates = self.generate_candidate_routes(payload)
        current_route = candidates[0] if candidates else targets

        current_cost, current_metrics = self.evaluate_cost(payload, current_route)

        best_route = list(current_route)
        best_cost = current_cost
        best_metrics = current_metrics

        temperature = self.initial_temperature
        evaluated = 1

        for _ in range(self.max_iterations):
            if temperature < self.stopping_temperature:
                break

            neighbor = self._swap_neighbor(current_route)
            neighbor_cost, neighbor_metrics = self.evaluate_cost(payload, neighbor)
            evaluated += 1

            delta = neighbor_cost - current_cost

            # Daha iyi çözüm veya olasılıkla kabul
            if delta < 0 or self._random.random() < math.exp(-delta / temperature):
                current_route = neighbor
                current_cost = neighbor_cost
                current_metrics = neighbor_metrics

            if current_cost < best_cost:
                best_route = list(current_route)
                best_cost = current_cost
                best_metrics = current_metrics

            temperature *= self.cooling_rate

        return OptimizationOutput(
            optimized_route_candidate=OptimizedRouteCandidate(
                algorithm_hint=OptimizationAlgorithm.SA,
                ordered_node_ids=[n.node_id for n in best_route],
                total_distance_km=best_metrics.total_distance_km,
                total_duration_min=best_metrics.total_duration_min,
                aggregated_risk_score=best_metrics.aggregated_risk_score,
            ),
            cost_score=best_cost,
            generated_candidates=evaluated,
        )

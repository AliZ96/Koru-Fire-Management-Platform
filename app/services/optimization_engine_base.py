"""
Optimization Engine Base (Sprint-8 preparation)

Scope of this class:
- optimization cost function
- candidate route generation
- SA / GA integration preparation
- optimization input / output orchestration

Note:
This is intentionally a base/preparation implementation. It produces deterministic
and random candidate routes and exposes helper payloads for future SA/GA engines.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from app.schemas.optimization import (
    OptimizationAlgorithm,
    OptimizationInput,
    OptimizationOutput,
    OptimizedRouteCandidate,
    RouteNode,
)
from app.services.air_accessibility_service import haversine_distance


@dataclass
class _RouteMetrics:
    total_distance_km: float
    total_duration_min: float
    aggregated_risk_score: float


class OptimizationEngineBase:
    """Base class for route optimization preparation work."""

    def __init__(self, random_seed: int | None = None) -> None:
        self._random = random.Random(random_seed)

    def generate_candidate_routes(self, payload: OptimizationInput) -> List[List[RouteNode]]:
        """
        Generate route candidates by mixing permutation and shuffle strategies.

        For small target sets, exact permutations are evaluated first.
        For larger sets, random shuffles are used to keep runtime bounded.
        """
        targets = list(payload.target_nodes)
        max_candidates = payload.max_candidates
        candidates: List[List[RouteNode]] = []

        if len(targets) <= 7:
            for perm in itertools.permutations(targets):
                candidates.append(list(perm))
                if len(candidates) >= max_candidates:
                    break
        else:
            # Always include the original order first for baseline comparison.
            candidates.append(targets)
            while len(candidates) < max_candidates:
                shuffled = list(targets)
                self._random.shuffle(shuffled)
                if not self._contains_same_order(candidates, shuffled):
                    candidates.append(shuffled)

        return candidates

    def evaluate_cost(
        self,
        payload: OptimizationInput,
        ordered_targets: Sequence[RouteNode],
    ) -> Tuple[float, _RouteMetrics]:
        """Compute weighted optimization cost and route metrics."""
        path: List[RouteNode] = [payload.start_node, *ordered_targets]

        total_distance_km = 0.0
        total_risk = 0.0
        total_service_min = 0.0

        for idx in range(len(path) - 1):
            current_node = path[idx]
            next_node = path[idx + 1]
            segment_distance = haversine_distance(
                current_node.latitude,
                current_node.longitude,
                next_node.latitude,
                next_node.longitude,
            )
            total_distance_km += segment_distance

        for node in ordered_targets:
            total_risk += node.risk_score
            total_service_min += node.service_time_min

        travel_duration_min = (total_distance_km / payload.average_speed_kmh) * 60.0
        total_duration_min = travel_duration_min + total_service_min

        cost_score = (
            payload.weights.distance_weight * total_distance_km
            + payload.weights.duration_weight * total_duration_min
            + payload.weights.risk_weight * total_risk
        )

        metrics = _RouteMetrics(
            total_distance_km=round(total_distance_km, 3),
            total_duration_min=round(total_duration_min, 3),
            aggregated_risk_score=round(total_risk, 3),
        )
        return round(cost_score, 4), metrics

    def optimize(self, payload: OptimizationInput) -> OptimizationOutput:
        """
        Build candidates, evaluate cost, and return the best route candidate.

        This method is algorithm-agnostic for now and acts as a base engine.
        """
        if payload.random_seed is not None:
            self._random.seed(payload.random_seed)

        candidates = self.generate_candidate_routes(payload)

        best_score: float | None = None
        best_candidate: Sequence[RouteNode] | None = None
        best_metrics: _RouteMetrics | None = None

        for route in candidates:
            score, metrics = self.evaluate_cost(payload, route)
            if best_score is None or score < best_score:
                best_score = score
                best_candidate = route
                best_metrics = metrics

        if best_candidate is None or best_metrics is None or best_score is None:
            raise ValueError("No route candidate could be generated")

        return OptimizationOutput(
            optimized_route_candidate=OptimizedRouteCandidate(
                algorithm_hint=payload.algorithm,
                ordered_node_ids=[node.node_id for node in best_candidate],
                total_distance_km=best_metrics.total_distance_km,
                total_duration_min=best_metrics.total_duration_min,
                aggregated_risk_score=best_metrics.aggregated_risk_score,
            ),
            cost_score=best_score,
            generated_candidates=len(candidates),
        )

    def prepare_sa_payload(self, payload: OptimizationInput) -> Dict[str, object]:
        """Provide initial state structure for future SA implementation."""
        base_candidates = self.generate_candidate_routes(payload)
        initial_route = base_candidates[0] if base_candidates else []

        return {
            "algorithm": OptimizationAlgorithm.SA,
            "initial_route_node_ids": [n.node_id for n in initial_route],
            "initial_temperature": 100.0,
            "cooling_rate": 0.95,
            "stopping_temperature": 0.1,
            "max_iterations": 300,
        }

    def prepare_ga_payload(self, payload: OptimizationInput) -> Dict[str, object]:
        """Provide population structure for future GA implementation."""
        population = self.generate_candidate_routes(payload)

        return {
            "algorithm": OptimizationAlgorithm.GA,
            "population_node_ids": [[n.node_id for n in route] for route in population],
            "population_size": len(population),
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "elitism_count": 1,
            "max_generations": 200,
        }

    @staticmethod
    def _contains_same_order(existing: Sequence[Sequence[RouteNode]], candidate: Sequence[RouteNode]) -> bool:
        candidate_ids = [n.node_id for n in candidate]
        for route in existing:
            if [n.node_id for n in route] == candidate_ids:
                return True
        return False

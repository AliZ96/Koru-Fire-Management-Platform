"""
Genetic Algorithm (GA) Optimization Engine

Mevcut OptimizationEngineBase üzerinde GA tabanlı rota optimizasyonu.
Popülasyon tabanlı evrimsel arama ile en iyi rotayı bulur.
"""
from __future__ import annotations

from typing import List, Tuple

from app.schemas.optimization import (
    OptimizationAlgorithm,
    OptimizationInput,
    OptimizationOutput,
    OptimizedRouteCandidate,
    RouteNode,
)
from app.services.optimization_engine_base import OptimizationEngineBase, _RouteMetrics


class GeneticAlgorithmEngine(OptimizationEngineBase):
    """Genetic Algorithm ile rota optimizasyonu."""

    def __init__(
        self,
        random_seed: int | None = None,
        population_size: int = 30,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_count: int = 2,
        max_generations: int = 200,
    ) -> None:
        super().__init__(random_seed=random_seed)
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.max_generations = max_generations

    def _init_population(self, targets: List[RouteNode]) -> List[List[RouteNode]]:
        """Rastgele permütasyonlardan başlangıç popülasyonu oluşturur."""
        population: List[List[RouteNode]] = [list(targets)]  # orijinal sıra
        while len(population) < self.population_size:
            shuffled = list(targets)
            self._random.shuffle(shuffled)
            population.append(shuffled)
        return population

    def _order_crossover(
        self, parent1: List[RouteNode], parent2: List[RouteNode]
    ) -> List[RouteNode]:
        """Order Crossover (OX): TSP için uygun çaprazlama operatörü."""
        size = len(parent1)
        if size < 2:
            return list(parent1)

        start, end = sorted(self._random.sample(range(size), 2))
        child_ids = {n.node_id for n in parent1[start : end + 1]}
        child: List[RouteNode] = [None] * size  # type: ignore[list-item]
        child[start : end + 1] = parent1[start : end + 1]

        fill_pos = (end + 1) % size
        for node in parent2:
            if node.node_id not in child_ids:
                child[fill_pos] = node
                fill_pos = (fill_pos + 1) % size

        return child

    def _mutate(self, route: List[RouteNode]) -> List[RouteNode]:
        """Swap mutasyonu: iki rastgele düğüm yer değiştirir."""
        if len(route) < 2 or self._random.random() > self.mutation_rate:
            return route
        mutated = list(route)
        i, j = self._random.sample(range(len(mutated)), 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]
        return mutated

    def _tournament_select(
        self, population: List[List[RouteNode]], fitness: List[float], k: int = 3
    ) -> List[RouteNode]:
        """Tournament seçimi: k birey arasından en iyisini seçer."""
        indices = self._random.sample(range(len(population)), min(k, len(population)))
        best_idx = min(indices, key=lambda i: fitness[i])
        return list(population[best_idx])

    def optimize(self, payload: OptimizationInput) -> OptimizationOutput:
        """GA algoritması ile en düşük maliyetli rotayı bulur."""
        if payload.random_seed is not None:
            self._random.seed(payload.random_seed)

        targets = list(payload.target_nodes)
        if not targets:
            raise ValueError("Hedef düğüm listesi boş olamaz")

        population = self._init_population(targets)
        evaluated = 0

        best_route: List[RouteNode] = []
        best_cost = float("inf")
        best_metrics: _RouteMetrics | None = None

        for _ in range(self.max_generations):
            # Fitness (maliyet) hesapla
            fitness: List[float] = []
            metrics_list: List[_RouteMetrics] = []
            for individual in population:
                cost, metrics = self.evaluate_cost(payload, individual)
                fitness.append(cost)
                metrics_list.append(metrics)
                evaluated += 1

                if cost < best_cost:
                    best_cost = cost
                    best_route = list(individual)
                    best_metrics = metrics

            # Yeni nesil oluştur
            sorted_indices = sorted(range(len(fitness)), key=lambda i: fitness[i])
            new_population: List[List[RouteNode]] = []

            # Elitizm: en iyi bireyleri koru
            for idx in sorted_indices[: self.elitism_count]:
                new_population.append(list(population[idx]))

            # Çaprazlama + mutasyon ile yeni bireyler
            while len(new_population) < self.population_size:
                if self._random.random() < self.crossover_rate:
                    p1 = self._tournament_select(population, fitness)
                    p2 = self._tournament_select(population, fitness)
                    child = self._order_crossover(p1, p2)
                else:
                    child = self._tournament_select(population, fitness)

                child = self._mutate(child)
                new_population.append(child)

            population = new_population

        if best_metrics is None:
            raise ValueError("Optimizasyon sonucu üretilemedi")

        return OptimizationOutput(
            optimized_route_candidate=OptimizedRouteCandidate(
                algorithm_hint=OptimizationAlgorithm.GA,
                ordered_node_ids=[n.node_id for n in best_route],
                total_distance_km=best_metrics.total_distance_km,
                total_duration_min=best_metrics.total_duration_min,
                aggregated_risk_score=best_metrics.aggregated_risk_score,
            ),
            cost_score=best_cost,
            generated_candidates=evaluated,
        )

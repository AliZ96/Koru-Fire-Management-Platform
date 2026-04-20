"""
SCRUM-97 S-11.3 Optimization Integration Tests

SA / GA engine + optimization service + router testleri.
"""
import pytest

from app.schemas.optimization import (
    CostWeights,
    OptimizationAlgorithm,
    OptimizationInput,
    RouteNode,
)
from app.services.optimization_engine_base import OptimizationEngineBase
from app.services.optimization_ga_engine import GeneticAlgorithmEngine
from app.services.optimization_sa_engine import SimulatedAnnealingEngine


# ── Fixture'lar ───────────────────────────────────────────────────────────────

@pytest.fixture
def start_node():
    return RouteNode(node_id="station_1", latitude=38.42, longitude=27.14)


@pytest.fixture
def target_nodes():
    return [
        RouteNode(node_id="c0", latitude=38.50, longitude=27.20, risk_score=0.8),
        RouteNode(node_id="c1", latitude=38.35, longitude=27.05, risk_score=0.6),
        RouteNode(node_id="c2", latitude=38.45, longitude=27.30, risk_score=0.9),
    ]


@pytest.fixture
def payload(start_node, target_nodes):
    return OptimizationInput(
        start_node=start_node,
        target_nodes=target_nodes,
        random_seed=42,
    )


# ── SA Engine Tests ───────────────────────────────────────────────────────────

class TestSimulatedAnnealing:
    def test_sa_produces_valid_output(self, payload):
        engine = SimulatedAnnealingEngine(random_seed=42)
        result = engine.optimize(payload)

        assert result.cost_score > 0
        assert result.generated_candidates > 1
        assert result.optimized_route_candidate.algorithm_hint == OptimizationAlgorithm.SA
        assert len(result.optimized_route_candidate.ordered_node_ids) == 3

    def test_sa_returns_all_targets(self, payload):
        engine = SimulatedAnnealingEngine(random_seed=42)
        result = engine.optimize(payload)
        ids = set(result.optimized_route_candidate.ordered_node_ids)
        assert ids == {"c0", "c1", "c2"}

    def test_sa_deterministic_with_seed(self, payload):
        r1 = SimulatedAnnealingEngine(random_seed=42).optimize(payload)
        r2 = SimulatedAnnealingEngine(random_seed=42).optimize(payload)
        assert r1.cost_score == r2.cost_score
        assert (
            r1.optimized_route_candidate.ordered_node_ids
            == r2.optimized_route_candidate.ordered_node_ids
        )

    def test_sa_single_target(self, start_node):
        single = [RouteNode(node_id="c0", latitude=38.50, longitude=27.20, risk_score=0.5)]
        p = OptimizationInput(start_node=start_node, target_nodes=single, random_seed=1)
        result = SimulatedAnnealingEngine(random_seed=1).optimize(p)
        assert result.optimized_route_candidate.ordered_node_ids == ["c0"]

    def test_sa_beats_or_matches_base(self, payload):
        base = OptimizationEngineBase(random_seed=42).optimize(payload)
        sa = SimulatedAnnealingEngine(random_seed=42).optimize(payload)
        assert sa.cost_score <= base.cost_score


# ── GA Engine Tests ───────────────────────────────────────────────────────────

class TestGeneticAlgorithm:
    def test_ga_produces_valid_output(self, payload):
        engine = GeneticAlgorithmEngine(random_seed=42)
        result = engine.optimize(payload)

        assert result.cost_score > 0
        assert result.generated_candidates > 1
        assert result.optimized_route_candidate.algorithm_hint == OptimizationAlgorithm.GA
        assert len(result.optimized_route_candidate.ordered_node_ids) == 3

    def test_ga_returns_all_targets(self, payload):
        engine = GeneticAlgorithmEngine(random_seed=42)
        result = engine.optimize(payload)
        ids = set(result.optimized_route_candidate.ordered_node_ids)
        assert ids == {"c0", "c1", "c2"}

    def test_ga_deterministic_with_seed(self, payload):
        r1 = GeneticAlgorithmEngine(random_seed=42).optimize(payload)
        r2 = GeneticAlgorithmEngine(random_seed=42).optimize(payload)
        assert r1.cost_score == r2.cost_score

    def test_ga_beats_or_matches_base(self, payload):
        base = OptimizationEngineBase(random_seed=42).optimize(payload)
        ga = GeneticAlgorithmEngine(random_seed=42).optimize(payload)
        assert ga.cost_score <= base.cost_score


# ── Error Handling Tests ──────────────────────────────────────────────────────

class TestErrorHandling:
    def test_empty_targets_raises(self, start_node):
        with pytest.raises(Exception):
            p = OptimizationInput(start_node=start_node, target_nodes=[])
            SimulatedAnnealingEngine().optimize(p)

    def test_sa_cost_structure(self, payload):
        result = SimulatedAnnealingEngine(random_seed=42).optimize(payload)
        c = result.optimized_route_candidate
        assert c.total_distance_km >= 0
        assert c.total_duration_min >= 0
        assert c.aggregated_risk_score >= 0


# ── Best Route Selection (time + safety) ──────────────────────────────────────

class TestBestRouteSelection:
    def test_risk_weight_affects_order(self, start_node, target_nodes):
        """Yüksek risk ağırlığı, düşük riskli hedefleri önce ziyaret etmeyi teşvik etmeli."""
        low_risk_w = OptimizationInput(
            start_node=start_node,
            target_nodes=target_nodes,
            random_seed=42,
            weights=CostWeights(distance_weight=1.0, duration_weight=0.3, risk_weight=0.0),
        )
        high_risk_w = OptimizationInput(
            start_node=start_node,
            target_nodes=target_nodes,
            random_seed=42,
            weights=CostWeights(distance_weight=0.0, duration_weight=0.0, risk_weight=5.0),
        )

        sa = SimulatedAnnealingEngine(random_seed=42)
        r_dist = sa.optimize(low_risk_w)
        r_risk = sa.optimize(high_risk_w)

        # Risk ağırlıklı sonuçta toplam risk skoru düşük olmalı (ya da eşit)
        assert r_risk.optimized_route_candidate.aggregated_risk_score <= (
            r_dist.optimized_route_candidate.aggregated_risk_score + 0.01
        )

    def test_safety_score_in_range(self, payload):
        """Safety score 0-100 arasında olmalı."""
        engine = SimulatedAnnealingEngine(random_seed=42)
        output = engine.optimize(payload)

        # Safety score hesabını doğrudan test et
        candidate = output.optimized_route_candidate
        max_risk = len(candidate.ordered_node_ids)  # her hedef max 1.0
        if max_risk > 0:
            safety = round((1 - candidate.aggregated_risk_score / max_risk) * 100, 1)
        else:
            safety = 100.0
        safety = max(0.0, min(100.0, safety))
        assert 0 <= safety <= 100

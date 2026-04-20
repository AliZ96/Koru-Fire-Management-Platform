"""
SCRUM-97 S-11.3 Optimization Integration Tests

Hocanın SA/GA motorlarıyla entegrasyon + API servis testleri.
"""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.optimization_service import (
    _get_coord,
    _load_coordinates,
    _build_station_response,
    get_optimization_results,
    get_scenario_info,
)


# ── Fixture'lar ───────────────────────────────────────────────────────────────

SAMPLE_SA_RESULT = [
    {
        "station_id": 600,
        "assigned_fire_points": [106, 308, 163],
        "total_distance": 1.415,
        "vehicles": [
            {
                "vehicle_index": 0,
                "tour": [600, 106, 163, 600],
                "load": 96,
                "distance": 0.3519,
            },
            {
                "vehicle_index": 1,
                "tour": [600, 308, 600],
                "load": 80,
                "distance": 1.063,
            },
        ],
    }
]

SAMPLE_GA_RESULT = [
    {
        "station_id": 600,
        "assigned_fire_points": [106, 308, 163],
        "total_distance": 1.2025,
        "vehicles": [
            {
                "vehicle_index": 0,
                "tour": [600, 308, 163, 600],
                "load": 200,
                "distance": 0.8505,
            },
            {
                "vehicle_index": 1,
                "tour": [600, 106, 600],
                "load": 56,
                "distance": 0.352,
            },
        ],
    }
]


@pytest.fixture
def sa_json_file(tmp_path):
    p = tmp_path / "SA_All_Stations_Best_Solutions.json"
    p.write_text(json.dumps(SAMPLE_SA_RESULT))
    return p


@pytest.fixture
def ga_json_file(tmp_path):
    p = tmp_path / "GA_All_Stations_Best_Solutions.json"
    p.write_text(json.dumps(SAMPLE_GA_RESULT))
    return p


# ── Station Response Build Tests ─────────────────────────────────────────────

class TestBuildStationResponse:
    def test_builds_valid_response(self):
        result = _build_station_response(SAMPLE_SA_RESULT[0])
        assert result["station_id"] == 600
        assert result["total_distance"] == 1.415
        assert result["vehicle_count"] == 2
        assert len(result["vehicles"]) == 2

    def test_vehicle_has_polyline(self):
        result = _build_station_response(SAMPLE_SA_RESULT[0])
        for v in result["vehicles"]:
            assert "polyline" in v
            assert isinstance(v["polyline"], list)
            assert len(v["polyline"]) == len(v["tour"])

    def test_vehicle_tour_nodes_have_coords(self):
        result = _build_station_response(SAMPLE_SA_RESULT[0])
        for v in result["vehicles"]:
            for node in v["tour"]:
                assert "node_id" in node
                assert "lat" in node
                assert "lon" in node
                assert "node_type" in node


# ── Optimization Results Tests ────────────────────────────────────────────────

class TestGetOptimizationResults:
    def test_sa_results_with_file(self, sa_json_file):
        with patch(
            "app.services.optimization_service.SA_RESULT_JSON", sa_json_file
        ):
            result = get_optimization_results("SA")
        assert result["success"] is True
        assert result["algorithm"] == "SA"
        assert len(result["stations"]) == 1
        assert result["summary"]["total_stations"] == 1
        assert result["summary"]["total_vehicles"] == 2
        assert result["summary"]["total_fire_points"] == 3

    def test_ga_results_with_file(self, ga_json_file):
        with patch(
            "app.services.optimization_service.GA_RESULT_JSON", ga_json_file
        ):
            result = get_optimization_results("GA")
        assert result["success"] is True
        assert result["algorithm"] == "GA"

    def test_missing_file_returns_error(self, tmp_path):
        fake_path = tmp_path / "nonexistent.json"
        with patch(
            "app.services.optimization_service.SA_RESULT_JSON", fake_path
        ):
            result = get_optimization_results("SA")
        assert result["success"] is False
        assert "bulunamadı" in result["error"]
        assert result.get("best_route") is None

    def test_invalid_algorithm_returns_error(self):
        result = get_optimization_results("XYZ")
        assert result["success"] is False
        assert "Geçersiz" in result["error"]

    def test_empty_results_returns_error(self, tmp_path):
        empty_file = tmp_path / "SA_empty.json"
        empty_file.write_text("[]")
        with patch(
            "app.services.optimization_service.SA_RESULT_JSON", empty_file
        ):
            result = get_optimization_results("SA")
        assert result["success"] is False
        assert result.get("best_route") is None


# ── Scenario Info Tests ───────────────────────────────────────────────────────

class TestScenarioInfo:
    def test_scenario_structure(self):
        info = get_scenario_info()
        assert "pipeline_ready" in info
        assert "sa_results_ready" in info
        assert "ga_results_ready" in info
        assert "available_algorithms" in info
        assert "SA" in info["available_algorithms"]
        assert "GA" in info["available_algorithms"]

    def test_scenario_with_pipeline(self, tmp_path):
        csv_content = "ID; Demand; FireStation; Risk; StationDist_km\n106; 80; 600; HIGH; 0.1234\n"
        csv_file = tmp_path / "pipeline_result.csv"
        csv_file.write_text(csv_content)
        with patch(
            "app.services.optimization_service.PIPELINE_RESULT_CSV", csv_file
        ):
            info = get_scenario_info()
        assert info["pipeline_ready"] is True
        assert info["pipeline_point_count"] == 1


# ── Error Handling Tests ──────────────────────────────────────────────────────

class TestErrorHandling:
    def test_no_route_returns_null_best_route(self, tmp_path):
        fake = tmp_path / "fake.json"
        with patch(
            "app.services.optimization_service.SA_RESULT_JSON", fake
        ):
            result = get_optimization_results("SA")
        assert result["success"] is False
        assert result.get("best_route") is None

    def test_multiple_stations_summary(self, tmp_path):
        multi = SAMPLE_SA_RESULT + [
            {
                "station_id": 596,
                "assigned_fire_points": [432, 415],
                "total_distance": 2.5,
                "vehicles": [
                    {"vehicle_index": 0, "tour": [596, 432, 415, 596], "load": 150, "distance": 2.5}
                ],
            }
        ]
        p = tmp_path / "SA_multi.json"
        p.write_text(json.dumps(multi))
        with patch("app.services.optimization_service.SA_RESULT_JSON", p):
            result = get_optimization_results("SA")
        assert result["success"] is True
        assert result["summary"]["total_stations"] == 2
        assert result["summary"]["total_fire_points"] == 5
        assert result["summary"]["total_distance"] == round(1.415 + 2.5, 4)

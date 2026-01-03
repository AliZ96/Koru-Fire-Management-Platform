"""
Unit tests for risk zone clustering logic.
"""
from app.api.routers.fire_risk import _cluster_to_zones


def test_cluster_to_zones_basic():
    """Test basic clustering with synthetic data."""
    points = [
        {"lat": 41.0, "lon": 29.0, "risk_score": 0.9},
        {"lat": 41.0005, "lon": 29.0005, "risk_score": 0.85},
        {"lat": 41.001, "lon": 29.001, "risk_score": 0.8},
        {"lat": 42.0, "lon": 28.0, "risk_score": 0.1},
    ]
    
    zones = _cluster_to_zones(
        points,
        eps_km=1.0,
        min_samples=2,
        min_cluster_size=2
    )
    
    assert isinstance(zones, list)
    assert len(zones) >= 1
    
    for zone in zones:
        assert "bbox" in zone
        assert "avg_risk" in zone
        assert "count" in zone
        assert len(zone["bbox"]) == 4
        assert zone["count"] >= 2


def test_cluster_to_zones_empty():
    """Test with empty input."""
    zones = _cluster_to_zones([])
    assert zones == []


def test_cluster_to_zones_no_clusters():
    """Test when points are too sparse to form clusters."""
    points = [
        {"lat": 41.0, "lon": 29.0, "risk_score": 0.5},
        {"lat": 45.0, "lon": 35.0, "risk_score": 0.5},
    ]
    
    zones = _cluster_to_zones(
        points,
        eps_km=1.0,
        min_samples=3,
        min_cluster_size=3
    )
    
    assert zones == []

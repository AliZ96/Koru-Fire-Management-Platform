"""Integration tests for fire risk API endpoints.

Bu dosya gerçek bir uvicorn sunucusu çalıştırır. Varsayılan olarak
CI/dışı ortamlarda kırmızıya düşmemesi için entegrasyon testleri
yalnızca RUN_INTEGRATION_TESTS=1 iken çalıştırılır.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests


RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"


def _find_free_port() -> int:
    """Find an available port for test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="module")
def live_server():
    """Start a live uvicorn server for integration tests."""
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(Path(__file__).parent.parent)
    )
    
    time.sleep(1.5)
    yield base_url
    
    process.terminate()
    process.wait(timeout=5)


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)")
def test_zones_endpoint_integration(live_server):
    """Test GET /api/fire-risk/zones endpoint."""
    url = f"{live_server}/api/fire-risk/zones"
    
    response = requests.get(url, params={
        "eps_km": 5.0,
        "min_samples": 3,
        "min_cluster_size": 5,
        "limit": 1000
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "zones" in data
    assert "total" in data
    assert isinstance(data["zones"], list)
    assert isinstance(data["total"], int)
    
    for zone in data["zones"]:
        assert "zone_id" in zone
        assert "bbox" in zone
        assert "avg_risk" in zone
        assert "count" in zone
        assert len(zone["bbox"]) == 4
        assert 0 <= zone["avg_risk"] <= 1


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)")
def test_top_zones_endpoint_integration(live_server):
    """Test GET /api/fire-risk/zones/top endpoint."""
    url = f"{live_server}/api/fire-risk/zones/top"
    
    response = requests.get(url, params={
        "n": 5,
        "eps_km": 5.0,
        "min_samples": 3,
        "min_cluster_size": 5
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "zones" in data
    assert "total" in data
    assert isinstance(data["zones"], list)
    assert len(data["zones"]) <= 5
    
    risks = [z["avg_risk"] for z in data["zones"]]
    assert risks == sorted(risks, reverse=True)


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)")
def test_points_endpoint_integration(live_server):
    """Test GET /api/fire-risk/points endpoint."""
    url = f"{live_server}/api/fire-risk/points"
    response = requests.get(url, params={"limit": 100})
    
    assert response.status_code == 200
    data = response.json()
    assert "points" in data
    assert isinstance(data["points"], list)


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)")
def test_heatmap_endpoint_integration(live_server):
    """Test GET /api/fire-risk/heatmap-data endpoint."""
    url = f"{live_server}/api/fire-risk/heatmap-data"
    response = requests.get(url, params={"limit": 100})
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    for item in data[:5]:
        assert isinstance(item, list)
        assert len(item) == 3


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)")
def test_statistics_endpoint_integration(live_server):
    """Test GET /api/fire-risk/statistics endpoint."""
    url = f"{live_server}/api/fire-risk/statistics"
    response = requests.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_points" in data
    assert isinstance(data["total_points"], int)

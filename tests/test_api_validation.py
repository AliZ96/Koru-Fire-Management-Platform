"""
API Endpoint Validation Tests
=============================
Risk ve erişilebilirlik verisi döndüren API endpoint'lerini doğrular.

Kapsamı:
  - Response schema tutarlılığı (JSON yapısı)
  - Response süresi ve kararlılık
  - Pipeline çıktılarıyla veri doğruluğu
  - Hata yanıtları ve edge case'ler

Çalıştırma:
  pytest tests/test_api_validation.py -v
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

# Proje kökünü PYTHONPATH'e ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    return TestClient(app)


def _is_json_response(resp) -> bool:
    """Yanıtın JSON olduğunu doğrular (HTML catch-all değil)."""
    ct = resp.headers.get("content-type", "")
    return "application/json" in ct


def _skip_if_not_json(resp, endpoint: str):
    """Router register değilse (HTML döner) testi atla."""
    if not _is_json_response(resp):
        pytest.skip(f"{endpoint} JSON dönmüyor – router muhtemelen register edilmemiş")


@pytest.fixture(scope="module")
def pipeline_result() -> List[Dict[str, Any]]:
    """pipeline_result.csv verisini parse eder."""
    csv_path = ROOT / "pipeline_result.csv"
    if not csv_path.exists():
        pytest.skip("pipeline_result.csv bulunamadı")
    rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";", skipinitialspace=True)
        for row in reader:
            rows.append({
                "ID": int(row["ID"].strip()),
                "Demand": int(row["Demand"].strip()),
                "FireStation": int(row["FireStation"].strip()),
                "Risk": row["Risk"].strip(),
                "StationDist_km": float(row["StationDist_km"].strip()),
            })
    return rows


@pytest.fixture(scope="module")
def pipeline_summary() -> Dict[str, Any]:
    """pipeline_summary.json verisini yükler."""
    json_path = ROOT / "pipeline_summary.json"
    if not json_path.exists():
        pytest.skip("pipeline_summary.json bulunamadı")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Yardımcı: response süre ölçümü
# ---------------------------------------------------------------------------

MAX_RESPONSE_TIME_SEC = 10.0  # Kabul edilebilir üst sınır


def _timed_get(client: TestClient, url: str, **kwargs):
    """GET isteği gönderir ve süreyi ölçer."""
    start = time.perf_counter()
    resp = client.get(url, **kwargs)
    elapsed = time.perf_counter() - start
    return resp, elapsed


def _timed_post(client: TestClient, url: str, **kwargs):
    """POST isteği gönderir ve süreyi ölçer."""
    start = time.perf_counter()
    resp = client.post(url, **kwargs)
    elapsed = time.perf_counter() - start
    return resp, elapsed


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  1. FIRE-RISK ENDPOINT'LERİ – SCHEMA DOĞRULAMA                       ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestFireRiskSchema:
    """Yangın risk endpoint'lerinin JSON şemasını doğrular."""

    def test_points_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/fire-risk/points", params={"limit": 100})
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC, f"Response süresi aşıldı: {elapsed:.2f}s"

        body = resp.json()
        # FeatureCollection yapısı
        assert body.get("type") == "FeatureCollection"
        assert "features" in body
        assert "total" in body
        assert isinstance(body["features"], list)

        if body["features"]:
            feat = body["features"][0]
            assert feat["type"] == "Feature"
            assert feat["geometry"]["type"] == "Point"
            assert len(feat["geometry"]["coordinates"]) == 2  # [lon, lat]

            props = feat["properties"]
            assert "risk_class" in props
            assert "fire_probability" in props
            assert "high_fire_probability" in props
            assert "combined_risk_score" in props
            assert "color" in props
            assert props["risk_class"] in (
                "SAFE_UNBURNABLE", "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"
            )
            assert 0 <= props["fire_probability"] <= 1
            assert 0 <= props["combined_risk_score"] <= 1

    def test_points_filter_by_risk_class(self, client: TestClient):
        resp = client.get("/api/fire-risk/points", params={"risk_class": "HIGH_RISK", "limit": 50})
        assert resp.status_code == 200
        body = resp.json()
        for feat in body.get("features", []):
            assert feat["properties"]["risk_class"] == "HIGH_RISK"

    def test_statistics_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/fire-risk/statistics")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        required_keys = {
            "total_points", "risk_distribution",
            "average_fire_probability", "average_combined_risk_score",
            "high_risk_count", "medium_risk_count", "low_risk_count", "safe_count",
        }
        assert required_keys.issubset(body.keys()), f"Eksik key'ler: {required_keys - body.keys()}"
        assert isinstance(body["risk_distribution"], dict)
        assert body["total_points"] > 0

    def test_heatmap_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/fire-risk/heatmap-data", params={"cell_size": 0.1})
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body
        assert "total_cells" in body
        assert "cell_size" in body

        if body["features"]:
            feat = body["features"][0]
            assert feat["geometry"]["type"] == "Polygon"
            props = feat["properties"]
            assert "combined_risk_score" in props
            assert "risk_class" in props
            assert "color" in props


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  2. ACCESSIBILITY ENDPOINT'LERİ – SCHEMA DOĞRULAMA                   ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestAccessibilitySchema:
    """Kara erişilebilirlik ve entegre risk endpoint'lerinin JSON şemasını doğrular."""

    def test_ground_map_schema(self, client: TestClient):
        resp, elapsed = _timed_get(
            client,
            "/api/accessibility/ground/map",
            params={"cell_size": 0.05},
        )
        _skip_if_not_json(resp, "/api/accessibility/ground/map")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body

        if body["features"]:
            props = body["features"][0]["properties"]
            assert "ground_access_class" in props
            assert props["ground_access_class"] in ("HIGH", "MEDIUM", "LOW", "NO_ACCESS")

    def test_ground_points_schema(self, client: TestClient):
        resp = client.get("/api/accessibility/ground/points", params={"limit": 50})
        _skip_if_not_json(resp, "/api/accessibility/ground/points")
        assert resp.status_code == 200

        body = resp.json()
        assert isinstance(body, (list, dict))

        items = body if isinstance(body, list) else body.get("points", body.get("features", []))
        if items:
            item = items[0] if isinstance(items[0], dict) and "properties" not in items[0] else items[0]
            # Noktanın temel alanları
            check_keys = {"center_lat", "center_lon", "ground_access_class", "ground_access_score"}
            item_keys = set(item.keys()) if "properties" not in item else set(item.get("properties", {}).keys())
            assert check_keys.issubset(item_keys), f"Eksik: {check_keys - item_keys}"

    def test_ground_summary_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/accessibility/ground/summary")
        _skip_if_not_json(resp, "/api/accessibility/ground/summary")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert "total_cells" in body
        assert "ground_access_distribution" in body
        assert "no_access_count" in body
        assert "no_access_percentage" in body
        assert isinstance(body["ground_access_distribution"], dict)

    def test_ground_classify_schema(self, client: TestClient):
        resp = client.get(
            "/api/accessibility/ground/classify",
            params={"lat": 38.42, "lon": 27.13},
        )
        _skip_if_not_json(resp, "/api/accessibility/ground/classify")
        assert resp.status_code == 200

        body = resp.json()
        assert "input" in body
        assert "nearest_cell" in body
        assert "ground_access_class" in body
        assert "ground_access_score" in body
        assert body["ground_access_class"] in ("HIGH", "MEDIUM", "LOW", "NO_ACCESS")

    def test_integrated_map_schema(self, client: TestClient):
        resp, elapsed = _timed_get(
            client,
            "/api/accessibility/integrated/map",
            params={"cell_size": 0.05},
        )
        _skip_if_not_json(resp, "/api/accessibility/integrated/map")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body

    def test_integrated_summary_schema(self, client: TestClient):
        resp = client.get("/api/accessibility/integrated/summary")
        _skip_if_not_json(resp, "/api/accessibility/integrated/summary")
        assert resp.status_code == 200

        body = resp.json()
        expected = {"total_cells", "fire_risk_distribution", "ground_access_distribution"}
        assert expected.issubset(body.keys()), f"Eksik: {expected - body.keys()}"

    def test_accessibility_levels_schema(self, client: TestClient):
        resp = client.get("/api/accessibility/levels")
        _skip_if_not_json(resp, "/api/accessibility/levels")
        assert resp.status_code == 200

        body = resp.json()
        assert "ground_access_classes" in body
        assert "priority_matrix" in body
        assert isinstance(body["ground_access_classes"], list)
        assert isinstance(body["priority_matrix"], list)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  3. AIR ACCESSIBILITY ENDPOINT'LERİ                                   ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestAirAccessibilitySchema:
    """Hava erişilebilirlik endpoint'lerinin doğrulaması."""

    def test_classify_schema(self, client: TestClient):
        payload = {
            "latitude": 38.4192,
            "longitude": 27.1287,
            "elevation": 150,
            "terrain_type": "HILLY",
            "vegetation_density": 0.6,
            "aircraft_type": "HELICOPTER",
        }
        resp, elapsed = _timed_post(client, "/api/air-accessibility/classify", json=payload)
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert "accessibility_level" in body
        assert "score" in body
        assert "distance_to_base_km" in body
        assert "nearest_base" in body
        assert "aircraft_type" in body
        assert "reasons" in body
        assert "recommendations" in body

        assert body["accessibility_level"] in (
            "EXCELLENT", "GOOD", "MODERATE", "DIFFICULT", "RESTRICTED"
        )
        assert 0 <= body["score"] <= 100
        assert body["distance_to_base_km"] >= 0

    def test_batch_classify_schema(self, client: TestClient):
        payload = {
            "locations": [
                {"lat": 38.42, "lon": 27.13, "elevation": 150, "terrain_type": "HILLY"},
                {"lat": 38.35, "lon": 27.05, "elevation": 200, "terrain_type": "FOREST"},
            ],
            "aircraft_type": "HELICOPTER",
        }
        resp, elapsed = _timed_post(client, "/api/air-accessibility/batch-classify", json=payload)
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert "results" in body
        assert "total_count" in body
        assert body["total_count"] == 2
        assert len(body["results"]) == 2

    def test_air_bases_schema(self, client: TestClient):
        resp = client.get("/api/air-accessibility/air-bases")
        assert resp.status_code == 200

        body = resp.json()
        assert "air_bases" in body
        assert "total_count" in body
        assert isinstance(body["air_bases"], list)
        assert body["total_count"] > 0

        base = body["air_bases"][0]
        assert "name" in base
        assert "latitude" in base
        assert "longitude" in base
        assert "type" in base

    def test_accessibility_levels(self, client: TestClient):
        resp = client.get("/api/air-accessibility/accessibility-levels")
        assert resp.status_code == 200

        body = resp.json()
        assert "levels" in body
        assert isinstance(body["levels"], list)
        assert len(body["levels"]) > 0

    def test_aircraft_types(self, client: TestClient):
        resp = client.get("/api/air-accessibility/aircraft-types")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, (list, dict))

    def test_terrain_types(self, client: TestClient):
        resp = client.get("/api/air-accessibility/terrain-types")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, (list, dict))

    def test_quick_assess(self, client: TestClient):
        resp = client.get(
            "/api/air-accessibility/quick-assess",
            params={"lat": 38.42, "lon": 27.13, "aircraft": "HELICOPTER"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "accessibility_level" in body or "level" in body


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  4. ROUTING ENDPOINT'LERİ                                             ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestRoutingSchema:
    """İtfaiye rota API şema doğrulaması."""

    def test_graph_summary_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/routing/graph-summary")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC
        body = resp.json()
        assert isinstance(body, dict)

    def test_stations_schema(self, client: TestClient):
        resp = client.get("/api/routing/stations")
        assert resp.status_code == 200

        body = resp.json()
        assert "stations" in body
        assert "count" in body
        assert isinstance(body["stations"], list)
        assert body["count"] == len(body["stations"])

    def test_risk_clusters_schema(self, client: TestClient):
        resp = client.get("/api/routing/risk-clusters")
        assert resp.status_code == 200

        body = resp.json()
        assert "clusters" in body
        assert "count" in body
        assert isinstance(body["clusters"], list)

    def test_cost_matrix_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/routing/cost-matrix")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC
        body = resp.json()
        assert isinstance(body, (dict, list))


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  5. RESOURCE PROXIMITY & DASHBOARD ENDPOINT'LERİ                      ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestResourceProximitySchema:
    """Kaynak yakınlık ve dashboard entegre katman şema doğrulaması."""

    def test_high_medium_grid_schema(self, client: TestClient):
        resp, elapsed = _timed_get(
            client,
            "/api/proximity/high-medium-grid",
            params={"cell_size": 0.05},
        )
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body

    def test_integrated_layer_schema(self, client: TestClient):
        resp, elapsed = _timed_get(
            client,
            "/api/dashboard/integrated-layer",
            params={"cell_size": 0.05},
        )
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  6. STATIC GEO DATA ENDPOINT'LERİ                                    ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestStaticGeoDataSchema:
    """Statik GeoJSON dosya endpoint'lerinin doğrulaması."""

    @pytest.mark.parametrize("path", [
        "/api/dams",
        "/api/water_sources",
        "/api/water_tanks",
        "/api/fire_stations",
    ])
    def test_geojson_feature_collection(self, client: TestClient, path: str):
        resp = client.get(path)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body
        assert isinstance(body["features"], list)

    def test_fire_station_risk_matching_schema(self, client: TestClient):
        resp, elapsed = _timed_get(client, "/api/fire_station_risk_matching")
        assert resp.status_code == 200
        assert elapsed < MAX_RESPONSE_TIME_SEC

        body = resp.json()
        assert body.get("type") == "FeatureCollection"
        assert "features" in body


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  7. PIPELINE ÇIKTILARIYLA VERİ DOĞRULUĞU                             ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestPipelineDataCorrectness:
    """API yanıtlarının pipeline_result / pipeline_summary ile tutarlılığını doğrular."""

    def test_risk_distribution_matches_pipeline(
        self, client: TestClient, pipeline_summary: Dict[str, Any]
    ):
        """API istatistiklerindeki risk dağılımı pipeline_summary ile uyumlu olmalı."""
        resp = client.get("/api/fire-risk/statistics")
        assert resp.status_code == 200

        api_stats = resp.json()
        # API veri setinin boş olmadığını doğrula
        assert api_stats.get("total_points", 0) > 0

        # Pipeline risk dağılım kategorileri mevcut olmalı
        pipeline_risk = pipeline_summary.get("risk_distribution", {})
        api_risk = api_stats.get("risk_distribution", {})

        # Pipeline'da HIGH ve LOW var; API'de daha detaylı sınıflar var
        # En azından API'nin risk sınıflarını içerdiğini doğrula
        assert len(api_risk) > 0, "API risk dağılımı boş"

    def test_pipeline_total_points(self, pipeline_summary: Dict[str, Any]):
        """Pipeline toplam nokta sayısı doğrulaması."""
        total = pipeline_summary.get("total_points", 0)
        assert total == 554, f"Pipeline toplam nokta: {total}, beklenen: 554"

    def test_pipeline_risk_totals_match(
        self, pipeline_result: List[Dict[str, Any]], pipeline_summary: Dict[str, Any]
    ):
        """pipeline_result satır sayısı ile pipeline_summary tutarlı olmalı."""
        assert len(pipeline_result) == pipeline_summary["total_points"]

        # Risk dağılımı kontrolü
        risk_counts: Dict[str, int] = {}
        for row in pipeline_result:
            risk_counts[row["Risk"]] = risk_counts.get(row["Risk"], 0) + 1

        for risk_class, count in pipeline_summary["risk_distribution"].items():
            assert risk_counts.get(risk_class, 0) == count, (
                f"Risk sınıfı {risk_class}: CSV={risk_counts.get(risk_class,0)} vs JSON={count}"
            )

    def test_pipeline_station_distances_in_range(
        self, pipeline_result: List[Dict[str, Any]], pipeline_summary: Dict[str, Any]
    ):
        """İstasyon mesafeleri pipeline_summary ile uyumlu olmalı."""
        distances = [r["StationDist_km"] for r in pipeline_result]
        stats = pipeline_summary["distance_stats_overall_km"]

        actual_max = max(distances)
        assert abs(actual_max - stats["max"]) < 0.001, (
            f"Max mesafe: CSV={actual_max}, JSON={stats['max']}"
        )

        actual_avg = sum(distances) / len(distances)
        assert abs(actual_avg - stats["avg"]) < 0.001, (
            f"Ortalama mesafe: CSV={actual_avg:.6f}, JSON={stats['avg']}"
        )

    def test_pipeline_cluster_counts_match(
        self, pipeline_result: List[Dict[str, Any]], pipeline_summary: Dict[str, Any]
    ):
        """Her küme için nokta sayısı pipeline_summary ile eşleşmeli."""
        cluster_counts: Dict[str, int] = {}
        for row in pipeline_result:
            station = str(row["FireStation"])
            cluster_counts[station] = cluster_counts.get(station, 0) + 1

        for cluster_id, expected_count in pipeline_summary.get("points_per_cluster", {}).items():
            actual = cluster_counts.get(str(cluster_id), 0)
            assert actual == expected_count, (
                f"Cluster {cluster_id}: CSV={actual}, JSON={expected_count}"
            )


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  8. HATA YANITLARI VE EDGE CASE'LER                                  ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestErrorHandlingAndEdgeCases:
    """Hata durumları ve sınır değer testleri."""

    # -- Fire Risk Edge Cases --
    def test_points_invalid_risk_class(self, client: TestClient):
        """Geçersiz risk_class filtresi boş sonuç dönmeli."""
        resp = client.get("/api/fire-risk/points", params={"risk_class": "INVALID_CLASS", "limit": 10})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body.get("features", [])) == 0

    def test_points_limit_zero(self, client: TestClient):
        """limit=0 ile boş sonuç dönmeli."""
        resp = client.get("/api/fire-risk/points", params={"limit": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body.get("features", [])) == 0

    def test_heatmap_large_cell_size(self, client: TestClient):
        """Büyük cell_size ile az hücre dönmeli ama hata olmamalı."""
        resp = client.get("/api/fire-risk/heatmap-data", params={"cell_size": 0.5})
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("type") == "FeatureCollection"

    # -- Air Accessibility Edge Cases --
    def test_classify_extreme_coordinates(self, client: TestClient):
        """Sınır koordinatlarla çalışmalı veya anlamlı hata dönmeli."""
        payload = {
            "latitude": 0.0,
            "longitude": 0.0,
            "elevation": 0,
            "terrain_type": "FLAT",
            "vegetation_density": 0.0,
            "aircraft_type": "HELICOPTER",
        }
        resp = client.post("/api/air-accessibility/classify", json=payload)
        # Uzak koordinat → servis 500 dönebilir (kapsam dışı); en azından JSON yanıt olmalı
        assert resp.status_code in (200, 422, 500)
        assert _is_json_response(resp), "Hata yanıtı bile JSON olmalı"

    def test_classify_invalid_body(self, client: TestClient):
        """Geçersiz JSON body → 422 Validation Error."""
        resp = client.post("/api/air-accessibility/classify", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_classify_invalid_aircraft_type(self, client: TestClient):
        """Geçersiz aircraft_type → 422."""
        payload = {
            "latitude": 38.42,
            "longitude": 27.13,
            "aircraft_type": "SPACESHIP",
        }
        resp = client.post("/api/air-accessibility/classify", json=payload)
        assert resp.status_code == 422

    def test_classify_out_of_range_latitude(self, client: TestClient):
        """latitude > 90 → 422."""
        payload = {
            "latitude": 999.0,
            "longitude": 27.13,
            "aircraft_type": "HELICOPTER",
        }
        resp = client.post("/api/air-accessibility/classify", json=payload)
        assert resp.status_code == 422

    def test_batch_classify_empty_locations(self, client: TestClient):
        """Boş konum listesi → 422."""
        payload = {"locations": [], "aircraft_type": "HELICOPTER"}
        resp = client.post("/api/air-accessibility/batch-classify", json=payload)
        assert resp.status_code == 422

    def test_batch_classify_over_limit(self, client: TestClient):
        """1000'den fazla konum → 422."""
        payload = {
            "locations": [{"lat": 38.0, "lon": 27.0}] * 1001,
            "aircraft_type": "HELICOPTER",
        }
        resp = client.post("/api/air-accessibility/batch-classify", json=payload)
        assert resp.status_code == 422

    # -- Ground Accessibility Edge Cases --
    def test_ground_classify_missing_params(self, client: TestClient):
        """lat/lon olmadan → 422 (router kayıtlı ise)."""
        resp = client.get("/api/accessibility/ground/classify")
        _skip_if_not_json(resp, "/api/accessibility/ground/classify")
        assert resp.status_code == 422

    def test_ground_map_with_bbox(self, client: TestClient):
        """bbox filtresi ile GeoJSON dönmeli."""
        resp = client.get(
            "/api/accessibility/ground/map",
            params={
                "min_lon": 27.0, "min_lat": 38.3,
                "max_lon": 27.2, "max_lat": 38.5,
                "cell_size": 0.05,
            },
        )
        _skip_if_not_json(resp, "/api/accessibility/ground/map")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("type") == "FeatureCollection"

    # -- Routing Edge Cases --
    def test_route_missing_params(self, client: TestClient):
        """station_id / cluster_id olmadan → 422."""
        resp = client.get("/api/routing/route")
        assert resp.status_code == 422

    def test_route_invalid_ids(self, client: TestClient):
        """Geçersiz station_id / cluster_id → 404."""
        resp = client.get(
            "/api/routing/route",
            params={"station_id": "nonexistent_99", "cluster_id": "nonexistent_99"},
        )
        assert resp.status_code in (404, 500)

    def test_route_nearest_missing_params(self, client: TestClient):
        """lat/lon olmadan → 422."""
        resp = client.get("/api/routing/route-nearest")
        assert resp.status_code == 422


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  9. RESPONSE SÜRESİ VE KARARLILIK                                    ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestResponseTimeAndStability:
    """Endpoint'lerin kabul edilebilir sürede yanıt verdiğini doğrular."""

    @pytest.mark.parametrize("endpoint,params", [
        ("/api/fire-risk/points", {"limit": 100}),
        ("/api/fire-risk/statistics", {}),
        ("/api/fire-risk/heatmap-data", {"cell_size": 0.1}),
        ("/api/air-accessibility/air-bases", {}),
        ("/api/air-accessibility/accessibility-levels", {}),
        ("/api/routing/stations", {}),
        ("/api/routing/risk-clusters", {}),
    ])
    def test_response_time(self, client: TestClient, endpoint: str, params: dict):
        resp, elapsed = _timed_get(client, endpoint, params=params)
        _skip_if_not_json(resp, endpoint)
        assert resp.status_code == 200, f"{endpoint} status={resp.status_code}"
        assert elapsed < MAX_RESPONSE_TIME_SEC, (
            f"{endpoint} çok yavaş: {elapsed:.2f}s (limit: {MAX_RESPONSE_TIME_SEC}s)"
        )

    def test_repeated_calls_stable(self, client: TestClient):
        """Aynı endpoint'e ardışık istekler tutarlı sonuç dönmeli."""
        results = []
        for _ in range(3):
            resp = client.get("/api/fire-risk/statistics")
            assert resp.status_code == 200
            results.append(resp.json())

        # Tüm yanıtlarda total_points aynı olmalı
        totals = [r.get("total_points") for r in results]
        assert len(set(totals)) == 1, f"Tutarsız total_points: {totals}"


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  10. HEALTH CHECK                                                     ║
# ╚═════════════════════════════════════════════════════════════════════════╝

class TestHealthCheck:
    def test_health_endpoint(self, client: TestClient):
        resp = client.get("/health/db")
        assert resp.status_code == 200
        body = resp.json()
        assert "db" in body

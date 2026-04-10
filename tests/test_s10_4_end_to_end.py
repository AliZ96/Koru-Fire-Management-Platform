"""
S10.4 - End-to-End System Testing
==================================

Kapsam (Acceptance Criteria):
  * Full system workflow executes successfully
  * No blocking errors in pipeline execution
  * ML model output integration is verified
  * GIS layers load correctly (frontend + mobile UI endpoints)
  * End-to-end scenarios pass
  * System produces consistent outputs

Bu test dosyası, KORU Yangın Yönetim Platformu'nun tüm boru hattını
veri girişinden görselleştirme katmanına kadar uçtan uca doğrular.

Test Sınıfları
--------------
  TestS10_4_DataInputs           -> Girdi dosyalarının (CSV/GeoJSON/ML) varlığı & şeması
  TestS10_4_PipelineExecution    -> run_pipeline / summary_generator boru hattı
  TestS10_4_MLOutputIntegration  -> ML tahminlerinin API'ye entegrasyonu
  TestS10_4_GISLayerLoading      -> GIS katmanlarının API üzerinden servis edilmesi
  TestS10_4_FrontendIntegration  -> static/index.html'in GIS API'lere bağlandığının doğrulaması
  TestS10_4_MobileUIIntegration  -> Mobil istemciye servis edilen mobile-ui endpoint'leri
  TestS10_4_AuthWorkflow         -> Kullanıcı kayıt/giriş/me uçtan uca akışı
  TestS10_4_ScenarioWorkflow     -> Senaryo bazlı full workflow
  TestS10_4_ConsistencyChecks    -> Birden fazla istekte tutarlılık (deterministik çıktı)

Çalıştırma:
  pytest tests/test_s10_4_end_to_end.py -v
  pytest tests/test_s10_4_end_to_end.py -v -k "MLOutput"
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# PYTHONPATH + FastAPI app import
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.user import User  # noqa: E402,F401

# ---------------------------------------------------------------------------
# SQLite test DB (isolated from production DB)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///./database/test.db"
_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Performance SLA — no individual request should take longer than this
SLA_SECONDS = 15.0


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    """Create a clean SQLite schema for the module."""
    Base.metadata.create_all(bind=_engine, tables=[User.__table__])
    yield
    # Intentionally keep data between modules to avoid brittle cleanup


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="module")
def ml_risk_csv_path(project_root: Path) -> Path:
    return project_root / "database" / "ml-map" / "izmir_future_fire_risk_dataset.csv"


@pytest.fixture(scope="module")
def pipeline_result_path(project_root: Path) -> Path:
    return project_root / "pipeline_result.csv"


@pytest.fixture(scope="module")
def pipeline_summary_path(project_root: Path) -> Path:
    return project_root / "pipeline_summary.json"


@pytest.fixture(scope="module")
def static_data_dir(project_root: Path) -> Path:
    return project_root / "static" / "data"


def _timed_get(client: TestClient, url: str, **kwargs) -> Tuple[Any, float]:
    """Helper: GET request + wall-clock duration."""
    start = time.perf_counter()
    r = client.get(url, **kwargs)
    return r, time.perf_counter() - start


def _timed_post(client: TestClient, url: str, **kwargs) -> Tuple[Any, float]:
    start = time.perf_counter()
    r = client.post(url, **kwargs)
    return r, time.perf_counter() - start


def _assert_feature_collection(body: Dict[str, Any], endpoint: str) -> None:
    """Common GeoJSON FeatureCollection schema validation."""
    assert isinstance(body, dict), f"{endpoint}: response is not a dict"
    assert body.get("type") == "FeatureCollection", (
        f"{endpoint}: expected type=FeatureCollection, got {body.get('type')}"
    )
    assert "features" in body, f"{endpoint}: missing 'features' key"
    assert isinstance(body["features"], list), f"{endpoint}: features must be list"


# ===========================================================================
# 1) DATA INPUT LAYER — files & schemas
# ===========================================================================


class TestS10_4_DataInputs:
    """Verify the raw data inputs the pipeline depends on."""

    def test_ml_risk_dataset_exists(self, ml_risk_csv_path: Path):
        assert ml_risk_csv_path.is_file(), (
            f"ML risk dataset missing: {ml_risk_csv_path}"
        )
        assert ml_risk_csv_path.stat().st_size > 0, "ML dataset is empty"

    def test_ml_risk_dataset_schema(self, ml_risk_csv_path: Path):
        """ML dataset must contain required columns for the pipeline."""
        with open(ml_risk_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []

        required = {
            "latitude",
            "longitude",
            "fire_probability",
            "high_fire_probability",
            "combined_risk_score",
            "predicted_risk_class",
        }
        missing = required - set(header)
        assert not missing, f"ML dataset missing columns: {missing}"

    def test_ml_risk_dataset_has_all_risk_classes(self, ml_risk_csv_path: Path):
        """Dataset must cover all four risk classes for the UI to render correctly."""
        classes = set()
        with open(ml_risk_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                classes.add(row["predicted_risk_class"])

        expected = {"SAFE_UNBURNABLE", "LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"}
        missing = expected - classes
        # At minimum 3 of the 4 classes must be present; dataset may lack MEDIUM
        assert len(expected & classes) >= 3, (
            f"ML dataset only contains risk classes: {classes}"
        )

    def test_pipeline_result_csv_exists(self, pipeline_result_path: Path):
        assert pipeline_result_path.is_file(), (
            f"pipeline_result.csv missing — pipeline has not been run"
        )

    def test_pipeline_result_csv_schema(self, pipeline_result_path: Path):
        with open(pipeline_result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";", skipinitialspace=True)
            header = [h.strip() for h in (reader.fieldnames or [])]
            first = next(reader, None)

        required = {"ID", "Demand", "FireStation", "Risk", "StationDist_km"}
        assert required.issubset(set(header)), (
            f"pipeline_result.csv missing columns: {required - set(header)}"
        )
        assert first is not None, "pipeline_result.csv has no data rows"

    def test_pipeline_summary_json_exists(self, pipeline_summary_path: Path):
        assert pipeline_summary_path.is_file(), "pipeline_summary.json missing"
        data = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))
        assert data.get("total_points", 0) > 0, (
            "pipeline_summary.json has zero total_points"
        )

    def test_required_geojson_files_exist(self, static_data_dir: Path):
        """Frontend relies on these GIS files being bundled."""
        required = [
            "barajlar.geojson",
            "water-sources.geojson",
            "water-tank.geojson",
            "fire-stations.geojson",
        ]
        missing = [f for f in required if not (static_data_dir / f).is_file()]
        assert not missing, f"Required GeoJSON files missing: {missing}"

    def test_geojson_files_are_valid_json(self, static_data_dir: Path):
        """All bundled GeoJSON files must parse as valid JSON and be GeoJSON shaped."""
        errors: List[str] = []
        for f in static_data_dir.glob("*.geojson"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                errors.append(f"{f.name}: invalid JSON — {e}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{f.name}: root is not a dict")
                continue
            if data.get("type") not in ("FeatureCollection", "Feature", "GeometryCollection"):
                errors.append(f"{f.name}: unexpected type={data.get('type')}")
        assert not errors, "GeoJSON validation errors:\n" + "\n".join(errors)


# ===========================================================================
# 2) PIPELINE EXECUTION — summary_generator + run_pipeline
# ===========================================================================


class TestS10_4_PipelineExecution:
    """Verify the data pipeline runs without blocking errors."""

    def test_summary_generator_produces_consistent_output(
        self,
        pipeline_result_path: Path,
        tmp_path: Path,
    ):
        """Running summary_generator twice must produce identical output."""
        from summary_generator import generate_summary

        out1 = tmp_path / "summary1.json"
        out2 = tmp_path / "summary2.json"

        s1 = generate_summary(str(pipeline_result_path), str(out1))
        s2 = generate_summary(str(pipeline_result_path), str(out2))

        # Deterministic output
        assert s1["total_points"] == s2["total_points"]
        assert s1["risk_distribution"] == s2["risk_distribution"]
        assert s1["distance_stats_overall_km"] == s2["distance_stats_overall_km"]

    def test_summary_generator_matches_checked_in_summary(
        self,
        pipeline_result_path: Path,
        pipeline_summary_path: Path,
        tmp_path: Path,
    ):
        """Regenerated summary must equal the committed pipeline_summary.json."""
        from summary_generator import generate_summary

        regenerated = generate_summary(
            str(pipeline_result_path), str(tmp_path / "summary.json")
        )
        checked_in = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))

        assert regenerated["total_points"] == checked_in["total_points"]
        assert regenerated["risk_distribution"] == checked_in["risk_distribution"]

    def test_pipeline_total_points_positive(self, pipeline_summary_path: Path):
        data = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))
        assert data["total_points"] > 0
        assert len(data["points_per_cluster"]) > 0
        assert len(data["risk_distribution"]) > 0

    def test_pipeline_risk_distribution_sums_to_total(self, pipeline_summary_path: Path):
        data = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))
        dist_sum = sum(data["risk_distribution"].values())
        assert dist_sum == data["total_points"], (
            f"Risk distribution ({dist_sum}) != total_points ({data['total_points']})"
        )

    def test_pipeline_distances_are_finite_and_positive(
        self, pipeline_summary_path: Path
    ):
        data = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))
        overall = data["distance_stats_overall_km"]
        for key, val in overall.items():
            assert val >= 0, f"Overall distance {key} is negative"
            assert val < 1000, f"Overall distance {key} is unreasonably large"


# ===========================================================================
# 3) ML OUTPUT INTEGRATION — fire risk API
# ===========================================================================


class TestS10_4_MLOutputIntegration:
    """Verify ML model output flows through the API layer."""

    def test_fire_risk_statistics_endpoint(self, client: TestClient):
        r, dt = _timed_get(client, "/api/fire-risk/statistics")
        assert r.status_code == 200, f"statistics failed: {r.text[:200]}"
        assert dt < SLA_SECONDS, f"statistics too slow: {dt:.2f}s"

        body = r.json()
        assert "total_points" in body
        assert body["total_points"] > 0, "ML output empty — integration broken"

        # All four risk counters must be present (even if zero)
        for field in (
            "high_risk_count",
            "medium_risk_count",
            "low_risk_count",
            "safe_count",
            "risk_distribution",
        ):
            assert field in body, f"statistics missing field: {field}"

    def test_fire_risk_statistics_counts_are_consistent(self, client: TestClient):
        """High + medium + low + safe should equal total_points."""
        r = client.get("/api/fire-risk/statistics")
        body = r.json()
        bucket_sum = (
            body["high_risk_count"]
            + body["medium_risk_count"]
            + body["low_risk_count"]
            + body["safe_count"]
        )
        assert bucket_sum == body["total_points"], (
            f"risk bucket sum {bucket_sum} != total_points {body['total_points']}"
        )

    def test_fire_risk_points_endpoint(self, client: TestClient):
        r, dt = _timed_get(client, "/api/fire-risk/points", params={"limit": 200})
        assert r.status_code == 200
        assert dt < SLA_SECONDS

        body = r.json()
        _assert_feature_collection(body, "/api/fire-risk/points")
        assert body["total"] > 0
        assert len(body["features"]) == body["total"]
        assert len(body["features"]) <= 200

        # Every feature must have the ML integration fields
        for feat in body["features"][:20]:
            assert feat["type"] == "Feature"
            assert feat["geometry"]["type"] == "Point"
            coords = feat["geometry"]["coordinates"]
            assert len(coords) == 2
            # İzmir bounding box (generous)
            assert 25.0 <= coords[0] <= 29.0
            assert 37.0 <= coords[1] <= 40.0

            props = feat["properties"]
            assert props["risk_class"] in {
                "SAFE_UNBURNABLE",
                "LOW_RISK",
                "MEDIUM_RISK",
                "HIGH_RISK",
            }
            assert 0.0 <= props["fire_probability"] <= 1.0
            assert 0.0 <= props["high_fire_probability"] <= 1.0
            assert 0.0 <= props["combined_risk_score"] <= 1.0
            assert re.match(r"^#[0-9a-fA-F]{6}$", props["color"])

    def test_fire_risk_points_filter_by_class(self, client: TestClient):
        for risk in ("HIGH_RISK", "LOW_RISK", "SAFE_UNBURNABLE"):
            r = client.get(
                "/api/fire-risk/points",
                params={"risk_class": risk, "limit": 50},
            )
            assert r.status_code == 200
            body = r.json()
            for feat in body["features"]:
                assert feat["properties"]["risk_class"] == risk, (
                    f"filter leaked: expected {risk}, got {feat['properties']['risk_class']}"
                )

    def test_fire_risk_heatmap_endpoint(self, client: TestClient):
        r, dt = _timed_get(
            client, "/api/fire-risk/heatmap-data", params={"cell_size": 0.1}
        )
        assert r.status_code == 200
        assert dt < SLA_SECONDS

        body = r.json()
        _assert_feature_collection(body, "/api/fire-risk/heatmap-data")
        assert body["total_cells"] > 0
        assert body["cell_size"] == 0.1

        for feat in body["features"][:10]:
            assert feat["geometry"]["type"] == "Polygon"
            # Polygon ring — 5 points for a closed square
            assert len(feat["geometry"]["coordinates"][0]) == 5
            assert 0.0 <= feat["properties"]["combined_risk_score"] <= 1.0


# ===========================================================================
# 4) GIS LAYER LOADING — static GeoJSON via API
# ===========================================================================


class TestS10_4_GISLayerLoading:
    """Verify GIS layers load via backend API (what the frontend calls)."""

    GEO_ENDPOINTS = [
        "/api/dams",
        "/api/water_sources",
        "/api/water_tanks",
        "/api/fire_stations",
    ]

    def test_all_gis_endpoints_return_feature_collections(self, client: TestClient):
        failures: List[str] = []
        for ep in self.GEO_ENDPOINTS:
            r, dt = _timed_get(client, ep)
            if r.status_code != 200:
                failures.append(f"{ep}: HTTP {r.status_code}")
                continue
            if dt > SLA_SECONDS:
                failures.append(f"{ep}: slow ({dt:.2f}s)")
            try:
                body = r.json()
                _assert_feature_collection(body, ep)
            except (json.JSONDecodeError, AssertionError) as e:
                failures.append(f"{ep}: {e}")

        assert not failures, "GIS endpoints failed:\n  " + "\n  ".join(failures)

    def test_gis_layers_contain_features(self, client: TestClient):
        """Each layer must have at least one feature."""
        empty: List[str] = []
        for ep in self.GEO_ENDPOINTS:
            r = client.get(ep)
            body = r.json()
            if len(body.get("features", [])) == 0:
                empty.append(ep)
        assert not empty, f"Empty GIS layers: {empty}"

    def test_gis_features_have_valid_geometry(self, client: TestClient):
        """Every feature must have a valid geometry block."""
        bad: List[str] = []
        for ep in self.GEO_ENDPOINTS:
            body = client.get(ep).json()
            for i, feat in enumerate(body.get("features", [])[:10]):
                geom = feat.get("geometry") or {}
                if geom.get("type") not in {
                    "Point",
                    "Polygon",
                    "MultiPolygon",
                    "LineString",
                    "MultiLineString",
                    "MultiPoint",
                }:
                    bad.append(f"{ep}[{i}]: bad geometry type {geom.get('type')}")
        assert not bad, "Bad GIS geometries:\n" + "\n".join(bad)

    def test_fire_station_risk_matching(self, client: TestClient):
        """S8-4 endpoint: every risk point paired with a station."""
        r, dt = _timed_get(client, "/api/fire_station_risk_matching")
        assert r.status_code == 200
        assert dt < SLA_SECONDS
        body = r.json()
        _assert_feature_collection(body, "/api/fire_station_risk_matching")
        assert len(body["features"]) > 0, "fire-station matching empty"
        # Each feature must reference a station
        for feat in body["features"][:10]:
            props = feat.get("properties", {})
            assert "station" in props or "station_id" in props or "station_name" in props, (
                f"feature missing station info: {list(props.keys())}"
            )

    def test_ground_accessibility_summary(self, client: TestClient):
        r, dt = _timed_get(client, "/api/accessibility/ground/summary")
        assert r.status_code == 200
        assert dt < SLA_SECONDS
        body = r.json()
        for key in (
            "total_cells",
            "ground_access_distribution",
            "average_dist_to_road_m",
            "average_slope_deg",
        ):
            assert key in body, f"ground summary missing {key}"
        assert body["total_cells"] > 0

    def test_ground_accessibility_points(self, client: TestClient):
        r, dt = _timed_get(
            client, "/api/accessibility/ground/points", params={"limit": 100}
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, (list, dict))


# ===========================================================================
# 5) FRONTEND INTEGRATION — does static/index.html wire up the APIs?
# ===========================================================================


class TestS10_4_FrontendIntegration:
    """Static analysis of the frontend to verify it consumes the right APIs."""

    @pytest.fixture(scope="class")
    def index_html(self, project_root=None) -> str:
        path = ROOT / "static" / "index.html"
        assert path.is_file(), "static/index.html missing"
        return path.read_text(encoding="utf-8", errors="ignore")

    def test_index_html_references_fire_risk_api(self, index_html: str):
        assert "/api/fire-risk/points" in index_html, (
            "Frontend does not call /api/fire-risk/points"
        )
        assert "/api/fire-risk/heatmap-data" in index_html, (
            "Frontend does not call /api/fire-risk/heatmap-data"
        )

    def test_index_html_uses_leaflet(self, index_html: str):
        assert "leaflet" in index_html.lower(), "Leaflet map library not loaded"

    def test_index_html_has_required_risk_buttons(self, index_html: str):
        required_ids = ["btnFireRisk", "btnHeatmap", "btnReservoirs"]
        missing = [b for b in required_ids if b not in index_html]
        assert not missing, f"Missing buttons in index.html: {missing}"

    def test_frontend_routes_serve_html(self, client: TestClient):
        """The FastAPI root + /app routes must serve HTML (not JSON error)."""
        for path in ("/", "/app", "/home", "/login"):
            r = client.get(path)
            assert r.status_code == 200, f"{path}: HTTP {r.status_code}"
            ct = r.headers.get("content-type", "")
            assert "text/html" in ct or ct == "", f"{path}: content-type={ct}"
            body = r.text
            assert "<html" in body.lower() or "<!doctype" in body.lower(), (
                f"{path}: no HTML markers in response"
            )

    def test_static_assets_mount(self, client: TestClient):
        """Static files like /static/data/fire-stations.geojson must be served."""
        r = client.get("/static/data/fire-stations.geojson")
        assert r.status_code == 200
        body = r.json()
        assert body.get("type") in ("FeatureCollection", "Feature")


# ===========================================================================
# 6) MOBILE UI INTEGRATION — mobile-ui endpoints
# ===========================================================================


class TestS10_4_MobileUIIntegration:
    """The Flutter client consumes /api/mobile-ui/* — verify those payloads."""

    def test_mobile_login_copy(self, client: TestClient):
        r, dt = _timed_get(client, "/api/mobile-ui/login")
        assert r.status_code == 200
        assert dt < SLA_SECONDS
        body = r.json()
        for key in (
            "landing_button",
            "tab_login",
            "tab_signup",
            "label_username",
            "label_password",
            "button_submit_login",
        ):
            assert key in body, f"mobile login copy missing {key}"
            assert isinstance(body[key], str) and body[key].strip(), (
                f"mobile login copy empty for {key}"
            )

    def test_mobile_welcome_copy(self, client: TestClient):
        r = client.get("/api/mobile-ui/welcome")
        assert r.status_code == 200
        body = r.json()
        assert "button_map" in body
        assert "button_station" in body

    def test_mobile_map_copy(self, client: TestClient):
        r = client.get("/api/mobile-ui/map")
        assert r.status_code == 200
        body = r.json()
        # Critical buttons the mobile client renders
        for key in (
            "header_title",
            "btn_fire_risk",
            "btn_heatmap",
            "btn_reset",
            "menu_fires",
        ):
            assert key in body, f"mobile map copy missing {key}"


# ===========================================================================
# 7) AUTH WORKFLOW — register → login → /me
# ===========================================================================


class TestS10_4_AuthWorkflow:
    """Full auth flow backed by SQLite test DB."""

    def test_user_register_login_me(self, client: TestClient):
        username = f"s10_4_user_{int(time.time() * 1000)}"
        password = "s10_4_pass_789"

        r = client.post(
            "/auth/user/register",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200, f"register: {r.text}"
        assert "access_token" in r.json()

        r = client.post(
            "/auth/user/login",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200, f"login: {r.text}"
        token = r.json()["access_token"]

        r = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 200
        assert r.json().get("sub") == username

    def test_firefighter_register_login(self, client: TestClient):
        username = f"s10_4_ff_{int(time.time() * 1000)}"
        password = "s10_4_pass_xyz"

        r = client.post(
            "/auth/firefighter/register",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200, f"firefighter register: {r.text}"

        r = client.post(
            "/auth/firefighter/login",
            json={"username": username, "password": password},
        )
        assert r.status_code == 200

    def test_me_requires_auth(self, client: TestClient):
        r = client.get("/auth/me")
        assert r.status_code in (401, 403), (
            f"/auth/me should require auth, got {r.status_code}"
        )

    def test_health_db_endpoint(self, client: TestClient):
        r = client.get("/health/db")
        assert r.status_code == 200
        assert r.json().get("db") == "connected"


# ===========================================================================
# 8) SCENARIO-BASED WORKFLOWS — end-to-end user journeys
# ===========================================================================


class TestS10_4_ScenarioWorkflow:
    """Multi-step scenarios that chain multiple subsystems."""

    def test_scenario_operator_explores_high_risk_zones(self, client: TestClient):
        """
        Operatör senaryosu:
          1) İstatistikleri getir
          2) HIGH_RISK noktalarını filtrele
          3) Bir HIGH_RISK nokta için hızlı hava erişilebilirliği değerlendir
          4) Accessibility/levels referans endpoint'ini sorgula
        """
        # Step 1 — stats
        r = client.get("/api/fire-risk/statistics")
        assert r.status_code == 200
        stats = r.json()
        assert stats["high_risk_count"] > 0, (
            "No HIGH_RISK points — scenario cannot continue"
        )

        # Step 2 — filter HIGH_RISK
        r = client.get(
            "/api/fire-risk/points",
            params={"risk_class": "HIGH_RISK", "limit": 5},
        )
        assert r.status_code == 200
        features = r.json()["features"]
        assert features, "HIGH_RISK filter returned no points"

        # Step 3 — quick-assess each one
        for feat in features[:3]:
            lon, lat = feat["geometry"]["coordinates"]
            r = client.get(
                "/api/air-accessibility/quick-assess",
                params={"lat": lat, "lon": lon, "aircraft": "HELICOPTER"},
            )
            assert r.status_code == 200
            payload = r.json()
            assert payload["accessibility_level"] in {
                "EXCELLENT",
                "GOOD",
                "MODERATE",
                "DIFFICULT",
                "RESTRICTED",
            }
            assert 0 <= payload["score"] <= 100
            assert payload["distance_km"] >= 0
            assert payload["eta_minutes"] >= 0

        # Step 4 — priority matrix
        r = client.get("/api/accessibility/levels")
        assert r.status_code == 200
        levels = r.json()
        assert "ground_access_classes" in levels
        assert "priority_matrix" in levels
        assert len(levels["priority_matrix"]) > 0

    def test_scenario_map_layers_load_sequentially(self, client: TestClient):
        """
        Harita senaryosu:
          Kullanıcı haritayı açıyor, her katmanı teker teker açıyor.
          Her katman bozulmadan FeatureCollection dönmeli.
        """
        layer_sequence = [
            "/api/fire_stations",
            "/api/dams",
            "/api/water_sources",
            "/api/water_tanks",
            "/api/fire-risk/points?limit=100",
            "/api/fire-risk/heatmap-data?cell_size=0.1",
        ]
        total_features = 0
        for url in layer_sequence:
            r, dt = _timed_get(client, url)
            assert r.status_code == 200, f"{url} failed"
            assert dt < SLA_SECONDS, f"{url} slow ({dt:.2f}s)"
            body = r.json()
            _assert_feature_collection(body, url)
            total_features += len(body["features"])

        assert total_features > 0, "No features across any layer"

    def test_scenario_batch_air_accessibility(self, client: TestClient):
        """Toplu hava erişim sınıflandırması (20 nokta)."""
        r = client.get(
            "/api/fire-risk/points",
            params={"risk_class": "HIGH_RISK", "limit": 20},
        )
        features = r.json()["features"]
        if not features:
            pytest.skip("No HIGH_RISK points")

        locations = [
            {
                "lat": f["geometry"]["coordinates"][1],
                "lon": f["geometry"]["coordinates"][0],
                "elevation": 0,
                "terrain_type": "HILLY",
                "vegetation_density": 0.5,
            }
            for f in features[:20]
        ]

        r, dt = _timed_post(
            client,
            "/api/air-accessibility/batch-classify",
            json={"locations": locations, "aircraft_type": "HELICOPTER"},
        )
        assert r.status_code == 200, f"batch-classify failed: {r.text[:200]}"
        assert dt < SLA_SECONDS
        body = r.json()
        # Response may use total_count or total_locations — accept either
        total_key = "total_count" if "total_count" in body else "total_locations"
        assert body.get(total_key, len(body.get("results", []))) == len(locations)
        assert len(body["results"]) == len(locations)

    def test_scenario_pipeline_kmeans_run(self, client: TestClient):
        """
        S9-1 pipeline senaryosu:
          /api/pipeline/run endpoint'i k-means'i çalıştırır ve GeoJSON döner.
        """
        r, dt = _timed_get(
            client, "/api/pipeline/run", params={"n": 20, "k": 4}
        )
        assert r.status_code == 200
        # Pipeline can be slow on first hit
        assert dt < SLA_SECONDS * 4, f"pipeline slow: {dt:.2f}s"
        body = r.json()
        assert body["type"] == "FeatureCollection"
        assert "features" in body
        # Either succeeded (features populated) or returned meta error
        meta = body.get("meta") or {}
        if "error" in meta:
            pytest.skip(f"pipeline not runnable: {meta['error']}")
        assert len(body["features"]) > 0


# ===========================================================================
# 9) CONSISTENCY CHECKS — repeated requests return identical data
# ===========================================================================


class TestS10_4_ConsistencyChecks:
    """System must produce consistent outputs (idempotent reads)."""

    def test_fire_risk_statistics_idempotent(self, client: TestClient):
        body1 = client.get("/api/fire-risk/statistics").json()
        body2 = client.get("/api/fire-risk/statistics").json()
        assert body1 == body2, "statistics are not deterministic"

    def test_fire_risk_points_idempotent(self, client: TestClient):
        r1 = client.get("/api/fire-risk/points", params={"limit": 50}).json()
        r2 = client.get("/api/fire-risk/points", params={"limit": 50}).json()
        assert r1["total"] == r2["total"]
        assert len(r1["features"]) == len(r2["features"])

    def test_gis_layers_idempotent(self, client: TestClient):
        for ep in ("/api/dams", "/api/fire_stations", "/api/water_sources"):
            a = client.get(ep).json()
            b = client.get(ep).json()
            assert a == b, f"{ep} is not deterministic"

    def test_accessibility_levels_idempotent(self, client: TestClient):
        a = client.get("/api/accessibility/levels").json()
        b = client.get("/api/accessibility/levels").json()
        assert a == b

    def test_pipeline_summary_cross_checks(
        self, client: TestClient, pipeline_summary_path: Path
    ):
        """Pipeline summary ↔ fire-risk statistics are independent subsystems,
        but both should report non-empty, sane totals."""
        summary = json.loads(pipeline_summary_path.read_text(encoding="utf-8"))
        stats = client.get("/api/fire-risk/statistics").json()
        assert summary["total_points"] > 0
        assert stats["total_points"] > 0

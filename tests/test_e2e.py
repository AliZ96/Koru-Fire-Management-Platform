import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Proje kökünü PYTHONPATH'e ekle (pytest ModuleNotFoundError için)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Tablo tanımlarının yüklenmesi için modelleri import et
from app.models import user as _user  # noqa: F401


# SQLite test veritabanı
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bağımlılığı override et
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Temiz DB oluştur
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


def test_health_db(client: TestClient):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json().get("db") == "connected"


def test_auth_register_login_me(client: TestClient):
    username = "user_e2e"
    password = "secret123"

    r = client.post("/auth/user/register", json={"username": username, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.post("/auth/user/login", json={"username": username, "password": password})
    assert r.status_code == 200
    token_login = r.json()["access_token"]

    # me endpoint
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token_login}"})
    assert r.status_code == 200
    assert r.json().get("sub") == username


@pytest.mark.skipif(not os.getenv("MAP_KEY"), reason="MAP_KEY missing; FIRMS live call skipped")
def test_fires_endpoint(client: TestClient):
    r = client.get("/api/fires?day_range=1")
    assert r.status_code == 200
    body = r.json()
    assert body.get("type") == "FeatureCollection"


def test_wind_endpoint(client: TestClient):
    r = client.get("/api/wind", params={"lat": 38.5, "lon": 27.1})
    assert r.status_code == 200
    body = r.json()
    assert "speed_ms" in body
    assert "deg" in body


def test_static_geo_endpoints(client: TestClient):
    for path in ("/api/dams", "/api/water_sources", "/api/water_tanks"):
        r = client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert body.get("type") == "FeatureCollection"


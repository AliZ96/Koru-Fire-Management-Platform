import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.fire_monitor import refresh_scenario, register_ws, unregister_ws
from app.services.fire_spread_engine import compute_eta, haversine_km
from app.services.firestore_store import FirestoreStore

router = APIRouter(prefix="/api/fire-spread", tags=["Fire Spread"])


def _store() -> FirestoreStore:
    return FirestoreStore()


class ScenarioCreate(BaseModel):
    name: str
    lat: float
    lon: float


class LocationUpsert(BaseModel):
    lat: float
    lon: float
    address: Optional[str] = None


# ─── Scenarios ────────────────────────────────────────────────────────────────

@router.post("/scenarios")
async def create_scenario(body: ScenarioCreate):
    scenario = _store().create_fire_scenario(
        {
            "name": body.name,
            "origin_lat": body.lat,
            "origin_lon": body.lon,
            "status": "active",
            "elapsed_minutes": 0.0,
        }
    )
    await refresh_scenario(str(scenario["id"]))
    return {"id": scenario["id"], "name": scenario["name"], "status": scenario["status"]}


@router.get("/scenarios")
def list_scenarios():
    rows = _store().list_fire_scenarios(limit=50)
    return [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "origin_lat": r.get("origin_lat"),
            "origin_lon": r.get("origin_lon"),
            "status": r.get("status"),
            "elapsed_minutes": r.get("elapsed_minutes"),
            "created_at": r.get("created_at"),
        }
        for r in rows
    ]


@router.get("/scenarios/{scenario_id}/current")
def get_current_spread(scenario_id: str):
    store = _store()
    scenario = store.get_fire_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    snap = store.get_latest_spread_snapshot(scenario_id)
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot yet")
    return {
        "scenario_id": scenario_id,
        "origin": {"lat": scenario.get("origin_lat"), "lon": scenario.get("origin_lon")},
        "elapsed_minutes": scenario.get("elapsed_minutes", 0.0),
        "spread_polygon": json.loads(snap.get("polygon_geojson", "{}")),
        "weather": {
            "wind_speed_ms": snap.get("wind_speed_ms"),
            "wind_dir_deg": snap.get("wind_dir_deg"),
            "humidity": snap.get("humidity"),
            "temperature_c": snap.get("temperature_c"),
        },
        "step": snap.get("step", 0),
    }


@router.patch("/scenarios/{scenario_id}/stop")
def stop_scenario(scenario_id: str):
    store = _store()
    scenario = store.get_fire_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    store.update_fire_scenario(scenario_id, {"status": "stopped"})
    return {"status": "stopped"}


@router.get("/scenarios/{scenario_id}/eta")
def get_eta_for_point(
    scenario_id: str, lat: float, lon: float
):
    store = _store()
    scenario = store.get_fire_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    snap = store.get_latest_spread_snapshot(scenario_id)
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot yet")
    eta = compute_eta(
        fire_lat=float(scenario.get("origin_lat", 0.0)),
        fire_lon=float(scenario.get("origin_lon", 0.0)),
        user_lat=lat,
        user_lon=lon,
        wind_dir_deg=float(snap.get("wind_dir_deg", 240.0)),
        wind_speed_ms=float(snap.get("wind_speed_ms", 6.0)),
        elapsed_minutes=float(scenario.get("elapsed_minutes", 0.0)),
        humidity=float(snap.get("humidity") or 50.0),
        temperature_c=float(snap.get("temperature_c") or 25.0),
    )
    dist_km = haversine_km(
        float(scenario.get("origin_lat", 0.0)),
        float(scenario.get("origin_lon", 0.0)),
        lat,
        lon,
    )
    return {
        "distance_km": round(dist_km, 3),
        "eta_minutes": round(eta, 1) if eta is not None else None,
        "already_in_zone": eta == 0.0,
    }


# ─── User location & alerts ───────────────────────────────────────────────────

@router.post("/my-location")
def upsert_my_location(
    body: LocationUpsert,
    current_user: dict = Depends(get_current_user),
):
    user_key = str(current_user.get("sub") or current_user.get("id"))
    if not user_key:
        raise HTTPException(status_code=401, detail="Invalid token")
    _store().upsert_user_location(
        user_key=user_key,
        payload={
            "lat": body.lat,
            "lon": body.lon,
            "address": body.address,
            "notifications_enabled": True,
        },
    )
    return {"ok": True}


@router.get("/my-alerts")
def get_my_alerts(
    current_user: dict = Depends(get_current_user),
):
    user_key = str(current_user.get("sub") or current_user.get("id"))
    if not user_key:
        raise HTTPException(status_code=401, detail="Invalid token")
    alerts = _store().list_alerts_for_user(user_key=user_key, limit=20)
    return [
        {
            "id": a.get("id"),
            "scenario_id": a.get("scenario_id"),
            "distance_km": a.get("distance_km"),
            "eta_minutes": a.get("eta_minutes"),
            "severity": a.get("severity"),
            "message": a.get("message"),
            "is_read": a.get("is_read", False),
            "created_at": a.get("created_at"),
        }
        for a in alerts
    ]


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/{scenario_id}")
async def fire_spread_ws(
    scenario_id: str, websocket: WebSocket
):
    await websocket.accept()

    store = _store()
    scenario = store.get_fire_scenario(scenario_id)
    if not scenario:
        await websocket.send_text(json.dumps({"error": "Scenario not found"}))
        await websocket.close()
        return

    snap = store.get_latest_spread_snapshot(scenario_id)
    if snap:
        await websocket.send_text(json.dumps({
            "event": "spread_update",
            "scenario_id": scenario_id,
            "scenario_name": scenario.get("name"),
            "origin": {"lat": scenario.get("origin_lat"), "lon": scenario.get("origin_lon")},
            "elapsed_minutes": scenario.get("elapsed_minutes", 0.0),
            "step": snap.get("step", 0),
            "spread_polygon": json.loads(snap.get("polygon_geojson", "{}")),
            "weather": {
                "wind_speed_ms": snap.get("wind_speed_ms"),
                "wind_dir_deg": snap.get("wind_dir_deg"),
                "humidity": snap.get("humidity"),
                "temperature_c": snap.get("temperature_c"),
            },
            "alerts": [],
        }))

    async def send_fn(msg: str) -> None:
        await websocket.send_text(msg)

    register_ws(scenario_id, send_fn)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=55.0)
                if data == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event": "heartbeat"}))
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(scenario_id, send_fn)

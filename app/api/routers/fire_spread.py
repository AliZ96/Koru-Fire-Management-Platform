import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.fire_spread import FireScenario, SpreadAlert, SpreadSnapshot, UserLocation
from app.services.fire_monitor import refresh_scenario, register_ws, unregister_ws
from app.services.fire_spread_engine import compute_eta, haversine_km

router = APIRouter(prefix="/api/fire-spread", tags=["Fire Spread"])


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
async def create_scenario(body: ScenarioCreate, db: Session = Depends(get_db)):
    scenario = FireScenario(
        name=body.name,
        origin_lat=body.lat,
        origin_lon=body.lon,
        status="active",
        elapsed_minutes=0.0,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    await refresh_scenario(scenario.id)
    return {"id": scenario.id, "name": scenario.name, "status": scenario.status}


@router.get("/scenarios")
def list_scenarios(db: Session = Depends(get_db)):
    rows = db.query(FireScenario).order_by(FireScenario.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "origin_lat": r.origin_lat,
            "origin_lon": r.origin_lon,
            "status": r.status,
            "elapsed_minutes": r.elapsed_minutes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/scenarios/{scenario_id}/current")
def get_current_spread(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.get(FireScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    snap = (
        db.query(SpreadSnapshot)
        .filter_by(scenario_id=scenario_id)
        .order_by(SpreadSnapshot.step.desc())
        .first()
    )
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot yet")
    return {
        "scenario_id": scenario_id,
        "origin": {"lat": scenario.origin_lat, "lon": scenario.origin_lon},
        "elapsed_minutes": scenario.elapsed_minutes,
        "spread_polygon": json.loads(snap.polygon_geojson),
        "weather": {
            "wind_speed_ms": snap.wind_speed_ms,
            "wind_dir_deg": snap.wind_dir_deg,
            "humidity": snap.humidity,
            "temperature_c": snap.temperature_c,
        },
        "step": snap.step,
    }


@router.patch("/scenarios/{scenario_id}/stop")
def stop_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.get(FireScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario.status = "stopped"
    db.commit()
    return {"status": "stopped"}


@router.get("/scenarios/{scenario_id}/eta")
def get_eta_for_point(
    scenario_id: int, lat: float, lon: float, db: Session = Depends(get_db)
):
    scenario = db.get(FireScenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    snap = (
        db.query(SpreadSnapshot)
        .filter_by(scenario_id=scenario_id)
        .order_by(SpreadSnapshot.step.desc())
        .first()
    )
    if not snap:
        raise HTTPException(status_code=404, detail="No snapshot yet")
    eta = compute_eta(
        fire_lat=scenario.origin_lat,
        fire_lon=scenario.origin_lon,
        user_lat=lat,
        user_lon=lon,
        wind_dir_deg=snap.wind_dir_deg,
        wind_speed_ms=snap.wind_speed_ms,
        elapsed_minutes=scenario.elapsed_minutes,
        humidity=snap.humidity or 50.0,
        temperature_c=snap.temperature_c or 25.0,
    )
    dist_km = haversine_km(scenario.origin_lat, scenario.origin_lon, lat, lon)
    return {
        "distance_km": round(dist_km, 3),
        "eta_minutes": round(eta, 1) if eta is not None else None,
        "already_in_zone": eta == 0.0,
    }


# ─── User location & alerts ───────────────────────────────────────────────────

@router.post("/my-location")
def upsert_my_location(
    body: LocationUpsert,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    loc = db.query(UserLocation).filter_by(user_id=user_id).first()
    if loc:
        loc.lat = body.lat
        loc.lon = body.lon
        loc.address = body.address
    else:
        loc = UserLocation(user_id=user_id, lat=body.lat, lon=body.lon, address=body.address)
        db.add(loc)
    db.commit()
    return {"ok": True}


@router.get("/my-alerts")
def get_my_alerts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    alerts = (
        db.query(SpreadAlert)
        .filter_by(user_id=current_user["id"])
        .order_by(SpreadAlert.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": a.id,
            "scenario_id": a.scenario_id,
            "distance_km": a.distance_km,
            "eta_minutes": a.eta_minutes,
            "severity": a.severity,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/{scenario_id}")
async def fire_spread_ws(
    scenario_id: int, websocket: WebSocket, db: Session = Depends(get_db)
):
    await websocket.accept()

    scenario = db.get(FireScenario, scenario_id)
    if not scenario:
        await websocket.send_text(json.dumps({"error": "Scenario not found"}))
        await websocket.close()
        return

    snap = (
        db.query(SpreadSnapshot)
        .filter_by(scenario_id=scenario_id)
        .order_by(SpreadSnapshot.step.desc())
        .first()
    )
    if snap:
        await websocket.send_text(json.dumps({
            "event": "spread_update",
            "scenario_id": scenario_id,
            "scenario_name": scenario.name,
            "origin": {"lat": scenario.origin_lat, "lon": scenario.origin_lon},
            "elapsed_minutes": scenario.elapsed_minutes,
            "step": snap.step,
            "spread_polygon": json.loads(snap.polygon_geojson),
            "weather": {
                "wind_speed_ms": snap.wind_speed_ms,
                "wind_dir_deg": snap.wind_dir_deg,
                "humidity": snap.humidity,
                "temperature_c": snap.temperature_c,
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

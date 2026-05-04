import io
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.firestore_store import FirestoreStore

router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])


class PipelineSaveRequest(BaseModel):
    name: str
    n: int = 20
    k: int = 4
    snapshot: Optional[Dict[str, Any]] = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    n: int
    k: int
    has_snapshot: bool
    snapshot: Optional[Dict[str, Any]] = None
    created_at: str

    model_config = {"from_attributes": True}


def _serialize(p: dict[str, Any], include_snapshot: bool = True) -> dict:
    snap = None
    snapshot_json = p.get("snapshot_json")
    if snapshot_json:
        try:
            snap = json.loads(snapshot_json)
        except Exception:
            snap = None
    return {
        "id": str(p.get("id")),
        "name": p.get("name"),
        "n": int(p.get("n", 0)),
        "k": int(p.get("k", 0)),
        "has_snapshot": snap is not None,
        "snapshot": snap if include_snapshot else None,
        "created_at": str(p.get("created_at") or ""),
    }


@router.get("")
def list_pipelines(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    username = current_user["sub"]
    rows = FirestoreStore().list_pipelines(username=username)
    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
def save_pipeline(
    payload: PipelineSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    username = current_user["sub"]
    snap_json = json.dumps(payload.snapshot) if payload.snapshot else None
    row = FirestoreStore().create_pipeline(
        username=username,
        name=payload.name,
        n=payload.n,
        k=payload.k,
        snapshot_json=snap_json,
    )
    return _serialize(row)


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(
    pipeline_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    username = current_user["sub"]
    deleted = FirestoreStore().delete_pipeline(pipeline_id=pipeline_id, username=username)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline bulunamadi")


@router.get("/{pipeline_id}/pdf")
def download_pipeline_pdf(
    pipeline_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    username = current_user["sub"]
    row = FirestoreStore().get_pipeline(pipeline_id=pipeline_id, username=username)
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline bulunamadi")

    snap: dict[str, Any] = {}
    if row.get("snapshot_json"):
        try:
            snap = json.loads(row.get("snapshot_json") or "{}")
        except Exception:
            snap = {}

    pipeline_points = snap.get("pipeline_points") or []
    stations_by_id = _group_points_by_station(pipeline_points)
    ga_stations = _ga_stations_from_snapshot(snap)
    high_count = sum(1 for p in pipeline_points if str(p.get("risk", "")).upper() == "HIGH")
    critical_count = sum(
        1
        for points in stations_by_id.values()
        if any(str(p.get("risk", "")).upper() in {"HIGH", "KRITIK", "CRITICAL"} for p in points)
    )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe(f"KORU - Scenario Report #{row.get('id')}"), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, _safe(f"Date: {row.get('created_at')}"), ln=1)
    pdf.cell(
        0,
        7,
        _safe(
            f"Total Points: {len(pipeline_points)}  |  "
            f"Clusters: {len(stations_by_id)}  |  "
            f"Critical Clusters: {critical_count}  |  "
            f"HIGH Points: {high_count}"
        ),
        ln=1,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Cluster Details", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    cluster_widths = [20, 25, 22, 18, 20, 25, 40]
    cluster_headers = ["Cluster", "Station ID", "Risk Level", "HIGH", "LOW", "Avg Dist (km)", "Fire Points"]
    for header, width in zip(cluster_headers, cluster_widths):
        pdf.cell(width, 7, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for idx, (station_id, points) in enumerate(stations_by_id.items()):
        high = sum(1 for p in points if str(p.get("risk", "")).upper() == "HIGH")
        low = max(0, len(points) - high)
        avg_dist = _average_distance(points)
        fire_points = ", ".join(str(p.get("id", "")) for p in points)
        row_data = [
            str(idx),
            str(station_id),
            _risk_label(high, low),
            str(high),
            str(low),
            f"{avg_dist:.4f}" if avg_dist is not None else "",
            _safe(fire_points, 35),
        ]
        for value, width in zip(row_data, cluster_widths):
            pdf.cell(width, 6, _safe(str(value)), border=1)
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "GA Optimization - Vehicle Tours", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    tour_widths = [25, 20, 20, 90]
    for header, width in zip(["Station ID", "Vehicle", "Load", "Tour"], tour_widths):
        pdf.cell(width, 7, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for station in ga_stations:
        station_id = station.get("station_id") or station.get("id") or ""
        vehicles = station.get("vehicles") or []
        assigned_points = station.get("assigned_fire_points") or station.get("points") or []
        for vehicle in vehicles:
            fire_nodes = _vehicle_fire_node_ids(vehicle.get("tour") or [], station_id)
            if not fire_nodes and len(vehicles) == 1:
                fire_nodes = [str(p.get("id")) for p in assigned_points if p.get("id") is not None]
            row_data = [
                str(station_id),
                str(vehicle.get("vehicle_index", vehicle.get("vehicle", ""))),
                str(vehicle.get("load", "")),
                _safe(" -> ".join(fire_nodes), 80),
            ]
            for value, width in zip(row_data, tour_widths):
                pdf.cell(width, 6, _safe(str(value)), border=1)
            pdf.ln()

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    filename = f"koru_pipeline_{row.get('id')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _group_points_by_station(points: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for point in points:
        station_id = point.get("fire_station_id") or point.get("station_id") or point.get("assigned_station_id") or "-"
        grouped.setdefault(str(station_id), []).append(point)
    return grouped


def _average_distance(points: list[dict[str, Any]]) -> float | None:
    distances = [p.get("station_distance_km") for p in points if isinstance(p.get("station_distance_km"), (int, float))]
    if not distances:
        return None
    return sum(distances) / len(distances)


def _risk_label(high: int, low: int) -> str:
    if high >= max(1, low):
        return "KRITIK" if high >= 4 else "YUKSEK"
    return "NORMAL"


def _ga_stations_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    direct = snapshot.get("ga_routes")
    if isinstance(direct, list):
        return direct
    optimization = snapshot.get("optimization") or {}
    ga = optimization.get("GA") or {}
    stations = ga.get("stations")
    return stations if isinstance(stations, list) else []


def _vehicle_fire_node_ids(tour: list[Any], station_id: Any) -> list[str]:
    station_key = str(station_id)
    fire_nodes: list[str] = []
    for node in tour:
        if isinstance(node, dict):
            node_id = node.get("node_id") or node.get("id")
        else:
            node_id = node
        if node_id is None or str(node_id) == station_key:
            continue
        fire_nodes.append(str(node_id))
    return fire_nodes


def _safe(text: str, maxlen: int = 200) -> str:
    replacements = {
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "İ": "I",
        "ı": "i",
        "Ş": "S",
        "ş": "s",
        "Ğ": "G",
        "ğ": "g",
        "Ü": "U",
        "ü": "u",
        "Ö": "O",
        "ö": "o",
        "Ç": "C",
        "ç": "c",
    }
    for ch, rep in replacements.items():
        text = text.replace(ch, rep)
    return text.encode("latin-1", errors="ignore").decode("latin-1")[:maxlen]

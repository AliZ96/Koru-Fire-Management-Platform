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
    pop: Optional[int] = None
    iter: Optional[int] = None
    temp: Optional[int] = None
    snapshot: Optional[Dict[str, Any]] = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    n: int
    k: int
    pop: Optional[int] = None
    iter: Optional[int] = None
    temp: Optional[int] = None
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
        "pop": p.get("pop"),
        "iter": p.get("iter"),
        "temp": p.get("temp"),
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
        pop=payload.pop,
        iter=payload.iter,
        temp=payload.temp,
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
    high_count = sum(
        1
        for p in pipeline_points
        if str(p.get("risk") or p.get("risk_class") or "").upper() == "HIGH"
    )
    cluster_groups: dict[str, list[dict[str, Any]]] = {}
    for point in pipeline_points:
        station_id = str(point.get("fire_station_id") or "-")
        cluster_groups.setdefault(station_id, []).append(point)

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
            f"Total Points: {len(pipeline_points) or row.get('n', '-')}  |  "
            f"Clusters: {row.get('k', '-')}  |  Critical Clusters: 0  |  HIGH Points: {high_count}"
        ),
        ln=1,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Cluster Details", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    cluster_col_w = [20, 25, 22, 18, 20, 25, 40]
    for i, header in enumerate(["Cluster", "Station ID", "Risk Level", "HIGH", "LOW", "Avg Dist (km)", "Fire Points"]):
        pdf.cell(cluster_col_w[i], 7, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for cluster_idx, (station_id, points) in enumerate(cluster_groups.items()):
        high = sum(
            1
            for p in points
            if str(p.get("risk") or p.get("risk_class") or "").upper() == "HIGH"
        )
        low = len(points) - high
        distances = [
            float(p.get("station_distance_km"))
            for p in points
            if isinstance(p.get("station_distance_km"), (int, float))
        ]
        avg_dist = sum(distances) / len(distances) if distances else 0
        risk_level = "KRITIK" if high and not low else ("YUKSEK" if high >= low and high > 0 else "NORMAL")
        fire_points = ", ".join(str(p.get("id", "")) for p in points if p.get("id") is not None)
        row_data = [
            str(cluster_idx),
            str(station_id),
            risk_level,
            str(high),
            str(low),
            f"{avg_dist:.4f}",
            fire_points[:35] + ("..." if len(fire_points) > 35 else ""),
        ]
        for i, value in enumerate(row_data):
            pdf.cell(cluster_col_w[i], 6, _safe(str(value), 80), border=1)
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "GA Optimization - Vehicle Tours", ln=1)
    pdf.set_font("Helvetica", "B", 9)
    tour_col_w = [25, 20, 20, 90]
    for i, header in enumerate(["Station ID", "Vehicle", "Load", "Tour"]):
        pdf.cell(tour_col_w[i], 7, header, border=1)
    pdf.ln()

    ga_stations = snap.get("ga_routes")
    if not isinstance(ga_stations, list):
        ga_stations = ((snap.get("optimization") or {}).get("GA") or {}).get("stations") or []
    pdf.set_font("Helvetica", "", 9)
    for station in ga_stations:
        station_id = station.get("station_id", "")
        assigned = station.get("assigned_fire_points") or []
        for vehicle in station.get("vehicles", []):
            fire_nodes = _vehicle_fire_node_ids(vehicle.get("tour") or [], station_id)
            if not fire_nodes and len(station.get("vehicles", [])) == 1:
                fire_nodes = [str(node) for node in assigned]
            tour_text = " -> ".join(fire_nodes)
            row_data = [
                str(station_id),
                str(vehicle.get("vehicle_index", "")),
                str(vehicle.get("load", "")),
                tour_text[:80] + ("..." if len(tour_text) > 80 else ""),
            ]
            for i, value in enumerate(row_data):
                pdf.cell(tour_col_w[i], 6, _safe(str(value), 120), border=1)
            pdf.ln()

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    filename = f"koru_pipeline_{row.get('id')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _vehicle_fire_node_ids(tour: list[Any], station_id: Any) -> list[str]:
    station_key = str(station_id)
    node_ids: list[str] = []
    for node in tour:
        if isinstance(node, dict):
            node_id = node.get("node_id") or node.get("id")
        else:
            node_id = node
        if node_id is None:
            continue
        node_key = str(node_id)
        if node_key == station_key:
            continue
        node_ids.append(node_key)
    return node_ids


def _safe(text: str, maxlen: int = 200) -> str:
    replacements = {
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "ı": "i",
        "İ": "I",
        "ğ": "g",
        "Ğ": "G",
        "ş": "s",
        "Ş": "S",
        "ç": "c",
        "Ç": "C",
        "ö": "o",
        "Ö": "O",
        "ü": "u",
        "Ü": "U",
    }
    for ch, rep in replacements.items():
        text = text.replace(ch, rep)
    return text.encode("latin-1", errors="ignore").decode("latin-1")[:maxlen]

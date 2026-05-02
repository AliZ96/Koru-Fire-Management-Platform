from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fpdf import FPDF

from app.core.security import get_current_user
from app.scenario import service
from app.scenario.schemaforscenario import ScenarioCreate
from pydantic import BaseModel

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


class ScenarioPersistRequest(BaseModel):
    sa_result: list[dict] | None = None
    ga_result: list[dict] | None = None
    pipeline_snapshot: dict | None = None


@router.post("/create")
def create_scenario(payload: ScenarioCreate, current_user: dict = Depends(get_current_user)):
    try:
        scenario = service.build_and_save(
            payload.name,
            owner_username=str(current_user.get("sub") or ""),
            owner_role=str(current_user.get("role") or "user"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "scenario_id": scenario["scenario_id"],
        "created_at": scenario["created_at"],
        "summary": scenario["summary"],
    }


@router.get("/mine")
def list_my_scenarios(current_user: dict = Depends(get_current_user)):
    username = str(current_user.get("sub") or "")
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return service.list_user_scenarios(username=username, limit=100)


@router.get("/get/{scenario_id}")
def get_scenario(scenario_id: str):
    scenario = service.load_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return scenario


@router.patch("/persist/{scenario_id}")
def persist_scenario(
    scenario_id: int,
    payload: ScenarioPersistRequest,
    current_user: dict = Depends(get_current_user),
):
    existing = service.load_scenario(scenario_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")

    username = str(current_user.get("sub") or "")
    role = str(current_user.get("role") or "user")
    owner = str(existing.get("owner_username") or "")
    if role != "admin" and owner and owner != username:
        raise HTTPException(status_code=403, detail="Bu senaryoyu güncelleme yetkiniz yok")

    patch: dict = {}
    if payload.sa_result is not None:
        patch["sa_result"] = payload.sa_result
    if payload.ga_result is not None:
        patch["ga_result"] = payload.ga_result
    if payload.pipeline_snapshot is not None:
        patch["pipeline_snapshot"] = payload.pipeline_snapshot
    if not patch:
        raise HTTPException(status_code=400, detail="Kaydedilecek alan gönderilmedi")

    updated = service.patch_scenario(scenario_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return {"ok": True, "scenario_id": scenario_id}


@router.get("/export/json/{scenario_id}")
def export_json(scenario_id: str):
    scenario = service.load_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    json_path = Path(tmp.name)
    tmp.close()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)

    return FileResponse(
        path=str(json_path),
        media_type="application/json",
        filename=f"scenario_{scenario_id}.json",
    )


@router.get("/export/pdf/{scenario_id}")
def export_pdf(scenario_id: str):
    scenario = service.load_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)

    # Başlık
    pdf.cell(0, 10, f"KORU - Scenario Report #{scenario_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Date: {scenario['created_at']}", new_x="LMARGIN", new_y="NEXT")

    s = scenario.get("summary", {})
    pdf.cell(0, 7, f"Total Points: {s.get('total_points', '-')}  |  "
                   f"Clusters: {s.get('total_clusters', '-')}  |  "
                   f"Critical Clusters: {s.get('critical_clusters', '-')}  |  "
                   f"HIGH Points: {s.get('high_count', '-')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Küme tablosu
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Cluster Details", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)

    col_w = [20, 25, 22, 18, 20, 25, 40]
    headers = ["Cluster", "Station ID", "Risk Level", "HIGH", "LOW", "Avg Dist (km)", "Fire Points"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for c in scenario.get("clusters", []):
        fire_points = ", ".join(str(p["id"]) for p in c.get("points", []))
        row = [
            str(c.get("cluster_id", "")),
            str(c.get("station_id", "")),
            str(c.get("risk_level", "")),
            str(c.get("high_count", "")),
            str(c.get("low_count", "")),
            str(c.get("station_distance_km", "")),
            fire_points[:35] + ("..." if len(fire_points) > 35 else ""),
        ]
        for i, val in enumerate(row):
            pdf.cell(col_w[i], 6, val, border=1)
        pdf.ln()

    pdf.ln(6)

    # GA tur tablosu
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "GA Optimization - Vehicle Tours", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)

    tour_col_w = [25, 20, 20, 90]
    tour_headers = ["Station ID", "Vehicle", "Load", "Tour"]
    for i, h in enumerate(tour_headers):
        pdf.cell(tour_col_w[i], 7, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for station in scenario.get("ga_result", []):
        for v in station.get("vehicles", []):
            tour_str = " -> ".join(str(t) for t in v.get("tour", []))
            row = [
                str(station.get("station_id", "")),
                str(v.get("vehicle_index", "")),
                str(v.get("load", "")),
                tour_str[:80] + ("..." if len(tour_str) > 80 else ""),
            ]
            for i, val in enumerate(row):
                pdf.cell(tour_col_w[i], 6, val, border=1)
            pdf.ln()

    tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = Path(tmp_pdf.name)
    tmp_pdf.close()
    pdf.output(str(pdf_path))

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"scenario_{scenario_id}.pdf",
    )


@router.delete("/{scenario_id}")
def delete_scenario(scenario_id: int, current_user: dict = Depends(get_current_user)):
    username = str(current_user.get("sub") or "")
    role = str(current_user.get("role") or "user")
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        deleted = service.delete_scenario(scenario_id, username=username, role=role)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return {"ok": True, "scenario_id": scenario_id}

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fpdf import FPDF

from app.scenario import service
from app.scenario.schemaforscenario import ScenarioCreate

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.post("/create")
def create_scenario(payload: ScenarioCreate):
    try:
        scenario = service.build_and_save(payload.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "scenario_id": scenario["scenario_id"],
        "created_at": scenario["created_at"],
        "summary": scenario["summary"],
    }


@router.get("/get/{scenario_id}")
def get_scenario(scenario_id: int):
    scenario = service.load_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return scenario


@router.get("/export/json/{scenario_id}")
def export_json(scenario_id: int):
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
def export_pdf(scenario_id: int):
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

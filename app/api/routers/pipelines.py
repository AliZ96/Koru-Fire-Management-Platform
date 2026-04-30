import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.models.pipeline import UserPipeline

router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])


# ── Schemas ───────────────────────────────────────────────────
class PipelineSaveRequest(BaseModel):
    name: str
    n: int = 20
    k: int = 4
    snapshot: Optional[Dict[str, Any]] = None


class PipelineResponse(BaseModel):
    id: int
    name: str
    n: int
    k: int
    has_snapshot: bool
    snapshot: Optional[Dict[str, Any]] = None
    created_at: str

    model_config = {"from_attributes": True}


# ── Helper ────────────────────────────────────────────────────
def _serialize(p: UserPipeline, include_snapshot: bool = True) -> dict:
    snap = None
    if p.snapshot_json:
        try:
            snap = json.loads(p.snapshot_json)
        except Exception:
            snap = None
    return {
        "id": p.id,
        "name": p.name,
        "n": p.n,
        "k": p.k,
        "has_snapshot": snap is not None,
        "snapshot": snap if include_snapshot else None,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


# ── Endpoints ─────────────────────────────────────────────────
@router.get("")
def list_pipelines(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    username = current_user["sub"]
    rows = (
        db.query(UserPipeline)
        .filter(UserPipeline.username == username)
        .order_by(UserPipeline.created_at.desc())
        .all()
    )
    return [_serialize(r) for r in rows]


@router.post("", status_code=201)
def save_pipeline(
    payload: PipelineSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    username = current_user["sub"]
    snap_json = json.dumps(payload.snapshot) if payload.snapshot else None
    row = UserPipeline(
        username=username,
        name=payload.name,
        n=payload.n,
        k=payload.k,
        snapshot_json=snap_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    username = current_user["sub"]
    row = db.query(UserPipeline).filter(
        UserPipeline.id == pipeline_id,
        UserPipeline.username == username,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline bulunamadı")
    db.delete(row)
    db.commit()


@router.get("/{pipeline_id}/pdf")
def download_pipeline_pdf(
    pipeline_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    username = current_user["sub"]
    row = db.query(UserPipeline).filter(
        UserPipeline.id == pipeline_id,
        UserPipeline.username == username,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline bulunamad\u0131")

    snap = {}
    if row.snapshot_json:
        try:
            snap = json.loads(row.snapshot_json)
        except Exception:
            snap = {}

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe(f"KORU - Pipeline Raporu #{row.id}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, _safe(f"Ad: {row.name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Kullanici: {row.username}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Tarih: {row.created_at}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, _safe(f"Nokta sayisi (n): {row.n}  |  Kume sayisi (k): {row.k}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── İtfaiye İstasyonları ──
    stations = snap.get("stations", [])
    if stations:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Atanan Itfaiye Istasyonlari", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        col_w = [12, 75, 30, 30, 18]
        for h, w in zip(["#", "Ad", "Enlem", "Boylam", "ID"], col_w):
            pdf.cell(w, 7, h, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for i, st in enumerate(stations, 1):
            lat = st.get("lat") or (st.get("geometry", {}).get("coordinates", [None, None])[1])
            lon = st.get("lon") or (st.get("geometry", {}).get("coordinates", [None, None])[0])
            name = st.get("name") or st.get("properties", {}).get("name") or str(st.get("id", "-"))
            row_data = [
                str(i),
                _safe(str(name), 60),
                f"{lat:.4f}" if lat else "-",
                f"{lon:.4f}" if lon else "-",
                str(st.get("id", "-")),
            ]
            for val, w in zip(row_data, col_w):
                pdf.cell(w, 6, str(val), border=1)
            pdf.ln()

    # ── Pipeline Noktaları ──
    pipeline_points = snap.get("pipeline_points", [])
    if pipeline_points:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Yangin/Risk Noktalari ({len(pipeline_points)} nokta)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        col_w2 = [12, 18, 25, 30, 30, 30, 20]
        for h, w in zip(["#", "ID", "Risk", "Enlem", "Boylam", "Mesafe (km)", "Talep"], col_w2):
            pdf.cell(w, 7, h, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        high_count = sum(1 for p in pipeline_points if str(p.get("risk", "")).upper() == "HIGH")
        for i, pt in enumerate(pipeline_points, 1):
            row_data2 = [
                str(i),
                str(pt.get("id", "-")),
                str(pt.get("risk", "-")),
                f"{pt['lat']:.4f}" if pt.get("lat") else "-",
                f"{pt['lon']:.4f}" if pt.get("lon") else "-",
                f"{pt.get('station_distance_km', '-'):.3f}" if isinstance(pt.get("station_distance_km"), (int, float)) else "-",
                str(pt.get("demand", "-")),
            ]
            for val, w in zip(row_data2, col_w2):
                pdf.cell(w, 6, str(val), border=1)
            pdf.ln()

        # Özet
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, _safe(f"Ozet: Toplam {len(pipeline_points)} nokta  |  HIGH risk: {high_count}  |  LOW risk: {len(pipeline_points) - high_count}"), new_x="LMARGIN", new_y="NEXT")

    pdf_bytes = pdf.output()
    filename = f"koru_pipeline_{row.id}.pdf"
    return StreamingResponse(
        io.BytesIO(bytes(pdf_bytes)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _safe(text: str, maxlen: int = 200) -> str:
    """Latin-1 dışı karakterleri ASCII eşdeğerleriyle değiştirir."""
    replacements = {"–": "-", "—": "-", "\u2019": "'", "\u2018": "'",
                    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00e9": "e"}
    for ch, rep in replacements.items():
        text = text.replace(ch, rep)
    # Geri kalan latin-1 dışı karakterleri sil
    return text.encode("latin-1", errors="ignore").decode("latin-1")[:maxlen]

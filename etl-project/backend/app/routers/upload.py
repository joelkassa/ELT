import json
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.connection import get_db
from app.services.staging_service import ingest_files
from app.services.commit_service import apply_review_decisions
from app.services.summary_service import compute_summary
from app.services.export_service import export_to_xlsx_bytes, export_to_csv_bytes, export_to_pdf_bytes
from app.services.table_config import ALL_TABLE_NAMES
from app.services.quality_report_service import compute_table_quality, compute_all_tables_quality
from app.database.db_helpers import get_pending_staging_rows, get_all_grants, count_pending_in_session
from app.models.schemas import ReviewRequest

router = APIRouter(prefix="/api", tags=["etl"])


@router.get("/tables")
def list_tables():
    return {"tables": ALL_TABLE_NAMES}


@router.get("/grants")
def list_grants(db: Session = Depends(get_db)):
    return {"grants": get_all_grants(db)}


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    manifest: str = Form(...),
    db: Session = Depends(get_db),
):
    manifest_entries = json.loads(manifest)
    if len(manifest_entries) != len(files):
        return {"error": f"manifest has {len(manifest_entries)} entries but {len(files)} files were sent"}

    files_with_meta = []
    for f, meta in zip(files, manifest_entries):
        content = await f.read()
        files_with_meta.append((f.filename, content, meta["grant_name"], meta.get("year")))

    session_id, preview = ingest_files(db, files_with_meta)
    return {"session_id": session_id, "preview": preview}


@router.get("/staging/pending")
def get_pending(session_id: str = None, db: Session = Depends(get_db)):
    rows = get_pending_staging_rows(db, session_id)
    return {"rows": rows}


@router.post("/review")
def review(payload: ReviewRequest, db: Session = Depends(get_db)):
    decisions = [d.model_dump() for d in payload.decisions]
    results = apply_review_decisions(db, decisions)
    return {"results": results}


@router.get("/session/{session_id}/pending-count")
def pending_count(session_id: str, db: Session = Depends(get_db)):
    return {"session_id": session_id, "pending_count": count_pending_in_session(db, session_id)}


@router.get("/summary/{session_id}")
def get_summary(session_id: str, mode: str = Query("per_grant", pattern="^(per_grant|combined)$"), db: Session = Depends(get_db)):
    return {"session_id": session_id, "mode": mode, "summary": compute_summary(db, session_id, mode)}


@router.get("/summary/{session_id}/export")
def export_summary(session_id: str, format: str = Query(..., pattern="^(xlsx|csv|pdf)$"),
                    mode: str = Query("per_grant", pattern="^(per_grant|combined)$"), db: Session = Depends(get_db)):
    summary_rows = compute_summary(db, session_id, mode)
    filename = f"etl_summary_{session_id[:8]}_{mode}.{format}"
    if format == "xlsx":
        content = export_to_xlsx_bytes(summary_rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "csv":
        content = export_to_csv_bytes(summary_rows)
        media_type = "text/csv"
    else:
        content = export_to_pdf_bytes(summary_rows, title=f"ETL Upload Summary ({mode})")
        media_type = "application/pdf"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/final/{table_name}/count")
def final_table_count(table_name: str, db: Session = Depends(get_db)):
    if table_name not in ALL_TABLE_NAMES:
        return {"error": "unknown table"}
    result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
    return {"table": table_name, "row_count": result}


@router.get("/quality/{table_name}")
def table_quality(table_name: str, db: Session = Depends(get_db)):
    if table_name not in ALL_TABLE_NAMES:
        return {"error": "unknown table"}
    return compute_table_quality(db, table_name)


@router.get("/quality")
def all_quality(db: Session = Depends(get_db)):
    return {"tables": compute_all_tables_quality(db)}
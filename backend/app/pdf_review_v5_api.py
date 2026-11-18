"""Authenticated, ephemeral PDF triage. No database writes or financial approvals."""
import hashlib
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot, ReviewCandidate
from .review_api import admin_auth
from .project_intelligence_v4 import extract_pdf
from .pdf_evidence_v7 import enrich_report
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/admin", tags=["pdf-review-v5"], dependencies=[Depends(admin_auth)])
MAX_PDF_BYTES = 15 * 1024 * 1024

def _tokens(value):
    import re
    return set(re.findall(r"[a-z0-9]+", (value or "").lower())) - {"mse", "cdp", "ip", "project", "industrial", "park", "the", "at"}

def suggest_matches(project, candidates):
    """Advisory only; do not equate shared district or generic words with identity."""
    name_tokens = _tokens(project.get("name"))
    matches = []
    if not name_tokens:
        return matches
    for candidate in candidates:
        title_tokens = _tokens(candidate.title)
        overlap = name_tokens & title_tokens
        if overlap and len(overlap) >= min(len(name_tokens), 2):
            matches.append({"candidate_id": candidate.id, "title": candidate.title,
                            "review_status": candidate.review_status, "shared_tokens": sorted(overlap),
                            "match_status": "possible_only"})
    return matches

@router.post("/snapshots/{snapshot_id}/pdf-table-preview")
async def pdf_table_preview(snapshot_id: int, request: Request, db: Session = Depends(get_db)):
    snap = db.get(IngestionSnapshot, snapshot_id)
    if snap is None:
        raise HTTPException(404, "Snapshot not found")
    if not (snap.url.lower().split("?", 1)[0].endswith(".pdf")):
        raise HTTPException(422, "Selected snapshot is not a PDF source")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/pdf":
        raise HTTPException(415, "Upload original PDF with Content-Type: application/pdf")
    # Bound the read even if the client lies about Content-Length.
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(413, "PDF exceeds 15 MiB")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Invalid PDF signature")
    digest = hashlib.sha256(content).hexdigest()
    filename = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            filename = tmp.name
            tmp.write(content)
        report = extract_pdf(filename)
        enrich_report(report, filename)
    except Exception as exc:
        raise HTTPException(422, "Unable to parse PDF: " + str(exc)[:160]) from exc
    finally:
        if filename and os.path.exists(filename):
            os.unlink(filename)
    candidates = db.scalars(select(ReviewCandidate).where(ReviewCandidate.snapshot_id == snapshot_id)).all()
    for project in report["projects"]:
        project["possible_candidate_matches"] = suggest_matches(project, candidates)
    return {"snapshot_id": snapshot_id, "snapshot_url": snap.url,
            "uploaded_pdf_sha256": digest, "snapshot_content_hash": snap.content_hash,
            "binary_matches_snapshot": None,
            "binary_match_notice": "Snapshot hash describes ingested content, not necessarily PDF bytes. Confirm the uploaded PDF matches the selected source URL.",
            "report": report,
            "notice": "EPHEMERAL READ-ONLY PREVIEW. No proposals, approvals, candidate edits, DB writes, or publication. Names and amounts require visual verification."}

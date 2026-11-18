"""Admin-only PDF archival. Registration never approves evidence or publishes candidates."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot
from .review_api import admin_auth
from .source_archive import ArchivedSourceDocument, MAX_PDF_BYTES, archive_pdf, verify_pdf

router = APIRouter(prefix='/api/v1/admin', tags=['source-archive'], dependencies=[Depends(admin_auth)])


def describe(row):
    return dict(id=row.id, snapshot_id=row.snapshot_id, sha256=row.sha256,
                byte_size=row.byte_size, archived_at=row.archived_at.isoformat() if row.archived_at else None,
                integrity='verified' if verify_pdf(row.sha256, row.byte_size) else 'missing_or_tampered')


@router.post('/snapshots/{snapshot_id}/archive-pdf', status_code=201)
async def upload_archive(snapshot_id: int, request: Request, db: Session = Depends(get_db)):
    snapshot = db.get(IngestionSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(404, 'Snapshot not found')
    if not snapshot.url.lower().split('?', 1)[0].endswith('.pdf'):
        raise HTTPException(422, 'Snapshot is not a PDF source')
    if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/pdf':
        raise HTTPException(415, 'Expected application/pdf')
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(413, 'PDF exceeds 15 MiB')
    try:
        digest, byte_size = archive_pdf(bytes(content))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(409, 'Unable to safely archive document: ' + str(exc)[:120]) from exc
    row = db.scalar(select(ArchivedSourceDocument).where(
        ArchivedSourceDocument.snapshot_id == snapshot_id, ArchivedSourceDocument.sha256 == digest))
    if row is None:
        row = ArchivedSourceDocument(snapshot_id=snapshot_id, sha256=digest, byte_size=byte_size)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            row = db.scalar(select(ArchivedSourceDocument).where(
                ArchivedSourceDocument.snapshot_id == snapshot_id, ArchivedSourceDocument.sha256 == digest))
            if row is None:
                raise
    db.refresh(row)
    return describe(row)


@router.get('/snapshots/{snapshot_id}/archived-pdfs')
def list_archives(snapshot_id: int, db: Session = Depends(get_db)):
    if not db.get(IngestionSnapshot, snapshot_id):
        raise HTTPException(404, 'Snapshot not found')
    rows = db.scalars(select(ArchivedSourceDocument).where(
        ArchivedSourceDocument.snapshot_id == snapshot_id).order_by(ArchivedSourceDocument.id.desc())).all()
    return [describe(row) for row in rows]

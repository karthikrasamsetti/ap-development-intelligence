"""Public source-observation feed. Snapshots are NOT verified developments."""
from datetime import timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot

router = APIRouter(prefix='/api/v1/public', tags=['public-source-updates'])

@router.get('/source-updates')
def source_updates(limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db)):
    # Latest observations first; no draft candidate content or admin data exposed.
    rows = db.scalars(select(IngestionSnapshot).order_by(IngestionSnapshot.fetched_at.desc(), IngestionSnapshot.id.desc()).limit(limit)).all()
    return {'data_kind': 'source_observations', 'notice': 'These are source collection records, not verified news, investment commitments, or completed projects. Fetched time is not publication time.', 'count': len(rows), 'items': [
        {'snapshot_id': x.id, 'title': x.title, 'source_name': x.source_name,
         'source_url': x.url if x.url.startswith(('https://','http://')) else None,
         'fetched_at': x.fetched_at.replace(tzinfo=timezone.utc).isoformat() if x.fetched_at and x.fetched_at.tzinfo is None else (x.fetched_at.isoformat() if x.fetched_at else None),
         'verification': 'unverified_source_observation'} for x in rows]}

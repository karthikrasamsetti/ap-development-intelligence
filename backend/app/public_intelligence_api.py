"""Two explicitly separated public feeds. Draft candidates never become verified records."""
from datetime import timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Development, ReviewCandidate, IngestionSnapshot

router = APIRouter(prefix='/api/v1/public', tags=['public-intelligence'])


def utc_iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def safe_link(url):
    return url if isinstance(url, str) and url.lower().startswith(('https://', 'http://')) else None


def verified_item(row):
    source = row.source
    return {
        'id': f'development-{row.id}', 'title': row.title,
        'summary': row.summary, 'category': row.category, 'district': row.district,
        'sector': row.sector, 'stage': row.status,
        'investment_inr_crore': float(row.investment_inr_crore) if row.investment_inr_crore is not None else None,
        'expected_jobs': row.expected_jobs, 'jobs_created': row.jobs_created,
        'source_name': source.title if source else None,
        'source_url': safe_link(source.url) if source else None,
        'source_published_on': source.published_on.isoformat() if source and source.published_on else None,
        'record_created_at': utc_iso(row.created_at), 'verification': 'verified',
    }


def unverified_item(row, snap):
    return {
        'id': f'candidate-{row.id}', 'title': row.title,
        'summary': row.summary, 'category': row.category, 'district': row.district,
        'sector': row.sector, 'stage': row.status,
        # Unreviewed financial claims must not appear as established figures.
        'investment_inr_crore': None, 'expected_jobs': None, 'jobs_created': None,
        'source_name': snap.source_name, 'source_url': safe_link(snap.url),
        'source_published_on': None, 'source_collected_at': utc_iso(snap.fetched_at),
        'record_created_at': utc_iso(row.created_at), 'verification': 'unverified_ai_extraction',
    }


@router.get('/intelligence')
def intelligence(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    verified = db.scalars(
        select(Development).where(Development.is_demo.is_(False), Development.verification_status == 'verified')
        .order_by(Development.created_at.desc(), Development.id.desc()).limit(limit)
    ).all()
    # Show only still-draft, unpublished candidates. These are public previews, not verified announcements.
    candidates = db.scalars(
        select(ReviewCandidate).where(ReviewCandidate.review_status == 'draft', ReviewCandidate.published_development_id.is_(None))
        .order_by(ReviewCandidate.created_at.desc(), ReviewCandidate.id.desc()).limit(limit)
    ).all()
    snapshot_ids = {r.snapshot_id for r in candidates}
    snapshots = {s.id: s for s in db.scalars(select(IngestionSnapshot).where(IngestionSnapshot.id.in_(snapshot_ids))).all()} if snapshot_ids else {}
    return {
        'verified': {'count': len(verified), 'items': [verified_item(r) for r in verified],
                     'notice': 'Published, non-demo records marked verified. Stage and impact claims still depend on their source evidence.'},
        'unverified': {'count': len(candidates), 'items': [unverified_item(r, snapshots[r.snapshot_id]) for r in candidates if r.snapshot_id in snapshots],
                       'notice': 'Unreviewed AI-extracted draft claims, NOT confirmed announcements. Source collection time is not news publication time. Financial figures are withheld pending review.'},
        'limit_per_feed': limit,
    }

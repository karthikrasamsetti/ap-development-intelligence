"""Admin-only, manual evidence-based claim review. No AI-generated claims or auto publishing."""
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Development, IngestionSnapshot, ReviewCandidate, Source, CandidateEvidence
from .review_checks import duplicate_suggestions, field_warnings
from .cross_source import compare_evidence
from .project_duplicates import cross_snapshot_suggestions

router = APIRouter(prefix='/api/v1/admin', tags=['admin-review'])

def admin_auth(x_admin_token: str | None = Header(default=None)):
    expected = os.getenv('APDI_ADMIN_TOKEN', '')
    if not expected or not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(403, 'Admin token required or invalid. Configure APDI_ADMIN_TOKEN on API container.')

class CandidateEdit(BaseModel):
    title: str = Field(min_length=8, max_length=300)
    summary: str = Field(min_length=20, max_length=5000)
    category: Literal['investment','infrastructure','scheme','policy','technology','other']
    district: str | None = Field(default=None, max_length=100)
    sector: str | None = Field(default=None, max_length=100)
    status: Literal['unknown','announced','mou_signed','approved','grounded','operational','delayed','cancelled']
    investment_inr_crore: float | None = Field(default=None, ge=0)
    expected_jobs: int | None = Field(default=None, ge=0)
    jobs_created: int | None = Field(default=None, ge=0)
    evidence_quote: str = Field(min_length=15, max_length=1500)

class Decision(BaseModel):
    confirm_evidence_checked: bool = False

@router.get('/candidates', dependencies=[Depends(admin_auth)])
def candidates(db: Session = Depends(get_db)):
    rows = db.scalars(select(ReviewCandidate).order_by(ReviewCandidate.id.desc()).limit(100)).all()
    return [dict(id=x.id,snapshot_id=x.snapshot_id,review_status=x.review_status,title=x.title,summary=x.summary,
                 category=x.category,district=x.district,sector=x.sector,status=x.status,
                 investment_inr_crore=float(x.investment_inr_crore) if x.investment_inr_crore is not None else None,
                 expected_jobs=x.expected_jobs,jobs_created=x.jobs_created,evidence_quote=x.evidence_quote,
                 source_url=x.snapshot.url,source_title=x.snapshot.title,source_excerpt=x.snapshot.excerpt,
                 published_development_id=x.published_development_id,extraction_method=x.extraction_method,field_evidence=x.field_evidence,extraction_warning=x.extraction_warning) for x in rows]

@router.get('/candidates/{candidate_id}/checks', dependencies=[Depends(admin_auth)])
def candidate_checks(candidate_id: int, db: Session = Depends(get_db)):
    row = db.get(ReviewCandidate, candidate_id)
    if not row:
        raise HTTPException(404, 'Candidate not found')
    same_snapshot = db.scalars(
        select(ReviewCandidate).where(ReviewCandidate.snapshot_id == row.snapshot_id)
    ).all()
    # Advisory search across all stored snapshots. No record is merged or modified.
    other_snapshots = db.scalars(
        select(ReviewCandidate).where(ReviewCandidate.snapshot_id != row.snapshot_id)
    ).all()
    return {
        'candidate_id': candidate_id,
        'warnings': field_warnings(row, row.snapshot.body_text),
        'possible_duplicates': duplicate_suggestions(row, same_snapshot),
        'possible_cross_snapshot_duplicates': cross_snapshot_suggestions(row, other_snapshots),
        'notice': 'Similarity is advisory. Review both records; no automatic merge or deletion.',
    }

@router.post('/snapshots/{snapshot_id}/draft', dependencies=[Depends(admin_auth)])
def draft_from_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snap = db.get(IngestionSnapshot, snapshot_id)
    if not snap: raise HTTPException(404, 'Snapshot not found')
    prior = db.scalar(select(ReviewCandidate).where(ReviewCandidate.snapshot_id == snapshot_id, ReviewCandidate.extraction_fingerprint.is_(None)))
    if prior: return {'id': prior.id, 'result': 'existing_draft'}
    # Only source title and excerpt; NEVER infer investments/jobs/status from a whole portal page.
    row = ReviewCandidate(snapshot_id=snap.id,title=snap.title[:300],summary=snap.excerpt[:1500],
        category='other',district=None,sector=None,status='unknown',evidence_quote='',review_status='draft')
    db.add(row); db.flush()
    from .cross_source_api import record_audit
    record_audit(db,row.id,'draft_created',None,after={'snapshot_id':snap.id})
    db.commit(); db.refresh(row)
    return {'id':row.id,'result':'draft_created','notice':'Placeholder fields require manual evidence review; do not approve a portal homepage as a project.'}

@router.put('/candidates/{candidate_id}', dependencies=[Depends(admin_auth)])
def update_candidate(candidate_id: int, payload: CandidateEdit, db: Session = Depends(get_db), x_admin_token: str | None = Header(default=None)):
    row=db.get(ReviewCandidate,candidate_id)
    if not row: raise HTTPException(404,'Candidate not found')
    if row.review_status != 'draft': raise HTTPException(409,'Only draft candidates can be edited')
    from .cross_source_api import record_audit
    before={k:getattr(row,k) for k in payload.model_dump()}
    for key,value in payload.model_dump().items(): setattr(row,key,value)
    record_audit(db,row.id,'draft_updated',x_admin_token,before=before,after=payload.model_dump())
    db.commit()
    return {'id':row.id,'result':'saved'}

@router.post('/candidates/{candidate_id}/reject', dependencies=[Depends(admin_auth)])
def reject(candidate_id: int, db: Session = Depends(get_db), x_admin_token: str | None = Header(default=None)):
    row=db.get(ReviewCandidate,candidate_id)
    if not row: raise HTTPException(404,'Candidate not found')
    if row.review_status != 'draft': raise HTTPException(409,'Only drafts can be rejected')
    from .cross_source_api import record_audit
    record_audit(db,row.id,'rejected',x_admin_token,before={'review_status':row.review_status},after={'review_status':'rejected'})
    row.review_status='rejected';db.commit()
    return {'id':row.id,'result':'rejected'}

@router.post('/candidates/{candidate_id}/publish', dependencies=[Depends(admin_auth)])
def publish(candidate_id: int, decision: Decision, db: Session = Depends(get_db), x_admin_token: str | None = Header(default=None)):
    row=db.get(ReviewCandidate,candidate_id)
    if not row: raise HTTPException(404,'Candidate not found')
    if row.review_status != 'draft': raise HTTPException(409,'Only drafts can be published')
    if not decision.confirm_evidence_checked: raise HTTPException(422,'Confirm evidence review before publishing')
    if not row.evidence_quote or len(row.evidence_quote.strip()) < 15: raise HTTPException(422,'Save a supporting evidence quote first')
    if row.evidence_quote.strip().casefold() not in row.snapshot.body_text.casefold():
        raise HTTPException(422,'Evidence quote must be an exact excerpt from the saved source snapshot')
    if not row.title or len(row.title.strip()) < 8 or not row.summary or len(row.summary.strip()) < 20:
        raise HTTPException(422,'Title and summary are required')
    if row.category == 'other': raise HTTPException(422,'Select a specific project category')
    if row.title.strip() == row.snapshot.title.strip():
        raise HTTPException(422,'Replace the source-page title with a specific development claim title')
    if not row.snapshot.url.startswith('https://'): raise HTTPException(422,'HTTPS evidence URL required')
    # Phase 3F: two distinct ingested source keys and URLs are required.
    evidence_rows = db.scalars(select(CandidateEvidence).where(CandidateEvidence.candidate_id == row.id)).all()
    verification = compare_evidence(evidence_rows)
    if not verification['corroborated']:
        raise HTTPException(422,'Two distinct HTTPS source snapshots with different source keys and URLs are required before publication')
    if verification['conflicts']:
        raise HTTPException(409,{'message':'Conflicting source observations require review','conflicts':verification['conflicts']})
    warnings = field_warnings(row, row.snapshot.body_text)
    if warnings:
        raise HTTPException(422, {'message':'Resolve review validation issues before publishing', 'issues':warnings})
    others = db.scalars(select(ReviewCandidate).where(ReviewCandidate.snapshot_id == row.snapshot_id)).all()
    if any(x['review_status'] == 'published' for x in duplicate_suggestions(row, others)):
        raise HTTPException(409, 'Potentially matching project already published from this snapshot; resolve duplicate before publishing')
    src=db.scalar(select(Source).where(Source.url == row.snapshot.url))
    if not src:
        src=Source(title=row.snapshot.source_name[:300],url=row.snapshot.url,source_type='government')
        db.add(src);db.flush()
    dev=Development(id='apdi-'+uuid.uuid4().hex[:16],title=row.title,summary=row.summary,
        category=row.category,district=row.district,sector=row.sector,status=row.status,
        investment_inr_crore=row.investment_inr_crore,expected_jobs=row.expected_jobs,
        jobs_created=row.jobs_created,source_id=src.id,is_demo=False,verification_status='verified')
    db.add(dev)
    from .cross_source_api import record_audit
    record_audit(db,row.id,'published',x_admin_token,before={'review_status':row.review_status},after={'review_status':'published','development_id':dev.id})
    row.review_status='published';row.published_development_id=dev.id
    db.commit()
    return {'result':'published','development_id':dev.id,'source_url':src.url}

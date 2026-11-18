"""Authenticated source linking, comparisons, and append-only review history."""
import hashlib
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import CandidateEvidence, IngestionSnapshot, ReviewCandidate, ReviewAuditEvent
from .review_api import admin_auth
from .cross_source import compare_evidence, valid_quote, validate_observations

router = APIRouter(prefix='/api/v1/admin', tags=['cross-source'], dependencies=[Depends(admin_auth)])

class EvidenceCreate(BaseModel):
    snapshot_id: int
    quote: str = Field(min_length=15, max_length=3000)
    source_date: date | None = None
    observed_status: str | None = None
    observed_investment_inr_crore: float | None = Field(default=None, ge=0)
    observed_expected_jobs: int | None = Field(default=None, ge=0)
    observed_jobs_created: int | None = Field(default=None, ge=0)

def actor_id(token: str | None):
    # Token-derived pseudonym, not a human identity; do not store the secret itself.
    return 'local-admin-' + hashlib.sha256((token or '').encode()).hexdigest()[:12]

def record_audit(db, candidate_id, action, token, before=None, after=None):
    db.add(ReviewAuditEvent(candidate_id=candidate_id,action=action,actor=actor_id(token),
        before_json=json.dumps(before,default=str,ensure_ascii=False) if before is not None else None,
        after_json=json.dumps(after,default=str,ensure_ascii=False) if after is not None else None))

def evidence_for(db, candidate_id):
    return db.scalars(select(CandidateEvidence).where(CandidateEvidence.candidate_id==candidate_id).order_by(CandidateEvidence.id)).all()

def snapshot_evidence(e):
    return {'id':e.id,'snapshot_id':e.snapshot_id,'source_key':e.snapshot.source_key,'source_name':e.snapshot.source_name,
        'url':e.snapshot.url,'quote':e.quote,'source_date':e.source_date.isoformat() if e.source_date else None,
        'observed_status':e.observed_status,
        'observed_investment_inr_crore':float(e.observed_investment_inr_crore) if e.observed_investment_inr_crore is not None else None,
        'observed_expected_jobs':e.observed_expected_jobs,'observed_jobs_created':e.observed_jobs_created}

@router.get('/candidates/{candidate_id}/verification')
def verification(candidate_id: int, db: Session=Depends(get_db)):
    candidate=db.get(ReviewCandidate,candidate_id)
    if not candidate: raise HTTPException(404,'Candidate not found')
    rows=evidence_for(db,candidate_id)
    return {'candidate_id':candidate_id,'evidence':[snapshot_evidence(x) for x in rows],**compare_evidence(rows)}

@router.post('/candidates/{candidate_id}/evidence', status_code=201)
def add_evidence(candidate_id:int,payload:EvidenceCreate,db:Session=Depends(get_db),x_admin_token:str|None=Header(default=None)):
    candidate=db.get(ReviewCandidate,candidate_id)
    if not candidate: raise HTTPException(404,'Candidate not found')
    if candidate.review_status!='draft': raise HTTPException(409,'Evidence may only be added to draft candidates')
    snap=db.get(IngestionSnapshot,payload.snapshot_id)
    if not snap: raise HTTPException(404,'Source snapshot not found; ingest it first')
    if not snap.url.startswith('https://'): raise HTTPException(422,'Only HTTPS source snapshots are accepted')
    if not valid_quote(snap.body_text,payload.quote): raise HTTPException(422,'Evidence quote must be an exact 15+ character excerpt from the stored snapshot')
    if payload.observed_status and payload.observed_status not in {'unknown','announced','mou_signed','approved','grounded','operational','delayed','cancelled'}:
        raise HTTPException(422,'Invalid observed status')
    errors=validate_observations(payload.quote,payload.observed_investment_inr_crore,payload.observed_expected_jobs,payload.observed_jobs_created,payload.observed_status)
    if errors: raise HTTPException(422,{'message':'Unsupported field observations','issues':errors})
    exists=db.scalar(select(CandidateEvidence).where(CandidateEvidence.candidate_id==candidate_id,CandidateEvidence.snapshot_id==snap.id))
    if exists: raise HTTPException(409,'Snapshot already linked; preserve history by ingesting a new version instead')
    row=CandidateEvidence(candidate_id=candidate_id,**payload.model_dump())
    db.add(row);db.flush()
    record_audit(db,candidate_id,'evidence_linked',x_admin_token,after={'evidence_id':row.id,**payload.model_dump(mode='json')})
    db.commit()
    return {'id':row.id,'result':'linked','notice':'Source evidence added; verify source independence and all claims manually.'}

@router.get('/candidates/{candidate_id}/audit')
def audit(candidate_id:int,db:Session=Depends(get_db)):
    if not db.get(ReviewCandidate,candidate_id): raise HTTPException(404,'Candidate not found')
    events=db.scalars(select(ReviewAuditEvent).where(ReviewAuditEvent.candidate_id==candidate_id).order_by(ReviewAuditEvent.id)).all()
    return [{'id':x.id,'action':x.action,'actor':x.actor,'occurred_at':x.occurred_at.isoformat() if x.occurred_at else None,
        'before':json.loads(x.before_json) if x.before_json else None,'after':json.loads(x.after_json) if x.after_json else None} for x in events]

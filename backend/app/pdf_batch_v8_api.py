"""Read-only bulk status endpoint; one database read per table, never writes."""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot, ReviewCandidate
from .financial_evidence import FinancialEvidence, FinancialEvidenceAudit
from .review_api import admin_auth

router = APIRouter(prefix='/api/v1/admin', tags=['pdf-batch-v8'], dependencies=[Depends(admin_auth)])

def classify(records, kind):
    relevant = [r for r in records if r['kind'] == kind]
    approved = [r for r in relevant if r['review_status'] == 'approved']
    pending = [r for r in relevant if r['review_status'] == 'proposed']
    if approved: return 'approved'
    if pending: return 'pending'
    return 'needs_review'

@router.get('/snapshots/{snapshot_id}/pdf-financial-batch-status')
def batch_status(snapshot_id: int, db: Session = Depends(get_db)):
    snap = db.get(IngestionSnapshot, snapshot_id)
    if snap is None: raise HTTPException(404, 'Snapshot not found')
    if not snap.url.lower().split('?',1)[0].endswith('.pdf'):
        raise HTTPException(422, 'Snapshot is not a PDF')
    candidates = db.scalars(select(ReviewCandidate).where(ReviewCandidate.snapshot_id == snapshot_id)).all()
    ids = [c.id for c in candidates]
    evidence = db.scalars(select(FinancialEvidence).where(FinancialEvidence.candidate_id.in_(ids))).all() if ids else []
    evidence_ids = [e.id for e in evidence]
    audits = db.scalars(select(FinancialEvidenceAudit).where(FinancialEvidenceAudit.financial_evidence_id.in_(evidence_ids))).all() if evidence_ids else []
    by_candidate = defaultdict(list)
    for e in evidence:
        by_candidate[e.candidate_id].append({'id':e.id,'kind':e.kind,'review_status':e.review_status,'converted_amount_crore':str(e.converted_amount_crore),'source_page':e.source_page,'snapshot_id':e.snapshot_id})
    audit_by_evidence = defaultdict(list)
    for a in audits:
        audit_by_evidence[a.financial_evidence_id].append({'action':a.action,'reason':a.reason,'occurred_at':a.occurred_at.isoformat() if a.occurred_at else None})
    return {'snapshot_id':snapshot_id,'candidates':[
        {'candidate_id':c.id,'title':c.title,'candidate_status':c.review_status,
         'approved_project_cost_status':classify(by_candidate[c.id],'approved_project_cost'),
         'expenditure_incurred_status':classify(by_candidate[c.id],'expenditure_incurred'),
         'evidence':[{**r,'audit_events':audit_by_evidence[r['id']]} for r in by_candidate[c.id]]}
        for c in candidates],
        'notice':'Read-only snapshot status. Candidate matching is advisory. No proposal, approval, or publication.'}

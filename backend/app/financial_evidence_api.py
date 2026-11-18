"""Admin-only financial evidence workflow. Never updates candidate or development fields."""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot, ReviewCandidate
from .review_api import admin_auth
from .financial_evidence import FinancialEvidence, FinancialEvidenceAudit, validate_proposal

router = APIRouter(prefix='/api/v1/admin', tags=['financial-evidence'], dependencies=[Depends(admin_auth)])

class ProposalInput(BaseModel):
    snapshot_id: int = Field(gt=0)
    proposal: dict

class DecisionInput(BaseModel):
    confirm_original_pdf_checked: bool = False
    reason: str = Field(min_length=5, max_length=1000)

def output(row):
    return {'id': row.id, 'candidate_id': row.candidate_id, 'snapshot_id': row.snapshot_id,
            'kind': row.kind, 'original_amount_lakh': str(row.original_amount_lakh),
            'converted_amount_crore': str(row.converted_amount_crore), 'review_status': row.review_status,
            'source_page': row.source_page, 'source_line': row.source_line,
            'source_amount_index': row.source_amount_index, 'proposal': json.loads(row.proposal_json)}

@router.post('/candidates/{candidate_id}/financial-evidence', status_code=201)
def submit(candidate_id: int, payload: ProposalInput, db: Session = Depends(get_db), x_admin_token: str | None = Header(default=None)):
    candidate = db.get(ReviewCandidate, candidate_id)
    snap = db.get(IngestionSnapshot, payload.snapshot_id)
    if not candidate or not snap:
        raise HTTPException(404, 'Candidate or snapshot not found')
    if candidate.review_status != 'draft':
        raise HTTPException(409, 'Financial proposals may only be added to draft candidates')
    if candidate.snapshot_id != snap.id:
        raise HTTPException(422, 'For now, proposal snapshot must be the candidate source snapshot')
    try:
        original = validate_proposal(payload.proposal)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(422, str(e))
    p = payload.proposal
    if not snap.url.lower().endswith('.pdf') and '.pdf?' not in snap.url.lower():
        raise HTTPException(422, 'Snapshot must be from a PDF URL')
    # Source coordinates refer to the original PDF, not to normalized snapshot text.
    # Manual original-PDF verification is required; these fields are not independently verified here.
    from .pdf_batch_v8_guard import reject_existing_active_evidence
    reject_existing_active_evidence(db, candidate_id, p['kind'])
    row = FinancialEvidence(candidate_id=candidate_id, snapshot_id=snap.id, kind=p['kind'],
        original_amount_lakh=original, converted_amount_crore=original / 100,
        source_page=p['source_page'], source_line=p['source_line'], source_amount_index=p['source_amount_index'],
        source_amount_token=str(p['source_amount_token']), source_text=p['source_text'],
        project_anchor_json=json.dumps(p['project_anchor']), unit_evidence_json=json.dumps(p['unit_evidence']),
        proposal_json=json.dumps(p), review_status='proposed')
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Financial evidence already submitted for these source coordinates')
    db.add(FinancialEvidenceAudit(financial_evidence_id=row.id, action='proposed', actor='admin-token-authenticated'))
    db.commit()
    return output(row)

@router.get('/candidates/{candidate_id}/financial-evidence')
def list_evidence(candidate_id: int, db: Session = Depends(get_db)):
    if not db.get(ReviewCandidate, candidate_id):
        raise HTTPException(404, 'Candidate not found')
    return [output(row) for row in db.scalars(select(FinancialEvidence).where(FinancialEvidence.candidate_id == candidate_id).order_by(FinancialEvidence.id.desc())).all()]

@router.get('/candidates/{candidate_id}/financial-evidence/audit')
def list_financial_audit(candidate_id: int, db: Session = Depends(get_db)):
    if not db.get(ReviewCandidate, candidate_id):
        raise HTTPException(404, 'Candidate not found')
    records = db.scalars(select(FinancialEvidenceAudit).join(
        FinancialEvidence, FinancialEvidenceAudit.financial_evidence_id == FinancialEvidence.id
    ).where(FinancialEvidence.candidate_id == candidate_id).order_by(FinancialEvidenceAudit.id.desc())).all()
    return [{'id': event.id, 'financial_evidence_id': event.financial_evidence_id,
             'action': event.action, 'actor': event.actor, 'reason': event.reason,
             'occurred_at': event.occurred_at.isoformat() if event.occurred_at else None}
            for event in records]

@router.post('/financial-evidence/{evidence_id}/{decision}')
def decide(evidence_id: int, decision: str, payload: DecisionInput, db: Session = Depends(get_db)):
    if decision not in ('approve', 'reject'):
        raise HTTPException(404, 'Unknown decision')
    row = db.get(FinancialEvidence, evidence_id)
    if not row:
        raise HTTPException(404, 'Financial evidence not found')
    if row.review_status != 'proposed':
        raise HTTPException(409, 'Only proposed financial evidence can be decided')
    if not payload.confirm_original_pdf_checked:
        raise HTTPException(422, 'Confirm original PDF row, column and measure before decision')
    row.review_status = 'approved' if decision == 'approve' else 'rejected'
    row.reviewed_at = datetime.now(timezone.utc)
    db.add(FinancialEvidenceAudit(financial_evidence_id=row.id, action=row.review_status,
                                  actor='admin-token-authenticated', reason=payload.reason))
    db.commit()
    return output(row)

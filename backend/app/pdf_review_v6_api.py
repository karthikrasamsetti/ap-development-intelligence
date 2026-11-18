"""Read-only conflict inspection for PDF review rows; never modifies candidates."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import get_db
from .models import ReviewCandidate
from .financial_evidence import FinancialEvidence
from .review_api import admin_auth

router = APIRouter(prefix='/api/v1/admin', tags=['pdf-review-v6'], dependencies=[Depends(admin_auth)])


def compare_amounts(extracted_lakh, candidate_investment_crore, approved_evidence):
    """Compare like-for-like only: draft investment is NOT necessarily approved cost."""
    pdf_crore = Decimal(str(extracted_lakh)) / Decimal('100') if extracted_lakh is not None else None
    draft = Decimal(str(candidate_investment_crore)) if candidate_investment_crore is not None else None
    approved = [e for e in approved_evidence if e['kind'] == 'approved_project_cost' and e['review_status'] == 'approved']
    differing_approved = [e for e in approved if pdf_crore is not None and Decimal(str(e['converted_amount_crore'])) != pdf_crore]
    return {
        'pdf_approved_cost_crore': str(pdf_crore) if pdf_crore is not None else None,
        'draft_investment_crore': str(draft) if draft is not None else None,
        'draft_comparison': 'different_measure_review_required' if draft is not None and pdf_crore is not None and draft != pdf_crore else 'same_number_not_proof_of_same_measure' if draft is not None and pdf_crore == draft else 'not_available',
        'approved_cost_conflict': bool(differing_approved),
        'approved_cost_evidence': approved,
        'notice': 'Candidate investment and approved project cost may be different measures. Differences are review flags, not automatic corrections.',
    }

@router.get('/candidates/{candidate_id}/pdf-financial-comparison')
def financial_comparison(candidate_id: int, pdf_approved_cost_lakh: str, snapshot_id: int, db: Session = Depends(get_db)):
    candidate = db.get(ReviewCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(404, 'Candidate not found')
    if candidate.snapshot_id != snapshot_id:
        raise HTTPException(422, 'Candidate must belong to selected snapshot')
    try:
        value = Decimal(pdf_approved_cost_lakh)
        if not value.is_finite() or value < 0 or value > 1000000000:
            raise ValueError()
    except Exception:
        raise HTTPException(422, 'Invalid approved-cost amount')
    evidence = db.scalars(select(FinancialEvidence).where(FinancialEvidence.candidate_id == candidate_id)).all()
    serialized = [{'id':e.id, 'kind':e.kind, 'review_status':e.review_status, 'converted_amount_crore':str(e.converted_amount_crore), 'source_page':e.source_page} for e in evidence]
    return {'candidate_id':candidate_id, 'snapshot_id':snapshot_id, 'candidate_title':candidate.title, 'candidate_status':candidate.review_status, **compare_amounts(value, candidate.investment_inr_crore, serialized)}

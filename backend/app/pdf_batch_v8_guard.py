"""Backend-level guard for a candidate+measure; call within submit transaction."""
from fastapi import HTTPException
from sqlalchemy import select
from .financial_evidence import FinancialEvidence

def reject_existing_active_evidence(db, candidate_id, kind):
    rows = db.scalars(select(FinancialEvidence).where(
        FinancialEvidence.candidate_id == candidate_id,
        FinancialEvidence.kind == kind,
        FinancialEvidence.review_status.in_(('approved', 'proposed'))
    )).all()
    if rows:
        states = ', '.join(f'#{r.id} ({r.review_status})' for r in rows)
        raise HTTPException(409, f'Active evidence already exists for this candidate and measure: {states}. Review it before proposing another.')

"""Financial evidence records: isolated from candidate edits and publication."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

KINDS = ('approved_project_cost', 'expenditure_incurred', 'tender_ecv', 'agreement_amount')

class FinancialEvidence(Base):
    __tablename__ = 'financial_evidence'
    __table_args__ = (UniqueConstraint('candidate_id', 'snapshot_id', 'kind', 'source_page', 'source_line', 'source_amount_index', name='uq_financial_evidence_anchor'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('review_candidates.id'), nullable=False, index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('ingestion_snapshots.id'), nullable=False)
    archived_document_id: Mapped[int | None] = mapped_column(ForeignKey('archived_source_documents.id'), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    original_amount_lakh: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    converted_amount_crore: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_line: Mapped[int] = mapped_column(Integer, nullable=False)
    source_amount_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_amount_token: Mapped[str] = mapped_column(String(50), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    project_anchor_json: Mapped[str] = mapped_column(Text, nullable=False)
    unit_evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default='proposed')
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class FinancialEvidenceAudit(Base):
    __tablename__ = 'financial_evidence_audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    financial_evidence_id: Mapped[int] = mapped_column(ForeignKey('financial_evidence.id'), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

def validate_proposal(p: dict) -> Decimal:
    if p.get('state') != 'proposed_unpublished' or p.get('kind') not in KINDS:
        raise ValueError('Invalid proposal state or financial measure')
    if p.get('reviewer_verified_row_and_column') is not True:
        raise ValueError('Reviewer must confirm the original PDF row and column')
    for field in ('source_page', 'source_line', 'source_amount_index'):
        if type(p.get(field)) is not int or p[field] < (0 if field == 'source_amount_index' else 1):
            raise ValueError('Invalid source coordinates: ' + field)
    if not isinstance(p.get('source_text'), str) or not p['source_text'].strip():
        raise ValueError('Missing original source line')
    for key in ('project_anchor', 'unit_evidence'):
        value = p.get(key)
        if not isinstance(value, dict) or not isinstance(value.get('text'), str) or not value['text'].strip():
            raise ValueError('Missing ' + key)
        if type(value.get('page')) is not int or value['page'] < 1 or type(value.get('line')) is not int or value['line'] < 1:
            raise ValueError('Invalid ' + key + ' coordinates')
    if 'lakh' not in p['unit_evidence']['text'].lower():
        raise ValueError('Unit evidence does not identify lakhs')
    if str(p.get('project', '')).strip().casefold() not in ('',) and not any(word in p['project_anchor']['text'].casefold() for word in p['project'].casefold().split() if len(word) >= 5):
        raise ValueError('Project anchor does not appear to match the project')
    try:
        original = Decimal(str(p['original_amount_lakh']))
        converted = Decimal(str(p['converted_amount_crore']))
        token = Decimal(str(p['source_amount_token']).replace(',', ''))
    except (InvalidOperation, KeyError):
        raise ValueError('Invalid financial values')
    if not original.is_finite() or original < 0 or token != original or converted != original / 100:
        raise ValueError('Financial conversion or token mismatch')
    if str(p['source_amount_token']) not in p['source_text']:
        raise ValueError('Source token not present in original line')
    return original

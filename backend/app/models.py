from datetime import date, datetime, timezone
from sqlalchemy import UniqueConstraint, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(Text, unique=True)
    published_on: Mapped[date | None] = mapped_column(Date)
    source_type: Mapped[str] = mapped_column(String(30), default='other')

class Development(Base):
    __tablename__ = 'developments'
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(40), index=True)
    district: Mapped[str | None] = mapped_column(String(100), index=True)
    sector: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40), index=True)
    investment_inr_crore: Mapped[float | None] = mapped_column(Numeric(16, 2))
    expected_jobs: Mapped[int | None] = mapped_column(Integer)
    jobs_created: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey('sources.id'))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), default='unverified')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[Source | None] = relationship()


class IngestionSnapshot(Base):
    __tablename__ = 'ingestion_snapshots'
    __table_args__ = (UniqueConstraint('source_key','content_hash',name='uq_snapshot_source_hash'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80))
    source_name: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(300))
    content_hash: Mapped[str] = mapped_column(String(64))
    excerpt: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(30),default='pending')
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc))

class ReviewCandidate(Base):
    __tablename__ = 'review_candidates'
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('ingestion_snapshots.id'))
    extraction_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), default='other')
    district: Mapped[str | None] = mapped_column(String(100))
    sector: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40), default='announced')
    investment_inr_crore: Mapped[float | None] = mapped_column(Numeric(16,2))
    expected_jobs: Mapped[int | None] = mapped_column(Integer)
    jobs_created: Mapped[int | None] = mapped_column(Integer)
    evidence_quote: Mapped[str] = mapped_column(Text, default='')
    review_status: Mapped[str] = mapped_column(String(30), default='draft')
    published_development_id: Mapped[str | None] = mapped_column(ForeignKey('developments.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    extraction_method: Mapped[str | None] = mapped_column(String(30))
    field_evidence: Mapped[str | None] = mapped_column(Text)
    extraction_warning: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[IngestionSnapshot] = relationship()

# LLM metadata is additive; old heuristic/manual drafts remain unchanged.


class CandidateEvidence(Base):
    __tablename__ = 'candidate_evidence'
    __table_args__ = (UniqueConstraint('candidate_id', 'snapshot_id', name='uq_candidate_evidence_snapshot'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('review_candidates.id'), nullable=False, index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('ingestion_snapshots.id'), nullable=False, index=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    observed_status: Mapped[str | None] = mapped_column(String(40))
    observed_investment_inr_crore: Mapped[float | None] = mapped_column(Numeric(16,2))
    observed_expected_jobs: Mapped[int | None] = mapped_column(Integer)
    observed_jobs_created: Mapped[int | None] = mapped_column(Integer)
    source_date: Mapped[date | None] = mapped_column(Date)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    snapshot: Mapped[IngestionSnapshot] = relationship()

class ReviewAuditEvent(Base):
    __tablename__ = 'review_audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey('review_candidates.id'), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SourceMonitorState(Base):
    __tablename__ = 'source_monitor_state'
    source_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('ingestion_snapshots.id'))
    last_content_hash: Mapped[str | None] = mapped_column(String(64))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)

class SourceMonitorRun(Base):
    __tablename__ = 'source_monitor_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), index=True)
    result: Mapped[str] = mapped_column(String(30))
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('ingestion_snapshots.id'))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class DiscoveryProposal(Base):
    __tablename__='discovery_proposals'
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_source_key: Mapped[str] = mapped_column(String(80),nullable=False,index=True)
    url: Mapped[str] = mapped_column(Text,nullable=False,unique=True)
    title: Mapped[str] = mapped_column(String(300),nullable=False)
    status: Mapped[str] = mapped_column(String(30),nullable=False,default='proposed')
    last_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('ingestion_snapshots.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)

class DiscoveryEvent(Base):
    __tablename__='discovery_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey('discovery_proposals.id'))
    action: Mapped[str] = mapped_column(String(40),nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)

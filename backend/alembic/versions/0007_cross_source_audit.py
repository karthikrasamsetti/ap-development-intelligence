"""Cross-source candidate evidence and reviewer audit trail.
Revision ID: 0007_cross_source_audit
Revises: 0006_review_safety
"""
from alembic import op
import sqlalchemy as sa
revision = '0007_cross_source_audit'
down_revision = '0006_review_safety'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('candidate_evidence',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('candidate_id',sa.Integer(),sa.ForeignKey('review_candidates.id'),nullable=False),
        sa.Column('snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id'),nullable=False),
        sa.Column('quote',sa.Text(),nullable=False),
        sa.Column('observed_status',sa.String(40)),
        sa.Column('observed_investment_inr_crore',sa.Numeric(16,2)),
        sa.Column('observed_expected_jobs',sa.Integer()),
        sa.Column('observed_jobs_created',sa.Integer()),
        sa.Column('source_date',sa.Date()),
        sa.Column('added_at',sa.DateTime(timezone=True)),
        sa.UniqueConstraint('candidate_id','snapshot_id',name='uq_candidate_evidence_snapshot'))
    op.create_index('ix_candidate_evidence_candidate_id','candidate_evidence',['candidate_id'])
    op.create_index('ix_candidate_evidence_snapshot_id','candidate_evidence',['snapshot_id'])
    op.create_table('review_audit_events',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('candidate_id',sa.Integer(),sa.ForeignKey('review_candidates.id'),nullable=False),
        sa.Column('action',sa.String(50),nullable=False),
        sa.Column('actor',sa.String(100),nullable=False),
        sa.Column('before_json',sa.Text()),
        sa.Column('after_json',sa.Text()),
        sa.Column('occurred_at',sa.DateTime(timezone=True)))
    op.create_index('ix_review_audit_events_candidate_id','review_audit_events',['candidate_id'])
    # Backfill all existing candidates, including the 17 drafts, without changing their status.
    op.execute(sa.text("INSERT INTO candidate_evidence (candidate_id, snapshot_id, quote, added_at) "
        "SELECT id, snapshot_id, COALESCE(evidence_quote, ''), CURRENT_TIMESTAMP "
        "FROM review_candidates ON CONFLICT (candidate_id, snapshot_id) DO NOTHING"))

def downgrade():
    op.drop_index('ix_review_audit_events_candidate_id',table_name='review_audit_events')
    op.drop_table('review_audit_events')
    op.drop_index('ix_candidate_evidence_snapshot_id',table_name='candidate_evidence')
    op.drop_index('ix_candidate_evidence_candidate_id',table_name='candidate_evidence')
    op.drop_table('candidate_evidence')

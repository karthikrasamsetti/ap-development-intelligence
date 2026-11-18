"""Version the Phase 3K.4C financial evidence schema; preserve manually installed tables."""
from alembic import op
import sqlalchemy as sa
revision = '0010_financial_evidence'
down_revision = '0009_discovery_queue'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if 'financial_evidence' not in existing:
        op.create_table('financial_evidence',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('candidate_id',sa.Integer(),sa.ForeignKey('review_candidates.id'),nullable=False),
            sa.Column('snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id'),nullable=False),
            sa.Column('kind',sa.String(40),nullable=False),
            sa.Column('original_amount_lakh',sa.Numeric(18,4),nullable=False),
            sa.Column('converted_amount_crore',sa.Numeric(18,6),nullable=False),
            sa.Column('source_page',sa.Integer(),nullable=False),
            sa.Column('source_line',sa.Integer(),nullable=False),
            sa.Column('source_amount_index',sa.Integer(),nullable=False),
            sa.Column('source_amount_token',sa.String(50),nullable=False),
            sa.Column('source_text',sa.Text(),nullable=False),
            sa.Column('project_anchor_json',sa.Text(),nullable=False),
            sa.Column('unit_evidence_json',sa.Text(),nullable=False),
            sa.Column('proposal_json',sa.Text(),nullable=False),
            sa.Column('review_status',sa.String(20),nullable=False),
            sa.Column('proposed_at',sa.DateTime(timezone=True)),
            sa.Column('reviewed_at',sa.DateTime(timezone=True)),
            sa.UniqueConstraint('candidate_id','snapshot_id','kind','source_page','source_line','source_amount_index',name='uq_financial_evidence_anchor'))
    if 'financial_evidence_audit' not in existing:
        op.create_table('financial_evidence_audit',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('financial_evidence_id',sa.Integer(),sa.ForeignKey('financial_evidence.id'),nullable=False),
            sa.Column('action',sa.String(40),nullable=False),
            sa.Column('actor',sa.String(100),nullable=False),
            sa.Column('reason',sa.Text()),
            sa.Column('occurred_at',sa.DateTime(timezone=True)))
    for table,column,name in [('financial_evidence','candidate_id','ix_financial_evidence_candidate_id'),('financial_evidence_audit','financial_evidence_id','ix_financial_evidence_audit_financial_evidence_id')]:
        indices = {i['name'] for i in sa.inspect(bind).get_indexes(table)}
        if name not in indices:
            op.create_index(name,table,[column])

def downgrade():
    # Non-destructive: financial review history must never be dropped automatically.
    raise RuntimeError('Destructive downgrade disabled for financial evidence and audit history')

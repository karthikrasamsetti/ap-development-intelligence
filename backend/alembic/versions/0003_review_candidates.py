"""Manual claim review queue.
Revision ID: 0003_review_candidates
Revises: 0002_source_snapshots
"""
from alembic import op
import sqlalchemy as sa
revision='0003_review_candidates'
down_revision='0002_source_snapshots'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('review_candidates',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id'),nullable=False,unique=True),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('summary',sa.Text(),nullable=False),
        sa.Column('category',sa.String(40),nullable=False),
        sa.Column('district',sa.String(100)),
        sa.Column('sector',sa.String(100)),
        sa.Column('status',sa.String(40),nullable=False),
        sa.Column('investment_inr_crore',sa.Numeric(16,2)),
        sa.Column('expected_jobs',sa.Integer()),
        sa.Column('jobs_created',sa.Integer()),
        sa.Column('evidence_quote',sa.Text(),nullable=False,server_default=''),
        sa.Column('review_status',sa.String(30),nullable=False,server_default='draft'),
        sa.Column('published_development_id',sa.String(60),sa.ForeignKey('developments.id')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))

def downgrade():
    op.drop_table('review_candidates')

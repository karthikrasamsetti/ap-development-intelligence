"""Store source snapshots for human review.
Revision ID: 0002_source_snapshots
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
revision='0002_source_snapshots'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('ingestion_snapshots',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('source_key',sa.String(80),nullable=False),
        sa.Column('source_name',sa.String(300),nullable=False),
        sa.Column('url',sa.Text(),nullable=False),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('content_hash',sa.String(64),nullable=False),
        sa.Column('excerpt',sa.Text(),nullable=False),
        sa.Column('body_text',sa.Text(),nullable=False),
        sa.Column('review_status',sa.String(30),nullable=False,server_default='pending'),
        sa.Column('fetched_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('source_key','content_hash',name='uq_snapshot_source_hash'))
    op.create_index('ix_snapshots_review_status','ingestion_snapshots',['review_status'])

def downgrade():
    op.drop_index('ix_snapshots_review_status',table_name='ingestion_snapshots')
    op.drop_table('ingestion_snapshots')

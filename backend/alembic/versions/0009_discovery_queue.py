"""Phase 3H additive discovery queue. Preserves all existing data."""
from alembic import op
import sqlalchemy as sa
revision='0009_discovery_queue'
down_revision='0008_source_monitor'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('discovery_proposals',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('parent_source_key',sa.String(80),nullable=False),
        sa.Column('url',sa.Text(),nullable=False,unique=True),
        sa.Column('title',sa.String(300),nullable=False),
        sa.Column('status',sa.String(30),nullable=False,server_default='proposed'),
        sa.Column('last_snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_discovery_proposals_parent_source_key','discovery_proposals',['parent_source_key'])
    op.create_table('discovery_events',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('proposal_id',sa.Integer(),sa.ForeignKey('discovery_proposals.id')),
        sa.Column('action',sa.String(40),nullable=False),
        sa.Column('detail',sa.Text()),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table('discovery_events')
    op.drop_index('ix_discovery_proposals_parent_source_key',table_name='discovery_proposals')
    op.drop_table('discovery_proposals')

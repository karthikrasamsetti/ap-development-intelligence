"""Source monitor state and append-only runs.
Revision ID: 0008_source_monitor
Revises: 0007_cross_source_audit
"""
from alembic import op
import sqlalchemy as sa
revision='0008_source_monitor'
down_revision='0007_cross_source_audit'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('source_monitor_state',
        sa.Column('source_key',sa.String(80),primary_key=True),
        sa.Column('source_url',sa.Text(),nullable=False),
        sa.Column('enabled',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('last_checked_at',sa.DateTime(timezone=True)),
        sa.Column('last_success_at',sa.DateTime(timezone=True)),
        sa.Column('last_snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id')),
        sa.Column('last_content_hash',sa.String(64)),
        sa.Column('consecutive_failures',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('last_error',sa.Text()))
    op.create_table('source_monitor_runs',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('source_key',sa.String(80),nullable=False),
        sa.Column('result',sa.String(30),nullable=False),
        sa.Column('snapshot_id',sa.Integer(),sa.ForeignKey('ingestion_snapshots.id')),
        sa.Column('error_message',sa.Text()),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('finished_at',sa.DateTime(timezone=True)))
    op.create_index('ix_source_monitor_runs_source_key','source_monitor_runs',['source_key'])

def downgrade():
    op.drop_index('ix_source_monitor_runs_source_key',table_name='source_monitor_runs')
    op.drop_table('source_monitor_runs')
    op.drop_table('source_monitor_state')

"""Add immutable PDF archive metadata without modifying existing evidence."""
from alembic import op
import sqlalchemy as sa

revision = '0012_source_provenance'
down_revision = '0011_active_financial_evidence'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('archived_source_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_id', sa.Integer(), sa.ForeignKey('ingestion_snapshots.id'), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('snapshot_id', 'sha256', name='uq_archived_source_snapshot_sha256'))
    op.create_index('ix_archived_source_documents_snapshot_id', 'archived_source_documents', ['snapshot_id'])
    op.create_index('ix_archived_source_documents_sha256', 'archived_source_documents', ['sha256'])


def downgrade():
    raise RuntimeError('Archive provenance must not be dropped automatically')

"""Bind financial evidence to archived source documents without retroactive certification."""
from alembic import op
import sqlalchemy as sa

revision = '0013_financial_provenance'
down_revision = '0012_source_provenance'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('financial_evidence', sa.Column('archived_document_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_financial_evidence_archived_document', 'financial_evidence',
                          'archived_source_documents', ['archived_document_id'], ['id'])
    op.create_index('ix_financial_evidence_archived_document_id', 'financial_evidence', ['archived_document_id'])
    # Existing approvals and proposals intentionally retain NULL (legacy/unbound).


def downgrade():
    raise RuntimeError('Financial provenance binding must not be removed automatically')

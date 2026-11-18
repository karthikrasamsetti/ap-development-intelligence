"""LLM provenance and per-field evidence for review drafts.
Revision ID: 0005_llm_evidence
Revises: 0004_multi_claim_extraction
"""
from alembic import op
import sqlalchemy as sa
revision='0005_llm_evidence'
down_revision='0004_multi_claim_extraction'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('review_candidates',sa.Column('extraction_method',sa.String(30),nullable=True))
    op.add_column('review_candidates',sa.Column('field_evidence',sa.Text(),nullable=True))
    op.add_column('review_candidates',sa.Column('extraction_warning',sa.Text(),nullable=True))

def downgrade():
    op.drop_column('review_candidates','extraction_warning')
    op.drop_column('review_candidates','field_evidence')
    op.drop_column('review_candidates','extraction_method')

"""Use unknown status for future review drafts.
Revision ID: 0006_review_safety
Revises: 0005_llm_evidence
"""
from alembic import op
import sqlalchemy as sa
revision = '0006_review_safety'
down_revision = '0005_llm_evidence'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('review_candidates', 'status', existing_type=sa.String(40), server_default='unknown')
    op.execute("UPDATE review_candidates SET status = 'unknown' WHERE extraction_method = 'llm' AND extraction_warning IS NOT NULL AND review_status = 'draft'")

def downgrade():
    op.alter_column('review_candidates', 'status', existing_type=sa.String(40), server_default=None)

"""Multiple claim candidates per snapshot with idempotent extraction.
Revision ID: 0004_multi_claim_extraction
Revises: 0003_review_candidates
"""
from alembic import op
import sqlalchemy as sa
revision='0004_multi_claim_extraction'
down_revision='0003_review_candidates'
branch_labels=None
depends_on=None

def upgrade():
    op.drop_constraint('review_candidates_snapshot_id_key','review_candidates',type_='unique')
    op.add_column('review_candidates',sa.Column('extraction_fingerprint',sa.String(64),nullable=True))
    op.create_unique_constraint('uq_review_candidate_fingerprint','review_candidates',['extraction_fingerprint'])

def downgrade():
    op.drop_constraint('uq_review_candidate_fingerprint','review_candidates',type_='unique')
    op.drop_column('review_candidates','extraction_fingerprint')
    # Preserve existing multi-claim data; downgrade requires manually resolving duplicates.
    op.create_unique_constraint('review_candidates_snapshot_id_key','review_candidates',['snapshot_id'])

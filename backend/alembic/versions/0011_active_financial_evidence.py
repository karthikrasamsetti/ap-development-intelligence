"""Prevent concurrent active evidence for the same candidate and financial measure.

IMPORTANT: Preexisting duplicates cause upgrade to fail; reconcile manually first.
"""
from alembic import op
import sqlalchemy as sa

revision = '0011_active_financial_evidence'
down_revision = '0010_financial_evidence'
branch_labels = None
depends_on = None

INDEX_NAME = 'uq_financial_evidence_active_candidate_kind'


def upgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text("""
        SELECT candidate_id, kind, COUNT(*) AS n
        FROM financial_evidence
        WHERE review_status IN ('proposed', 'approved')
        GROUP BY candidate_id, kind HAVING COUNT(*) > 1
    """)).fetchall()
    if duplicates:
        examples = ', '.join(f'candidate={r[0]} kind={r[1]} count={r[2]}' for r in duplicates[:10])
        raise RuntimeError('Active financial evidence duplicates exist; review and resolve manually before migration: ' + examples)
    op.create_index(INDEX_NAME, 'financial_evidence', ['candidate_id', 'kind'], unique=True,
                    postgresql_where=sa.text("review_status IN ('proposed', 'approved')"),
                    sqlite_where=sa.text("review_status IN ('proposed', 'approved')"))


def downgrade():
    op.drop_index(INDEX_NAME, table_name='financial_evidence')

"""Regression checks for the v10 migration's active-evidence invariant."""
import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, text
import pytest

MIGRATION = Path(__file__).resolve().parents[1] / 'alembic' / 'versions' / '0011_active_financial_evidence.py'
spec = importlib.util.spec_from_file_location('financial_active_v10', MIGRATION)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_active_unique_index_sqlite(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE financial_evidence (id INTEGER PRIMARY KEY, candidate_id INTEGER, kind TEXT, review_status TEXT)'))
        monkeypatch.setattr(migration.op, 'get_bind', lambda: conn)
        monkeypatch.setattr(migration.op, 'create_index', lambda name, table, cols, **kwargs: conn.execute(text(
            f"CREATE UNIQUE INDEX {name} ON {table} (candidate_id, kind) WHERE review_status IN ('proposed', 'approved')")))
        migration.upgrade()
        conn.execute(text("INSERT INTO financial_evidence VALUES (1,23,'approved_project_cost','approved')"))
        with pytest.raises(Exception):
            conn.execute(text("INSERT INTO financial_evidence VALUES (2,23,'approved_project_cost','proposed')"))
        conn.execute(text("INSERT INTO financial_evidence VALUES (3,23,'expenditure_incurred','proposed')"))
        conn.execute(text("INSERT INTO financial_evidence VALUES (4,23,'approved_project_cost','rejected')"))


def test_upgrade_refuses_preexisting_duplicates(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE financial_evidence (id INTEGER PRIMARY KEY, candidate_id INTEGER, kind TEXT, review_status TEXT)'))
        conn.execute(text("INSERT INTO financial_evidence VALUES (1,23,'approved_project_cost','proposed'), (2,23,'approved_project_cost','approved')"))
        monkeypatch.setattr(migration.op, 'get_bind', lambda: conn)
        with pytest.raises(RuntimeError, match='duplicates exist'):
            migration.upgrade()

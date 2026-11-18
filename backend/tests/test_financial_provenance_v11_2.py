"""Fail-closed provenance checks without requiring a live PostgreSQL server."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.financial_evidence_api import require_verified_archive, ProposalInput, BindArchiveInput
from app.source_archive import ArchivedSourceDocument, archive_pdf
import app.financial_evidence_api as api


def test_missing_archive_binding_fails():
    with pytest.raises(HTTPException) as exc:
        require_verified_archive(Mock(), None, 4)
    assert exc.value.status_code == 409


def test_wrong_snapshot_fails(monkeypatch):
    monkeypatch.setattr(api, 'verify_pdf', lambda *_: True)
    db = Mock()
    db.get.return_value = SimpleNamespace(snapshot_id=9, sha256='a'*64, byte_size=12)
    with pytest.raises(HTTPException) as exc:
        require_verified_archive(db, 1, 4)
    assert exc.value.status_code == 422


def test_missing_or_tampered_pdf_fails(monkeypatch, tmp_path):
    pdf = b'%PDF-1.4\n%%EOF'
    digest, size = archive_pdf(pdf, tmp_path)
    db = Mock()
    db.get.return_value = SimpleNamespace(snapshot_id=4, sha256=digest, byte_size=size)
    monkeypatch.setattr(api, 'verify_pdf', lambda h, n: __import__('app.source_archive', fromlist=['verify_pdf']).verify_pdf(h, n, tmp_path))
    assert require_verified_archive(db, 1, 4).snapshot_id == 4
    (tmp_path / (digest + '.pdf')).write_bytes(b'tampered')
    with pytest.raises(HTTPException) as exc:
        require_verified_archive(db, 1, 4)
    assert exc.value.status_code == 409


def test_new_proposals_require_archive_id():
    with pytest.raises(Exception):
        ProposalInput(snapshot_id=4, proposal={})
    assert BindArchiveInput(archived_document_id=1).confirm_original_pdf_checked is False


def test_model_nullable_legacy_binding():
    col = ArchivedSourceDocument.__table__.c.snapshot_id
    assert col.nullable is False
    from app.financial_evidence import FinancialEvidence
    assert FinancialEvidence.__table__.c.archived_document_id.nullable is True

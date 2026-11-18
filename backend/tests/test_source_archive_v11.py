import hashlib
from pathlib import Path
import pytest
from app.source_archive import archive_pdf, digest_pdf, verify_pdf


def test_archive_and_integrity(tmp_path: Path):
    pdf = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF'
    digest, size = archive_pdf(pdf, tmp_path)
    assert digest == hashlib.sha256(pdf).hexdigest()
    assert size == len(pdf)
    assert verify_pdf(digest, size, tmp_path)
    assert archive_pdf(pdf, tmp_path) == (digest, size)
    (tmp_path / (digest + '.pdf')).write_bytes(b'tampered')
    assert not verify_pdf(digest, size, tmp_path)
    with pytest.raises(RuntimeError):
        archive_pdf(pdf, tmp_path)


def test_reject_bad_pdf(tmp_path: Path):
    with pytest.raises(ValueError):
        archive_pdf(b'not a PDF', tmp_path)
    assert not verify_pdf('../' + 'a'*61, 5, tmp_path)

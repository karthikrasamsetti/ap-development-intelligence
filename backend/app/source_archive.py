"""Content-addressed PDF storage; never trusts filenames or client-supplied digests."""
import hashlib
import os
from pathlib import Path
import tempfile

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

MAX_PDF_BYTES = 15 * 1024 * 1024
ARCHIVE_ROOT = Path(os.getenv('APDI_ARCHIVE_DIR', '/app/source_archive'))

class ArchivedSourceDocument(Base):
    __tablename__ = 'archived_source_documents'
    __table_args__ = (UniqueConstraint('snapshot_id', 'sha256', name='uq_archived_source_snapshot_sha256'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('ingestion_snapshots.id'), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    archived_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def digest_pdf(content: bytes) -> str:
    if not content.startswith(b'%PDF-'):
        raise ValueError('Not a PDF file')
    if not content or len(content) > MAX_PDF_BYTES:
        raise ValueError('PDF size out of bounds')
    return hashlib.sha256(content).hexdigest()


def archive_pdf(content: bytes, root: Path = ARCHIVE_ROOT) -> tuple[str, int]:
    digest = digest_pdf(content)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = root / f'{digest}.pdf'
    if target.exists():
        if not verify_pdf(digest, len(content), root):
            raise RuntimeError('Archive collision or tampered document; manual intervention required')
        return digest, len(content)
    fd, temporary = tempfile.mkstemp(prefix='.incoming-', dir=root)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # Exclusive creation: never overwrite an existing archive entry.
        try:
            os.link(temporary, target)
        except FileExistsError:
            if not verify_pdf(digest, len(content), root):
                raise RuntimeError('Archive collision or tampered document')
        return digest, len(content)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_pdf(digest: str, expected_size: int, root: Path = ARCHIVE_ROOT) -> bool:
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        return False
    path = root / f'{digest}.pdf'
    if not path.is_file() or path.is_symlink():
        return False
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                return False
            h.update(chunk)
    return size == expected_size and h.hexdigest() == digest

"""Read-only, page-aware PDF inspection for human review.

Does not update snapshots, create candidates, or assert project/amount attribution.
"""
from __future__ import annotations
import argparse
import json
import re
from io import BytesIO
from pathlib import Path

MAX_PAGES = 40
MAX_BYTES = 15_000_000
PROJECT_RE = re.compile(r'\bMSE\s*[- ]?\s*CDP\s+(?:IP|JP)\s*[-–]?\s*([A-Za-z][A-Za-z .-]{2,55})', re.I)
MONEY_RE = re.compile(r'(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d{4,}(?:\.\d+)?)(?!\d)')
UNIT_RE = re.compile(r'Rs\.?\s*in\s*lakhs?|₹\s*in\s*lakhs?|INR\s*in\s*lakhs?', re.I)
TOTAL_RE = re.compile(r'\btotal\s*:?', re.I)

def extract_pages(pdf_bytes: bytes) -> list[dict]:
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError('PDF exceeds inspection byte limit')
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('Install pypdf to inspect PDF files') from exc
    reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    if len(reader.pages) > MAX_PAGES:
        raise ValueError('PDF exceeds inspection page limit')
    pages = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text(extraction_mode='layout') or ''
        except (TypeError, ValueError):
            text = page.extract_text() or ''
        pages.append({'page': i, 'text': text})
    return pages

def inspect_pages(pages: list[dict], project_filter: str | None = None) -> dict:
    """Produce review hints only. A financial number is NEVER linked to a project automatically."""
    result = []
    for page in pages:
        lines = [re.sub(r'\s+', ' ', line).strip() for line in page['text'].splitlines()]
        lines = [line for line in lines if line]
        hits = []
        for i, line in enumerate(lines):
            names = [m.group(0).strip() for m in PROJECT_RE.finditer(line)]
            if project_filter and project_filter.casefold() not in line.casefold() and not names:
                continue
            if names or TOTAL_RE.search(line) or UNIT_RE.search(line) or (project_filter and project_filter.casefold() in line.casefold()):
                hits.append({'line': i + 1, 'text': line[:500], 'project_name_hints': names,
                             'numeric_tokens': MONEY_RE.findall(line)[:24],
                             'is_total_row': bool(TOTAL_RE.search(line)),
                             'unit_heading': bool(UNIT_RE.search(line))})
        if hits:
            result.append({'page': page['page'], 'hits': hits})
    return {'mode': 'read_only_review', 'pages_inspected': len(pages), 'pages_with_hits': result,
            'caution': ('Project names, table totals and unit headings are review hints only. '
                        'Do not attribute an amount to a project without verifying the original PDF '
                        'page, row, column, unit and financial meaning.')}

def inspect_pdf(pdf_bytes: bytes, project_filter: str | None = None) -> dict:
    return inspect_pages(extract_pages(pdf_bytes), project_filter)

def main() -> None:
    parser = argparse.ArgumentParser(description='Read-only page-aware PDF review; no database writes')
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--project', default=None, help='Optional project-name text to highlight')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    report = inspect_pdf(args.pdf.read_bytes(), args.project)
    content = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(content + '\n', encoding='utf-8')
        print(f'Wrote review hints to {args.output}')
    else:
        print(content)

if __name__ == '__main__':
    main()

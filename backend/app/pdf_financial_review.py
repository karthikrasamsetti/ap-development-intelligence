"""Read-only reviewer-anchored financial measures from layout-extracted PDF pages.

This module intentionally does not infer row ownership from nearby PDF text.
The reviewer supplies page, source line and measure kind. No database writes.
"""
from __future__ import annotations
import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .pdf_table_review import extract_pages

KINDS = {'approved_project_cost', 'expenditure_incurred', 'tender_ecv', 'agreement_amount'}
NUM = re.compile(r'(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w.])')
MONEY_UNIT = re.compile(r'(?:Rs\.?|INR|₹)\s*(?:in\s*)?lakhs?', re.I)


def line_at(pages: list[dict], page: int, line: int) -> str:
    if not isinstance(page, int) or not isinstance(line, int) or page < 1 or line < 1 or page > len(pages):
        raise ValueError('Invalid page/line number')
    lines = pages[page - 1]['text'].splitlines()
    if line > len(lines):
        raise ValueError('Line outside page')
    return lines[line - 1].strip()


def financial_proposal(pages: list[dict], request: dict) -> dict:
    """Create an unapproved proposal using exact PDF layout line + reviewer input.

    A line may contain several amounts: require an explicit token occurrence index.
    Amount must match exactly, and unit must be separately evidenced.
    """
    kind = request.get('kind')
    if kind not in KINDS:
        raise ValueError('Unknown financial measure kind')
    project = request.get('project')
    if not isinstance(project, str) or len(project.strip()) < 4:
        raise ValueError('Project identity is required')
    page, line = request['page'], request['line']
    excerpt = line_at(pages, page, line)
    matches = list(NUM.finditer(excerpt))
    index = request.get('amount_index')
    if type(index) is not int or not (0 <= index < len(matches)):
        raise ValueError('Explicit amount_index required for selected line')
    raw = matches[index].group()
    try:
        amount_lakh = Decimal(raw.replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('Invalid amount') from exc
    if amount_lakh <= 0:
        raise ValueError('Amount must be positive')
    unit_page, unit_line = request['unit_page'], request['unit_line']
    unit_excerpt = line_at(pages, unit_page, unit_line)
    if not MONEY_UNIT.search(unit_excerpt):
        raise ValueError('Unit line does not explicitly establish Rs in lakhs')
    if unit_page != page:
        raise ValueError('Unit heading must be on the same page as the amount')
    project_page, project_line = request['project_page'], request['project_line']
    project_excerpt = line_at(pages, project_page, project_line)
    if project_page != page or not any(w.casefold() in project_excerpt.casefold() for w in project.split() if len(w) >= 5):
        raise ValueError('Project anchor must identify project on same page')
    # No automated row/column attribution: reviewer must visually verify it.
    if request.get('reviewer_verified_row_and_column') is not True:
        raise ValueError('Reviewer must explicitly confirm row and column visually')
    return {
        'state': 'proposed_unpublished', 'project': project, 'kind': kind,
        'source_page': page, 'source_line': line, 'source_text': excerpt,
        'source_amount_token': raw, 'source_amount_index': index,
        'original_amount_lakh': str(amount_lakh),
        'converted_amount_crore': str(amount_lakh / Decimal('100')),
        'conversion': 'Rs lakh / 100 = Rs crore',
        'unit_evidence': {'page': unit_page, 'line': unit_line, 'text': unit_excerpt},
        'project_anchor': {'page': project_page, 'line': project_line, 'text': project_excerpt},
        'reviewer_verified_row_and_column': True,
        'warning': 'Reviewer-anchored proposal only; no database mutation, no independent corroboration or publication.'
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a read-only financial proposal from a PDF and explicit review coordinates')
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--review', required=True, type=Path, help='JSON object with reviewer-confirmed coordinates')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pages = extract_pages(args.pdf.read_bytes())
    request = json.loads(args.review.read_text(encoding='utf-8'))
    proposal = financial_proposal(pages, request)
    args.output.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote unapproved proposal to {args.output}; database unchanged')


if __name__ == '__main__':
    main()

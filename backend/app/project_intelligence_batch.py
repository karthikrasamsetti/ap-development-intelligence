"""Read-only batch project/financial intelligence from PDF layout text.

Finds project/total *candidates*, never asserts column ownership or modifies DB.
Supports reviewer exports to compare draft investments with approved measures.
"""
from __future__ import annotations
import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .pdf_table_review import extract_pages
from .pdf_financial_review import NUM

PROJECT = re.compile(r'\b(?:MSE\s*[- ]?\s*CDP\s*)?(?:IP|JP)\s*[-–]?\s*([A-Za-z][A-Za-z .-]{2,55})', re.I)
TOTAL = re.compile(r'\btotal\s*:?\s*$', re.I)
UNIT = re.compile(r'(?:Rs\.?|INR|₹)\s*(?:in\s*)?lakhs?', re.I)


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def project_key(name: str) -> str:
    """Candidate grouping key only; not a canonical identity."""
    return re.sub(r'[^a-z0-9]+', '', name.casefold())


def scan_pages(pages: list[dict]) -> dict:
    hits = []
    for page in pages:
        lines = page['text'].splitlines()
        units = [i for i, line in enumerate(lines, 1) if UNIT.search(line)]
        # PDF tables can print the project label *inside* its component block.
        # Consider the nearest surrounding total boundaries but never assign
        # amounts automatically when more than one anchor is plausible.
        totals = [i for i, line in enumerate(lines, 1) if TOTAL.search(line)]
        anchors = []
        for i, line in enumerate(lines, 1):
            m = PROJECT.search(line)
            if m:
                name = norm(m.group(0))
                if len(name) > 70:
                    name = name[:70]
                anchors.append((i, name, norm(line)[:350]))
        for index, (line_no, name, source) in enumerate(anchors):
            before = max((t for t in totals if t < line_no), default=0)
            after = min((t for t in totals if t >= line_no), default=0)
            # Include the line following Total, where PDF layout often places numbers.
            candidate_lines = []
            if after and after + 1 <= len(lines):
                for n in (after, after + 1):
                    tokens = [m.group() for m in NUM.finditer(lines[n-1])]
                    if tokens:
                        candidate_lines.append({'line': n, 'text': norm(lines[n-1])[:500], 'tokens': tokens})
            other_anchors = [a[1] for a in anchors if before < a[0] <= (after or len(lines)) and a[0] != line_no]
            flags = []
            if not units: flags.append('missing_lakh_unit_heading')
            if not after: flags.append('no_following_total')
            if other_anchors: flags.append('multiple_project_anchors_in_block')
            if not candidate_lines: flags.append('no_numeric_total_tokens')
            hits.append({'project_hint': name, 'grouping_key': project_key(name),
                         'page': page['page'], 'project_line': line_no,
                         'project_text': source, 'preceding_total_line': before or None,
                         'following_total_line': after or None,
                         'unit_heading_lines': units[:10], 'total_candidates': candidate_lines,
                         'flags': flags,
                         'review_state': 'needs_visual_row_column_verification'})
    return {'mode': 'read_only_batch_triage', 'project_mentions': len(hits),
            'projects': hits,
            'notice': 'Amounts are unassigned numeric tokens, not financial facts. Do not automatically update candidates, approve evidence, merge projects, or publish.'}


def conflicts(candidates: list[dict], financial_evidence: list[dict]) -> list[dict]:
    """Compare approved project-cost evidence to a candidate draft, no mutations."""
    approved = {}
    for item in financial_evidence:
        if item.get('review_status') == 'approved' and item.get('kind') == 'approved_project_cost':
            approved.setdefault(item.get('candidate_id'), []).append(item)
    out = []
    for candidate in candidates:
        cid = candidate.get('id')
        values = approved.get(cid, [])
        if not values: continue
        try:
            draft = Decimal(str(candidate['investment_inr_crore'])) if candidate.get('investment_inr_crore') is not None else None
            amounts = sorted(set(Decimal(str(v['converted_amount_crore'])) for v in values))
        except (InvalidOperation, KeyError, TypeError):
            out.append({'candidate_id': cid, 'status': 'invalid_numeric_input'})
            continue
        if len(amounts) > 1:
            status = 'conflicting_approved_costs'
        elif draft is None:
            status = 'draft_missing_investment'
        elif draft != amounts[0]:
            status = 'draft_differs_from_approved_cost'
        else:
            status = 'draft_matches_approved_cost'
        out.append({'candidate_id': cid, 'title': candidate.get('title'), 'status': status,
                    'draft_investment_crore': str(draft) if draft is not None else None,
                    'approved_costs_crore': [str(a) for a in amounts],
                    'evidence_ids': [v.get('id') for v in values],
                    'action': 'manual_review_only'})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description='Read-only batch PDF project triage and financial conflicts')
    p.add_argument('pdf', type=Path, nargs='?')
    p.add_argument('--candidates', type=Path)
    p.add_argument('--financial-evidence', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if not args.pdf and not (args.candidates and args.financial_evidence):
        p.error('Provide PDF and/or both candidate and financial evidence JSON files')
    result = {}
    if args.pdf: result['pdf_triage'] = scan_pages(extract_pages(args.pdf.read_bytes()))
    if args.candidates and args.financial_evidence:
        result['financial_conflicts'] = conflicts(json.loads(args.candidates.read_text()), json.loads(args.financial_evidence.read_text()))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Wrote read-only batch report:', args.output)

if __name__ == '__main__': main()

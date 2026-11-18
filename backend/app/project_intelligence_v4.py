"""Read-only, word-geometry-based triage for APIIC MSE-CDP status tables.

This is a document-specific extractor, not a generic PDF table parser. It never
updates a database or upgrades a financial suggestion to verified evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

MONEY = re.compile(r"^\d+(?:,\d{3})*(?:\.\d{1,4})?$")
NAME_PREFIX = re.compile(r"\b(?:MSE\s*[- ]?\s*CDP\s*)?(?:GC|JP|FFC|IP)\b", re.I)


def words_on_page(page):
    return page.extract_words(x_tolerance=1, y_tolerance=2, keep_blank_chars=False)


def physical_rows(words, tolerance=2.3):
    """Group using vertical *centres*, preserving independent word x coordinates."""
    result = []
    for word in sorted(words, key=lambda w: ((w['top'] + w['bottom']) / 2, w['x0'])):
        cy = (word['top'] + word['bottom']) / 2
        if result and abs(result[-1]['y'] - cy) <= tolerance:
            row = result[-1]
            row['words'].append(word)
            row['y'] = sum((w['top'] + w['bottom']) / 2 for w in row['words']) / len(row['words'])
        else:
            result.append({'y': cy, 'words': [word]})
    for row in result:
        row['words'].sort(key=lambda w: w['x0'])
    return result


def _column_text(words, xlo, xhi):
    return ' '.join(w['text'] for w in words if xlo <= w['x0'] < xhi).strip()


def _is_total(row):
    return any(145 <= w['x0'] < 220 and re.fullmatch(r'Total:?', w['text'], re.I) for w in row['words'])


def _money_cell(words, lo, hi):
    candidates = [w for w in words if lo <= w['x0'] < hi and MONEY.fullmatch(w['text'].replace(',', ''))]
    if len(candidates) != 1:
        return None
    w = candidates[0]
    return {'value_lakh': w['text'].replace(',', ''), 'bbox': [round(w[k], 2) for k in ('x0', 'top', 'x1', 'bottom')]}


def _project_identity(rows):
    name_rows = []
    serials = []
    for row in rows:
        nw = [w for w in row['words'] if 35 <= w['x0'] < 94]
        if nw:
            text = ' '.join(w['text'] for w in nw)
            if not re.search(r'\bIP Name\b', text, re.I):
                name_rows.append((row['y'], text))
        for w in row['words']:
            if 18 <= w['x0'] < 35 and w['text'].isdigit() and 1 <= int(w['text']) <= 100:
                serials.append((row['y'], int(w['text'])))
    # The serial and project name are typically vertically centred in merged cells.
    full = ' '.join(text for _, text in name_rows)
    full = re.sub(r'\s+', ' ', full).strip()
    match = NAME_PREFIX.search(full)
    if not match:
        return None
    name = full[match.start():].strip(' -')
    # Only use text from the project-name column, not the component column.
    name = re.sub(r'^MSE\s*[- ]?\s*CDP\s*', '', name, flags=re.I).strip()
    if not name or len(name) < 4:
        return None
    centre = sum(y for y, _ in name_rows) / len(name_rows)
    serial = min(serials, key=lambda x: abs(x[0] - centre))[1] if serials else None
    return {'name': name, 'serial': serial, 'name_rows': name_rows}


def extract_pdf(pdf_path):
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError('Install pdfplumber: pip install pdfplumber') from exc
    projects = []
    diagnostics = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            rows = physical_rows(words_on_page(page))
            totals = [i for i, row in enumerate(rows) if _is_total(row)]
            if not totals:
                diagnostics.append({'page': page_no, 'flag': 'no_total_rows'})
                continue
            previous = -1
            for idx in totals:
                block = rows[previous + 1:idx + 1]
                previous = idx
                ident = _project_identity(block)
                row = rows[idx]
                # The four fields are separate *measured* word positions.
                # Page layout is fixed: GoI x~334, GoAP x~365, total x~382,
                # expenditure x~754. Reject missing/multiple cells.
                cols = {
                    'goi_share': _money_cell(row['words'], 305, 344),
                    'goap_apiic_share': _money_cell(row['words'], 344, 381),
                    'approved_project_cost': _money_cell(row['words'], 381, 416),
                    'expenditure_incurred': _money_cell(row['words'], 744, 799),
                }
                flags = []
                if not ident:
                    flags.append('project_identity_not_found_in_block')
                if any(v is None for v in cols.values()):
                    flags.append('missing_or_ambiguous_financial_cell')
                if all(cols[k] for k in ('goi_share', 'goap_apiic_share', 'approved_project_cost')):
                    a = Decimal(cols['goi_share']['value_lakh'])
                    b = Decimal(cols['goap_apiic_share']['value_lakh'])
                    c = Decimal(cols['approved_project_cost']['value_lakh'])
                    if abs(a + b - c) > Decimal('0.03'):
                        flags.append('share_total_arithmetic_mismatch')
                # We do not claim the project association is independently verified.
                projects.append({
                    'page': page_no,
                    'name': ident['name'] if ident else None,
                    'serial': ident['serial'] if ident else None,
                    'total_row_y': round(row['y'], 2),
                    'total_row_text': _column_text(row['words'], 145, 215),
                    'financial_cells': cols,
                    'flags': flags,
                    'review_state': 'needs_original_pdf_confirmation',
                })
    return {
        'version': 4,
        'mode': 'read_only_word_geometry',
        'source_file': Path(pdf_path).name,
        'pages_inspected': len(pdf.pages),
        'projects': projects,
        'diagnostics': diagnostics,
        'verified_financial_assignments': 0,
        'safety': 'Geometry-based candidates only. No DB writes, auto-approval, or publication.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf')
    parser.add_argument('--output', default='mse-v4-review.json')
    args = parser.parse_args()
    report = extract_pdf(args.pdf)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote {len(report['projects'])} read-only project rows to {args.output}")


if __name__ == '__main__':
    main()

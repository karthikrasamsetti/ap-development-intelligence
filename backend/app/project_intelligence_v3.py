"""APDI v3: geometry-aware, read-only PDF financial review.

Coordinates and inferred table cells are *hints*, not verified claims. No DB writes.
"""
from __future__ import annotations
import argparse
import json
import re
from io import BytesIO
from pathlib import Path

MAX_BYTES = 15_000_000
MAX_PAGES = 40

NUMBER = re.compile(r'(?<![\w.])(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}(?![\w.])')
PROJECT = re.compile(r'^\s*(?:(\d{1,2})\s+)?(?:(?:MSE\s*[- ]?\s*CDP)\s+)?((?:IP|JP)\s*[-–]?\s*[A-Za-z][A-Za-z-]{2,35})\b', re.I)
HEADER = re.compile(r'\bIP\s+Name\s+Letter\s+No\b', re.I)
COMPONENT = re.compile(r'^(?:water|roads?|drains?|storm|power|culverts?|building|contingenc|greenery|administrative|harvesting)\b', re.I)
TOTAL = re.compile(r'\btotal\s*:', re.I)
LABELS = ('goi', 'goap', 'apiic', 'total', 'expenditure', 'spent', 'incurred')


def normalized_name(s):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\b(?:mse|cdp)\b', '', s.lower()))


def project_anchor(text):
    if HEADER.search(text):
        return None
    match = PROJECT.search(text)
    if not match:
        return None
    name = re.sub(r'\s+', ' ', match.group(2)).strip()
    tail = text[match.end():].strip()
    if COMPONENT.search(name.split(' ', 1)[-1].lstrip('- ')) or COMPONENT.match(tail):
        return None
    # Reject 'IP- Water Harvesting' and other component prefixes.
    if COMPONENT.match(re.sub(r'^(?:IP|JP)\s*[-–]?\s*', '', name, flags=re.I)):
        return None
    return {'name': name, 'identity_hint': normalized_name(name), 'serial': int(match.group(1)) if match.group(1) else None}


def group_fragments(fragments, y_tolerance=3.5):
    """Group text fragments by physical baseline, then order by horizontal position."""
    lines = []
    for f in sorted(fragments, key=lambda x: (-x['y'], x['x'])):
        match = next((line for line in lines if abs(line['y'] - f['y']) <= y_tolerance), None)
        if match is None:
            match = {'y': f['y'], 'fragments': []}
            lines.append(match)
        match['fragments'].append(f)
    for line in lines:
        line['fragments'].sort(key=lambda f: f['x'])
        line['text'] = ' '.join(f['text'] for f in line['fragments'])
    return sorted(lines, key=lambda line: -line['y'])


def extract_geometry(pdf_bytes):
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError('PDF exceeds inspection byte limit')
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    if len(reader.pages) > MAX_PAGES:
        raise ValueError('PDF exceeds inspection page limit')
    output = []
    for page_number, page in enumerate(reader.pages, 1):
        fragments = []
        def visit(text, cm, tm, font_dict, font_size):
            # Text matrix is transformed by the current transformation matrix.
            # pypdf visitor coordinates are approximate for complex PDFs.
            if not text or not text.strip():
                return
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            for part in text.splitlines():
                part = part.strip()
                if part:
                    fragments.append({'x': round(float(x), 2), 'y': round(float(y), 2), 'text': part[:350], 'font_size': round(float(font_size), 2)})
        page.extract_text(visitor_text=visit)
        output.append({'page': page_number, 'width': float(page.mediabox.width), 'height': float(page.mediabox.height), 'lines': group_fragments(fragments)})
    return output


def report_geometry(pages):
    """Offer bounded row candidates, never assign financial meanings automatically."""
    result = []
    anchors = []
    for page in pages:
        for idx, line in enumerate(page['lines']):
            a = project_anchor(line['text'])
            if a:
                anchors.append({**a, 'page': page['page'], 'line_index': idx, 'y': line['y'], 'anchor_text': line['text'][:300]})
    for i, anchor in enumerate(anchors):
        next_anchor = anchors[i + 1] if i + 1 < len(anchors) else None
        page_items = []
        for page in pages:
            if page['page'] < anchor['page'] or (next_anchor and page['page'] > next_anchor['page']):
                continue
            start = anchor['line_index'] if page['page'] == anchor['page'] else 0
            end = next_anchor['line_index'] if next_anchor and page['page'] == next_anchor['page'] else len(page['lines'])
            for index in range(start, end):
                line = page['lines'][index]
                if not TOTAL.search(line['text']):
                    continue
                nearby = page['lines'][index:min(end, index + 3)]
                cells = []
                for row in nearby:
                    for frag in row['fragments']:
                        for match in NUMBER.finditer(frag['text']):
                            cells.append({'text': match.group(), 'x': frag['x'], 'y': frag['y'], 'position_estimated': len(NUMBER.findall(frag['text'])) > 1})
                if cells:
                    page_items.append({'page': page['page'], 'line_index': index, 'y': line['y'], 'row_text': line['text'][:450], 'numeric_cells': cells[:32], 'financial_kind': 'unassigned', 'column_verified': False, 'project_verified': False})
        flags = []
        if anchor['serial'] is None:
            flags.append('unnumbered_project_anchor')
        if not page_items:
            flags.append('no_total_row_detected')
        if len(page_items) > 1:
            flags.append('multiple_totals_require_row_review')
        if next_anchor and next_anchor['page'] > anchor['page']:
            flags.append('cross_page_boundary_inferred')
        flags.append('geometry_requires_visual_verification')
        result.append({**anchor, 'total_candidates': page_items, 'flags': flags, 'review_state': 'unverified'})
    return {'version': 3, 'mode': 'read_only_geometry_triage', 'pages_inspected': len(pages), 'project_anchors': len(result), 'projects': result, 'verified_financial_assignments': 0, 'safety': 'No financial attribution, candidate update, database write, merge, approval or publication. Inspect the original PDF visually.'}


def main():
    p = argparse.ArgumentParser(description='Geometry-aware APDI PDF review; no database writes')
    p.add_argument('pdf', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = report_geometry(extract_geometry(args.pdf.read_bytes()))
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote read-only geometry review: {args.output} ({report['project_anchors']} anchors)")

if __name__ == '__main__':
    main()

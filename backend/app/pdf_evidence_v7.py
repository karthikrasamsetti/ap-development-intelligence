"""Ephemeral evidence suggestions from PDF geometry; physical row ordinals, not canonical PDF text lines."""
from decimal import Decimal
from .project_intelligence_v4 import words_on_page, physical_rows


def enrich_report(report, pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for project in report['projects']:
            page_number = project['page']
            rows = physical_rows(words_on_page(pdf.pages[page_number - 1]))
            total_y = project['total_row_y']
            total_index = min(range(len(rows)), key=lambda i: abs(rows[i]['y'] - total_y))
            total = rows[total_index]
            total_text = ' '.join(w['text'] for w in total['words'])
            header = next(((i, r) for i, r in enumerate(rows[:total_index]) if '(Rs.' in ' '.join(w['text'] for w in r['words']) and 'Lakhs' in ' '.join(w['text'] for w in r['words'])), None)
            previous_total = max((i for i in range(total_index) if any(145 <= w['x0'] < 220 and w['text'].lower().rstrip(':') == 'total' for w in rows[i]['words'])), default=12)
            identity = [(i, ' '.join(w['text'] for w in rows[i]['words'] if 35 <= w['x0'] < 94)) for i in range(previous_total + 1, total_index) if any(35 <= w['x0'] < 94 for w in rows[i]['words'])]
            identity = [(i, text) for i, text in identity if text.strip()]
            anchor = max(identity, key=lambda t: len(t[1]), default=None)
            prepared = {}
            for kind in ('approved_project_cost', 'expenditure_incurred'):
                cell = project['financial_cells'].get(kind)
                if not cell or not header or not anchor:
                    prepared[kind] = {'ready': False, 'reason': 'Missing amount, project identity or unit header in page geometry'}
                    continue
                token = cell['value_lakh']
                if not any(w['text'].replace(',', '') == token and abs(w['x0'] - cell['bbox'][0]) < 1 for w in total['words']):
                    prepared[kind] = {'ready': False, 'reason': 'Amount token cannot be uniquely traced to source row'}
                    continue
                prepared[kind] = {
                    'ready': True, 'source_page': page_number,
                    'source_line': total_index + 1, 'source_text': total_text,
                    'source_amount_index': 0, 'source_amount_token': token,
                    'project_anchor': {'page': page_number, 'line': anchor[0] + 1, 'text': anchor[1]},
                    'unit_evidence': {'page': page_number, 'line': header[0] + 1, 'text': ' '.join(w['text'] for w in header[1]['words'])},
                    'coordinate_system': 'pdfplumber physical-row ordinal (1-based, page-local); not canonical PDF text line',
                    'source_bbox': cell['bbox'],
                    'original_amount_lakh': token,
                    'converted_amount_crore': str(Decimal(token) / Decimal('100')),
                }
            project['prepared_evidence'] = prepared
    return report

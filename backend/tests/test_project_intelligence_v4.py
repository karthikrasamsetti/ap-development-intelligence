"""Regression checks against the actual APIIC document, when supplied via APDI_TEST_PDF."""
import os
from pathlib import Path
from app.project_intelligence_v4 import extract_pdf, physical_rows, _money_cell


def test_physical_words_keep_individual_coordinates():
    rows = physical_rows([
        {'text':'100','x0':10,'x1':20,'top':10,'bottom':15},
        {'text':'200','x0':40,'x1':50,'top':10,'bottom':15},
    ])
    assert len(rows) == 1
    assert _money_cell(rows[0]['words'], 0, 30)['bbox'][0] == 10
    assert _money_cell(rows[0]['words'], 30, 60)['bbox'][0] == 40


def test_ambiguous_cell_rejected():
    words = [{'text':t,'x0':10,'x1':20,'top':10,'bottom':15} for t in ('100','200')]
    assert _money_cell(words, 0, 30) is None


def test_apiic_real_pdf_regressions():
    path = os.environ.get('APDI_TEST_PDF')
    if not path or not Path(path).is_file():
        return  # Real-document regression is optional for normal CI environments.
    report = extract_pdf(path)
    assert len(report['projects']) == 21
    by_serial = {p['serial']:p for p in report['projects']}
    expected = {
        8: ('Gopavaram', '1525.49', '294.75'),
        9: ('Guttapadu', '2140.00', '1020.10'),
        10: ('Jagadurthy', '1045.99', '413.22'),
        12: ('Chandaluru', '1076.41', '391.06'),
        14: ('Pagali', '1030.00', '0.00'),
        16: ('Koduru', '2686.00', '1282.00'),
    }
    for serial, (name, approved, spent) in expected.items():
        project = by_serial[serial]
        assert name.lower() in project['name'].lower()
        assert project['financial_cells']['approved_project_cost']['value_lakh'] == approved
        assert project['financial_cells']['expenditure_incurred']['value_lakh'] == spent
        assert project['flags'] == []
    assert report['verified_financial_assignments'] == 0

import os
import pytest
from decimal import Decimal
from app.project_intelligence_v4 import extract_pdf
from app.pdf_evidence_v7 import enrich_report


def test_v7_real_pdf_gopavaram_and_guttapadu():
    pdf = os.environ.get('APDI_TEST_PDF')
    if not pdf or not os.path.exists(pdf):
        pytest.skip('APDI_TEST_PDF not set')
    report = enrich_report(extract_pdf(pdf), pdf)
    assert len(report['projects']) == 21
    for serial, token, crore in [(8, '1525.49', '15.2549'), (9, '2140.00', '21.4')]:
        project = next(p for p in report['projects'] if p['serial'] == serial)
        evidence = project['prepared_evidence']['approved_project_cost']
        assert evidence['ready']
        assert evidence['source_page'] == 5
        assert token in evidence['source_text']
        assert Decimal(evidence['converted_amount_crore']) == Decimal(crore)
        assert 'lakh' in evidence['unit_evidence']['text'].lower()
        assert 'Gopavaram' in evidence['project_anchor']['text'] or 'Guttapadu' in evidence['project_anchor']['text']
        assert evidence['coordinate_system'].startswith('pdfplumber physical-row')


def test_v7_all_prepared_amounts_retrace_source():
    pdf = os.environ.get('APDI_TEST_PDF')
    if not pdf or not os.path.exists(pdf):
        pytest.skip('APDI_TEST_PDF not set')
    report = enrich_report(extract_pdf(pdf), pdf)
    for p in report['projects']:
        for kind, evidence in p['prepared_evidence'].items():
            if evidence['ready']:
                assert evidence['source_amount_token'] in evidence['source_text']
                assert evidence['source_line'] > 0
                assert evidence['project_anchor']['line'] > 0
                assert evidence['unit_evidence']['line'] > 0

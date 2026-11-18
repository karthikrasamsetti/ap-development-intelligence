from decimal import Decimal
from types import SimpleNamespace
from app.review_checks import similar_names, numeric_supported, field_warnings

def test_duplicate_title_vs_paragraph():
    assert similar_names('Donakonda Mega Industrial Hub', 'Donakonda Mega Industrial Hub The proposed Donakonda Mega Industrial Hub is envisioned as a large project')

def test_numeric_mismatch_rejected():
    assert not numeric_supported(4500, '₹297 crore investment', '₹297 crore investment', 'investment')
    assert numeric_supported(4500, '₹4,500 crore investment', '₹4,500 crore investment', 'investment')
    assert not numeric_supported(1950, '₹297 crore investment', '₹297 crore investment', 'jobs')
    assert numeric_supported(1950, '1,950 jobs expected', '1,950 jobs expected', 'jobs')

def test_unknown_status_blocked():
    c = SimpleNamespace(evidence_quote='Example source passage', field_evidence='{}', investment_inr_crore=None, expected_jobs=None, jobs_created=None, status='unknown', district=None, extraction_method='llm')
    assert any('unknown' in x for x in field_warnings(c, 'Example source passage'))

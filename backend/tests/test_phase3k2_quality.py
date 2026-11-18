from types import SimpleNamespace
from app.review_checks import similar_names, duplicate_suggestions, numeric_supported, title_warnings, field_warnings


def test_distinct_mse_cdp_parks_not_duplicates():
    assert not similar_names('MSE CDP IP-Guttapadu', 'MSE-CDP IP-Guntur')
    assert not similar_names('MSE CDP IP-Guttapadu', 'MSE CDP IP-Tanuku')
    assert not similar_names('MSE CDP IP-Guttapadu', 'MSE CDP IP Thatiguntapalli')


def test_real_identity_match():
    assert similar_names('MSE CDP IP-Guttapadu', 'MSE-CDP IP Guttapadu')
    assert similar_names('Donakonda Mega Industrial Hub', 'Donakonda Industrial Hub')


def test_duplicate_suggestions_exclude_other_parks():
    c = SimpleNamespace(id=29, title='MSE CDP IP-Guttapadu', review_status='draft')
    others = [SimpleNamespace(id=19, title='MSE CDP IP-Guntur', review_status='draft'),
              SimpleNamespace(id=30, title='MSE-CDP IP Guttapadu', review_status='draft')]
    assert [r['id'] for r in duplicate_suggestions(c, others)] == [30]


def test_investment_explicit_units_and_conversions():
    for quote, value in [('Investment 13.79 crore', 13.79), ('₹1 lakh crore', 100000), ('Investment INR 13.79 Cr', 13.79)]:
        assert numeric_supported(value, quote, quote, 'investment')
    assert not numeric_supported(13.79, 'Investment 12.5 crore', 'Investment 12.5 crore', 'investment')


def test_table_headings_conservative():
    q = 'Investment (₹ crore) 13.79'
    assert numeric_supported(13.79, q, q, 'investment')
    assert not numeric_supported(13.79, 'Investment (₹ crore) 13.79 17.25', 'Investment (₹ crore) 13.79 17.25', 'investment')
    assert not numeric_supported(13.79, '13.79', '13.79', 'investment')


def test_jobs_and_source_anchor():
    q = 'Expected employment 1,950 jobs'
    assert numeric_supported(1950, q, q, 'jobs')
    assert not numeric_supported(1950, q, 'different source', 'jobs')


def test_title_quality():
    assert title_warnings('With an estimated investment exceeding 1 lakh crore, the project represents one of the largest investments')
    assert title_warnings('MSE-CDP Hindupur1')
    assert not title_warnings('MSE CDP IP-Guttapadu')


def test_field_warnings_non_mutating():
    q = 'MSE CDP IP-Guttapadu grounded. Investment 13.79 crore.'
    c = SimpleNamespace(title='MSE CDP IP-Guttapadu', evidence_quote=q,
        investment_inr_crore=13.79, expected_jobs=None, jobs_created=None,
        status='grounded', district=None, extraction_method='llm',
        field_evidence='{"investment_evidence":"Investment 13.79 crore", "status_evidence":"grounded"}')
    assert field_warnings(c, q) == []
    assert c.investment_inr_crore == 13.79

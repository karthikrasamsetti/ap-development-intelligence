import pytest
from app.pdf_financial_review import financial_proposal

PAGES = [{'page': 1, 'text': 'STATUS OF ONGOING MSE CDP PROJECTS\nTotal (Rs. in Lakhs)\n9 MSE CDP IP-Guttapadu\nTotal 1050.00 1090.00 2140.00 1020.10\n10 MSE CDP IP-Jagadurthy'}]
BASE = {'project': 'MSE CDP IP-Guttapadu', 'kind': 'approved_project_cost', 'page': 1, 'line': 4, 'amount_index': 2, 'unit_page': 1, 'unit_line': 2, 'project_page': 1, 'project_line': 3, 'reviewer_verified_row_and_column': True}

def test_approved_cost_conversion():
    result = financial_proposal(PAGES, BASE)
    assert result['converted_amount_crore'] == '21.40'
    assert result['state'] == 'proposed_unpublished'

def test_expenditure_is_distinct():
    result = financial_proposal(PAGES, {**BASE, 'kind': 'expenditure_incurred', 'amount_index': 3})
    assert result['converted_amount_crore'] == '10.201'
    assert result['kind'] == 'expenditure_incurred'

def test_requires_reviewer_confirmation():
    with pytest.raises(ValueError, match='Reviewer'):
        financial_proposal(PAGES, {**BASE, 'reviewer_verified_row_and_column': False})

def test_rejects_missing_unit():
    with pytest.raises(ValueError, match='Unit line'):
        financial_proposal(PAGES, {**BASE, 'unit_line': 1})

def test_rejects_wrong_project_anchor():
    with pytest.raises(ValueError, match='Project anchor'):
        financial_proposal(PAGES, {**BASE, 'project_line': 5})

def test_rejects_missing_amount_index():
    with pytest.raises(ValueError, match='amount_index'):
        financial_proposal(PAGES, {k: v for k, v in BASE.items() if k != 'amount_index'})

def test_rejects_out_of_bounds_line():
    with pytest.raises(ValueError, match='Line outside'):
        financial_proposal(PAGES, {**BASE, 'line': 50})

def test_rejects_unknown_measure():
    with pytest.raises(ValueError, match='Unknown'):
        financial_proposal(PAGES, {**BASE, 'kind': 'investment'})

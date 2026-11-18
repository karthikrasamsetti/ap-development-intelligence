from decimal import Decimal
from app.pdf_review_v6_api import compare_amounts

def test_guttapadu_draft_difference_is_not_silent_correction():
    r=compare_amounts('2140.00', Decimal('13.79'), [])
    assert r['pdf_approved_cost_crore']=='21.40'
    assert r['draft_comparison']=='different_measure_review_required'
    assert not r['approved_cost_conflict']

def test_existing_approved_evidence_preserved():
    evidence=[{'id':1,'kind':'approved_project_cost','review_status':'approved','converted_amount_crore':'21.400000'}]
    r=compare_amounts('2140.00',None,evidence)
    assert not r['approved_cost_conflict']
    assert r['approved_cost_evidence']==evidence

def test_conflicting_approved_amount_flagged():
    evidence=[{'id':1,'kind':'approved_project_cost','review_status':'approved','converted_amount_crore':'13.79'}]
    assert compare_amounts('2140',None,evidence)['approved_cost_conflict']

def test_different_kind_does_not_count_as_approved_cost():
    evidence=[{'id':1,'kind':'expenditure_incurred','review_status':'approved','converted_amount_crore':'10.201'}]
    assert not compare_amounts('2140',None,evidence)['approved_cost_conflict']

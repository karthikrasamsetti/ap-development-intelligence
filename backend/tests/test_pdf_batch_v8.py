from app.pdf_batch_v8_api import classify

def test_batch_status_priority():
    r=[{'kind':'approved_project_cost','review_status':'proposed'},{'kind':'approved_project_cost','review_status':'approved'}]
    assert classify(r,'approved_project_cost')=='approved'
    assert classify(r,'expenditure_incurred')=='needs_review'

def test_pending_and_rejected():
    assert classify([{'kind':'approved_project_cost','review_status':'proposed'}],'approved_project_cost')=='pending'
    assert classify([{'kind':'approved_project_cost','review_status':'rejected'}],'approved_project_cost')=='needs_review'

from datetime import datetime, timezone
from types import SimpleNamespace
from app.cross_source import compare_evidence, validate_observations, valid_quote

def row(i,key,url,quote,amount=None,status=None):
    snap=SimpleNamespace(id=i,source_key=key,url=url,body_text=quote,fetched_at=datetime.now(timezone.utc))
    return SimpleNamespace(id=i,snapshot=snap,quote=quote,source_date=None,observed_status=status,
        observed_investment_inr_crore=amount,observed_expected_jobs=None,observed_jobs_created=None)

def test_one_source_not_corroborated():
    assert not compare_evidence([row(1,'a','https://a.gov.in','A project investment is ₹100 crore')])['corroborated']

def test_distinct_keys_and_urls_required():
    a=row(1,'a','https://a.gov.in','Investment is ₹100 crore')
    b=row(2,'a','https://b.gov.in','Investment is ₹100 crore')
    c=row(3,'b','https://a.gov.in','Investment is ₹100 crore')
    assert not compare_evidence([a,b])['corroborated']
    assert not compare_evidence([a,c])['corroborated']
    assert compare_evidence([a,row(4,'b','https://b.gov.in','Investment is ₹100 crore')])['corroborated']

def test_conflicting_amounts_detected():
    a=row(1,'a','https://a.gov.in','Investment is ₹100 crore',100)
    b=row(2,'b','https://b.gov.in','Investment is ₹200 crore',200)
    result=compare_evidence([a,b]); assert result['corroborated']
    assert result['conflicts'][0]['field']=='observed_investment_inr_crore'

def test_invalid_quote_not_counted():
    a=row(1,'a','https://a.gov.in','A project has investment ₹100 crore')
    b=row(2,'b','https://b.gov.in','A project has investment ₹100 crore')
    b.quote='Not in the source snapshot body at all'
    assert not compare_evidence([a,b])['corroborated']

def test_unsupported_numbers_and_status():
    assert validate_observations('The investment is ₹100 crore',investment=200)
    assert validate_observations('The project was proposed',status='operational')
    assert not validate_observations('The project was approved with ₹100 crore investment',investment=100,status='approved')

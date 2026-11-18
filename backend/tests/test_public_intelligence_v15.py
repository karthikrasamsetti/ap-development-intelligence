from datetime import datetime, timezone
from types import SimpleNamespace
from app.public_intelligence_api import safe_link, verified_item, unverified_item

def test_url_safety():
    assert safe_link('javascript:alert(1)') is None
    assert safe_link('https://example.org/report') == 'https://example.org/report'

def test_unverified_hides_unreviewed_numeric_claims():
    candidate = SimpleNamespace(id=7,title='Draft project',summary='Claim awaiting review',category='investment',district='Guntur',sector='Industry',status='announced',investment_inr_crore=9999,expected_jobs=12345,jobs_created=999,created_at=datetime.now(timezone.utc))
    snap = SimpleNamespace(source_name='Official portal',url='https://example.org',fetched_at=datetime.now(timezone.utc))
    item = unverified_item(candidate,snap)
    assert item['verification'] == 'unverified_ai_extraction'
    assert item['investment_inr_crore'] is None and item['expected_jobs'] is None and item['jobs_created'] is None
    assert item['source_published_on'] is None

def test_verified_keeps_source_date_and_measures():
    source=SimpleNamespace(title='Publisher',url='https://example.org',published_on=None)
    row=SimpleNamespace(id='x',title='Published',summary='Summary',category='investment',district='Kakinada',sector='Industry',status='grounded',investment_inr_crore=42,expected_jobs=100,jobs_created=5,created_at=datetime.now(timezone.utc),source=source)
    item=verified_item(row)
    assert item['verification']=='verified' and item['jobs_created']==5
    assert item['source_published_on'] is None

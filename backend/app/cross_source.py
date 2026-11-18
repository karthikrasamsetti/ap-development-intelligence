"""Deterministic, conservative cross-source verification helpers.

Independent means different source keys AND URLs, not independent journalism.
No claim is factually verified merely because two pages contain a quote.
"""
from collections import defaultdict
from decimal import Decimal
from urllib.parse import urlsplit
from .review_checks import numeric_supported

FIELDS = ('observed_investment_inr_crore','observed_expected_jobs','observed_jobs_created','observed_status')
STATUS_ORDER = ('announced','mou_signed','approved','grounded','operational')

def valid_quote(snapshot_text, quote):
    return bool(quote and len(quote.strip()) >= 15 and quote.strip() in (snapshot_text or ''))

def validate_observations(quote, investment=None, expected_jobs=None, jobs_created=None, status=None):
    problems=[]
    for label, value, kind in (('investment',investment,'investment'),('expected jobs',expected_jobs,'jobs'),('actual jobs',jobs_created,'jobs')):
        if value is not None and not numeric_supported(value,quote,quote,kind):
            problems.append(f'{label} not supported by exact quote')
    if status and status != 'unknown':
        import re
        # Exact matching status language is intentionally conservative.
        terms={'announced':r'announc', 'mou_signed':r'\b(?:mou|memorandum of understanding|signed)\b',
            'approved':r'approv', 'grounded':r'\b(?:groundbreak|groundbreaking|construction started|work commenced)\b',
            'operational':r'\b(?:operational|commissioned|inaugurated)\b',
            'delayed':r'delay', 'cancelled':r'cancel'}
        if status not in terms or not re.search(terms[status],quote,re.I):
            problems.append('status lacks explicit supporting language')
    return problems

def compare_evidence(rows):
    """rows: evidence objects with .snapshot relationship. Returns conflicts and coverage."""
    by_field=defaultdict(list)
    keys=set(); urls=set(); timeline=[]
    for row in rows:
        snap=row.snapshot
        if not valid_quote(snap.body_text,row.quote):
            continue
        keys.add(snap.source_key); urls.add(snap.url)
        timeline.append({'evidence_id':row.id,'snapshot_id':snap.id,'source_key':snap.source_key,
            'url':snap.url,'source_date':row.source_date.isoformat() if row.source_date else None,
            'fetched_at':snap.fetched_at.isoformat() if snap.fetched_at else None,
            'status':row.observed_status,'investment_inr_crore':float(row.observed_investment_inr_crore) if row.observed_investment_inr_crore is not None else None,
            'expected_jobs':row.observed_expected_jobs,'jobs_created':row.observed_jobs_created})
        for field in FIELDS:
            value=getattr(row,field)
            if value is not None and value != 'unknown':
                by_field[field].append((str(value),snap.id))
    conflicts=[]
    for field, entries in by_field.items():
        unique={v for v,_ in entries}
        if len(unique)>1:
            conflicts.append({'field':field,'observations':[{'value':v,'snapshot_id':sid} for v,sid in entries],
                'note':'Different reported values or stages; review chronology and definitions before publication'})
    timeline.sort(key=lambda x:(x['source_date'] or x['fetched_at'] or '',x['snapshot_id']))
    return {'valid_source_keys':len(keys),'valid_source_urls':len(urls),'corroborated':len(keys)>=2 and len(urls)>=2,
            'conflicts':conflicts,'timeline':timeline,
            'note':'Corroborated here means two distinct registered source keys and URLs, not proven factual independence.'}

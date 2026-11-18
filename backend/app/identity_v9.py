"""Pure advisory matching and evidence comparison; no database mutations."""
import re
from decimal import Decimal, InvalidOperation

STOP={'mse','cdp','ip','jp','gc','ffc','project','projects','phase','block','development','industrial','park','cluster'}
def normalize(value):
    value=re.sub(r'(?<=\D)(?=\d)|(?<=\d)(?=\D)', ' ', value.lower())
    return [x for x in re.findall(r'[a-z]+|\d+',value) if x not in STOP and not x.isdigit()]

def suggest(project, candidates):
    target=set(normalize(project))
    if not target:return []
    out=[]
    for candidate in candidates:
        tokens=set(normalize(candidate['title']))
        if not tokens:continue
        overlap=target & tokens
        if overlap and len(overlap)==len(target) and len(overlap)==len(tokens):
            out.append({'candidate_id':candidate['candidate_id'],'title':candidate['title'],'reason':'normalized exact name; verify project identity'})
    return out

def compare_cost(pdf_lakh, records):
    try: pdf=Decimal(str(pdf_lakh))/Decimal(100)
    except InvalidOperation:return 'invalid'
    approved=[r for r in records if r.get('kind')=='approved_project_cost' and r.get('review_status')=='approved']
    if not approved:return 'no_approved'
    try: values=[Decimal(str(r['converted_amount_crore'])) for r in approved]
    except (InvalidOperation,KeyError):return 'invalid'
    return 'match' if all(v==pdf for v in values) else 'conflict'

"""Conservative, deterministic LangGraph evidence extraction.

No LLM calls, invented values, or auto-publication. A page is not a project.
Candidate spans must appear verbatim in the saved snapshot. Each candidate
needs manual correction and confirmation before publication.
"""
import hashlib
import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import IngestionSnapshot, ReviewCandidate

# Require an explicit project-like phrase and an action; generic portal copy is skipped.
SUBJECT = re.compile(r'\b(?:project|plant|facility|industrial park|industrial corridor|port|airport|highway|manufacturing unit|factory|solar park|wind farm|data cent(?:er|re)|investment|MoU|memorandum of understanding)\b', re.I)
ACTION = re.compile(r'\b(?:announced|proposed|approved|signed|commissioned|inaugurated|launched|established|developing|developed|invest(?:ed|ment)|construction|set up|setting up|groundbreaking)\b', re.I)
DISTRICTS = ('Alluri Sitharama Raju','Anakapalli','Anantapur','Annamayya','Bapatla','Chittoor','Dr. B.R. Ambedkar Konaseema','East Godavari','Eluru','Guntur','Kakinada','Krishna','Kurnool','Markapuram','Nandyal','NTR','Palnadu','Parvathipuram Manyam','Polavaram','Prakasam','Sri Potti Sriramulu Nellore','Sri Sathya Sai','Srikakulam','Tirupati','Visakhapatnam','Vizianagaram','West Godavari','YSR Kadapa')

class State(TypedDict):
    text: str
    spans: list[str]
    claims: list[dict]

def split_spans(state: State):
    # Avoid splitting decimals, and preserve exact substrings for auditability.
    text=state['text'][:200000]
    chunks=re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])|\n+',text)
    spans=[x.strip() for x in chunks if 45<=len(x.strip())<=1200]
    return {'spans':spans}

def identify(state: State):
    claims=[]
    for span in state['spans']:
        if not (SUBJECT.search(span) and ACTION.search(span)):
            continue
        # No guessed financial values, jobs, statuses or companies.
        district=next((d for d in DISTRICTS if re.search(r'(?<!\w)'+re.escape(d)+r'(?!\w)',span,re.I)),None)
        category='investment' if re.search(r'\b(?:investment|invested|MoU|manufacturing unit|factory|plant)\b',span,re.I) else 'infrastructure'
        claims.append({'title':span[:190], 'summary':span[:1200], 'evidence_quote':span[:1200], 'district':district, 'category':category})
    # Limit review noise, not a comprehensive extraction guarantee.
    return {'claims':claims[:12]}

def validate(state: State):
    return {'claims':[c for c in state['claims'] if c['evidence_quote'] in state['text'] and len(c['evidence_quote'])>=45]}

builder=StateGraph(State)
builder.add_node('split',split_spans)
builder.add_node('identify',identify)
builder.add_node('validate',validate)
builder.add_edge(START,'split');builder.add_edge('split','identify');builder.add_edge('identify','validate');builder.add_edge('validate',END)
graph=builder.compile()

def extract_snapshot(db:Session, snapshot_id:int):
    snap=db.get(IngestionSnapshot,snapshot_id)
    if not snap: raise ValueError('Snapshot not found')
    output=graph.invoke({'text':snap.body_text,'spans':[],'claims':[]})
    created=0;existing=0
    for c in output['claims']:
        fingerprint=hashlib.sha256(f'{snapshot_id}\0{c["evidence_quote"]}'.encode()).hexdigest()
        if db.scalar(select(ReviewCandidate.id).where(ReviewCandidate.extraction_fingerprint==fingerprint)):
            existing+=1;continue
        db.add(ReviewCandidate(snapshot_id=snapshot_id,extraction_fingerprint=fingerprint,title=c['title'],summary=c['summary'],category=c['category'],district=c['district'],sector=None,status='announced',investment_inr_crore=None,expected_jobs=None,jobs_created=None,evidence_quote=c['evidence_quote'],review_status='draft'))
        created+=1
    db.commit()
    return {'snapshot_id':snapshot_id,'matched_spans':len(output['claims']),'created':created,'already_present':existing,'notice':'Heuristic suggestions only. All fields and supporting evidence require human review. Nothing published.'}

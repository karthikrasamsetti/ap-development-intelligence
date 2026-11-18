"""Admin-controlled discovery approval, ingestion, and explicit extraction."""
import os
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .db import get_db
from .models import DiscoveryProposal,DiscoveryEvent
from .review_api import admin_auth
from .source_monitor import registry
from .discovery import scan,ingest,utcnow
from .discovery_relevance import assess, duplicate_hints

router=APIRouter(prefix='/api/v1/admin/discovery',tags=['discovery'],dependencies=[Depends(admin_auth)])
class Decision(BaseModel):
    reason:str=''

@router.get('/registry')
def sources(): return [{'key':s['key'],'name':s['name'],'url':s['url']} for s in registry()]

@router.post('/scan/{source_key}')
def scan_one(source_key:str,db:Session=Depends(get_db)):
    try: return scan(db,source_key)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        db.rollback(); raise HTTPException(502,f'Scan failed ({type(exc).__name__})') from exc

@router.get('/proposals')
def proposals(db:Session=Depends(get_db)):
    rows=db.scalars(select(DiscoveryProposal).order_by(DiscoveryProposal.id.desc()).limit(300)).all()
    return [{'id':r.id,'parent_source_key':r.parent_source_key,'url':r.url,'title':r.title,'status':r.status,'last_snapshot_id':r.last_snapshot_id,'created_at':r.created_at} for r in rows]

def decide(proposal_id:int, decision:str, body:Decision, db:Session):
    p=db.get(DiscoveryProposal,proposal_id)
    if not p: raise HTTPException(404,'Proposal not found')
    if p.status!='proposed': raise HTTPException(409,'Proposal already reviewed')
    p.status='approved' if decision=='approve' else 'rejected'
    db.add(DiscoveryEvent(proposal_id=p.id,action=p.status,detail=body.reason[:500],created_at=utcnow()))
    db.commit()
    return {'id':p.id,'status':p.status}

@router.get('/triage')
def triage(db:Session=Depends(get_db)):
    """Read-only ranking for the same latest 300 proposals as /proposals."""
    rows=db.scalars(select(DiscoveryProposal).order_by(DiscoveryProposal.id.desc()).limit(300)).all()
    hints=duplicate_hints(rows)
    items=[]
    for p in rows:
        item=assess(p.title,p.url)
        item.update({'id':p.id,'similar_title_proposal_ids':hints.get(p.id,[])[:10]})
        items.append(item)
    return {'items':items,'scoring_version':'rules-v1','note':'Ranking is advisory; human approval remains mandatory.'}

@router.post('/proposals/{proposal_id}/approve')
def approve_one(proposal_id:int, body:Decision, db:Session=Depends(get_db)):
    return decide(proposal_id,'approve',body,db)

@router.post('/proposals/{proposal_id}/reject')
def reject_one(proposal_id:int, body:Decision, db:Session=Depends(get_db)):
    return decide(proposal_id,'reject',body,db)

@router.post('/proposals/{proposal_id}/ingest')
def ingest_one(proposal_id:int,db:Session=Depends(get_db)):
    p=db.get(DiscoveryProposal,proposal_id)
    if not p: raise HTTPException(404,'Proposal not found')
    try: return ingest(db,p)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        db.rollback(); raise HTTPException(502,f'Ingestion failed ({type(exc).__name__})') from exc

@router.post('/proposals/{proposal_id}/extract')
def extract_one(proposal_id:int,db:Session=Depends(get_db)):
    p=db.get(DiscoveryProposal,proposal_id)
    if not p or p.status!='approved' or not p.last_snapshot_id: raise HTTPException(409,'Approved and ingested proposal required')
    if not os.getenv('OPENAI_API_KEY'): raise HTTPException(503,'OPENAI_API_KEY not configured')
    from .llm_extraction import extract_llm
    try:
        result=extract_llm(db,p.last_snapshot_id)
        db.add(DiscoveryEvent(proposal_id=p.id,action='extracted',detail=str(result)[:500],created_at=utcnow())); db.commit()
        return result
    except Exception as exc:
        db.rollback(); raise HTTPException(502,f'Extraction failed ({type(exc).__name__})') from exc

@router.get('/events')
def events(db:Session=Depends(get_db)):
    rows=db.scalars(select(DiscoveryEvent).order_by(DiscoveryEvent.id.desc()).limit(100)).all()
    return [{'id':r.id,'proposal_id':r.proposal_id,'action':r.action,'detail':r.detail,'created_at':r.created_at} for r in rows]

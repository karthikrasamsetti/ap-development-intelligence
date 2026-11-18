"""Admin-only source-monitoring API; public URLs cannot be submitted."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import SourceMonitorState, SourceMonitorRun
from .source_monitor import registry, run_monitor
from .review_api import admin_auth

router=APIRouter(prefix='/api/v1/admin/monitor',tags=['source-monitor'],dependencies=[Depends(admin_auth)])

class RunRequest(BaseModel):
    source_keys: list[str] | None = None
    force: bool = False

@router.get('/status')
def status(db:Session=Depends(get_db)):
    states={x.source_key:x for x in db.scalars(select(SourceMonitorState)).all()}
    counts=dict(db.execute(select(SourceMonitorRun.source_key,func.count()).group_by(SourceMonitorRun.source_key)).all())
    return {'sources':[{'key':s['key'],'name':s['name'],'url':s['url'],'interval_minutes':s.get('interval_minutes',1440),
        'enabled':states[s['key']].enabled if s['key'] in states else True,
        'last_checked_at':states[s['key']].last_checked_at if s['key'] in states else None,
        'last_success_at':states[s['key']].last_success_at if s['key'] in states else None,
        'last_snapshot_id':states[s['key']].last_snapshot_id if s['key'] in states else None,
        'consecutive_failures':states[s['key']].consecutive_failures if s['key'] in states else 0,
        'last_error':states[s['key']].last_error if s['key'] in states else None,
        'runs':counts.get(s['key'],0)} for s in registry()]}

@router.get('/runs')
def runs(limit:int=50,db:Session=Depends(get_db)):
    limit=max(1,min(200,limit))
    rows=db.scalars(select(SourceMonitorRun).order_by(SourceMonitorRun.id.desc()).limit(limit)).all()
    return [{'id':r.id,'source_key':r.source_key,'result':r.result,'snapshot_id':r.snapshot_id,'error_message':r.error_message,'started_at':r.started_at,'finished_at':r.finished_at} for r in rows]

@router.post('/run')
def run(body:RunRequest,db:Session=Depends(get_db)):
    if body.source_keys is not None and len(body.source_keys)>30: raise HTTPException(422,'Too many source keys')
    try: return run_monitor(db,keys=body.source_keys,force=body.force)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

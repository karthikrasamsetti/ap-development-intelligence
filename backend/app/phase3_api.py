from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import IngestionSnapshot
from .source_registry import SOURCES

router=APIRouter(prefix='/api/v1', tags=['source-ingestion'])
@router.get('/source-registry')
def source_registry():
    return {'sources': SOURCES, 'policy':'Source pages are evidence candidates, not verified projects.'}

@router.get('/ingestion/review-queue')
def review_queue(limit:int=Query(20,ge=1,le=100), db:Session=Depends(get_db)):
    rows=db.scalars(select(IngestionSnapshot).order_by(IngestionSnapshot.fetched_at.desc()).limit(limit)).all()
    return [{'id':r.id,'source_key':r.source_key,'title':r.title,'url':r.url,'fetched_at':r.fetched_at,'review_status':r.review_status,'excerpt':r.excerpt} for r in rows]

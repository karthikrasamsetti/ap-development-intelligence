from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .review_api import admin_auth
from .extraction import extract_snapshot
router=APIRouter(prefix='/api/v1/admin',tags=['admin-extraction'],dependencies=[Depends(admin_auth)])
@router.post('/snapshots/{snapshot_id}/extract')
def extract(snapshot_id:int,db:Session=Depends(get_db)):
    try: return extract_snapshot(db,snapshot_id)
    except ValueError as e: raise HTTPException(404,str(e))

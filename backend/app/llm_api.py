import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .review_api import admin_auth
from .llm_extraction import extract_llm

router = APIRouter(prefix='/api/v1/admin',tags=['admin-llm-extraction'],dependencies=[Depends(admin_auth)])

@router.post('/snapshots/{snapshot_id}/extract-llm')
def run_llm(snapshot_id: int, db: Session = Depends(get_db)):
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503,'OPENAI_API_KEY is not configured. Add it to project-root .env and restart the API container.')
    try:
        return extract_llm(db,snapshot_id)
    except ValueError as exc:
        raise HTTPException(404,str(exc))
    except Exception as exc:
        db.rollback()
        # Avoid exposing provider details, prompts, or credentials through API errors.
        raise HTTPException(502,f'LLM extraction failed ({type(exc).__name__}); check backend logs')

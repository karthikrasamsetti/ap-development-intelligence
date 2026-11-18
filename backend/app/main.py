from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from .db import get_db
from .models import Development as DevelopmentRow

app = FastAPI(title='AP Development Intelligence API', version='0.2.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

class Source(BaseModel):
    title: str
    url: str
    published_on: date | None = None
    source_type: Literal['government', 'company', 'news', 'other'] = 'other'
    model_config = ConfigDict(from_attributes=True)

class Development(BaseModel):
    id: str
    title: str
    category: Literal['investment', 'infrastructure', 'scheme', 'policy', 'technology', 'other']
    district: str | None
    sector: str | None = None
    status: Literal['announced', 'mou_signed', 'approved', 'grounded', 'operational', 'delayed', 'cancelled']
    investment_inr_crore: float | None = None
    expected_jobs: int | None = None
    jobs_created: int | None = None
    summary: str
    source: Source | None = None
    is_demo: bool = True
    model_config = ConfigDict(from_attributes=True)

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'ap-development-intelligence-api'}

@app.get('/health/db')
def database_health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'connected'}

@app.get('/api/v1/developments', response_model=list[Development])
def list_developments(category: str | None = None, district: str | None = None, db: Session = Depends(get_db)):
    stmt = select(DevelopmentRow).order_by(DevelopmentRow.created_at.desc(), DevelopmentRow.id)
    if category:
        stmt = stmt.where(DevelopmentRow.category == category)
    if district:
        stmt = stmt.where(func.lower(DevelopmentRow.district) == district.lower())
    return db.scalars(stmt).all()

@app.get('/api/v1/dashboard')
def dashboard(db: Session = Depends(get_db)):
    items = db.scalars(select(DevelopmentRow).order_by(DevelopmentRow.created_at.desc(), DevelopmentRow.id)).all()
    live = [item for item in items if not item.is_demo and item.verification_status == 'verified']
    return {
        'as_of': datetime.now(timezone.utc).isoformat(),
        'data_mode': 'demo' if any(x.is_demo for x in items) else 'database',
        'notice': 'Demo records are illustrative, not verified Andhra Pradesh statistics.' if any(x.is_demo for x in items) else 'Only verified records count toward public impact metrics.',
        'metrics': {
            'tracked_records': len(live),
            'mou_signed': sum(x.status == 'mou_signed' for x in live),
            'grounded': sum(x.status == 'grounded' for x in live),
            'operational': sum(x.status == 'operational' for x in live),
            'verified_jobs_created': sum(x.jobs_created or 0 for x in live),
        },
        'recent_developments': [Development.model_validate(x).model_dump(mode='json') for x in items[:20]],
    }

from .phase3_api import router as phase3_router
from .pdf_batch_v8_api import router as pdf_batch_v8_router
app.include_router(pdf_batch_v8_router)
app.include_router(phase3_router)

from .review_api import router as review_router
app.include_router(review_router)

from .extraction_api import router as extraction_router
app.include_router(extraction_router)

from .llm_api import router as llm_router
app.include_router(llm_router)

from .cross_source_api import router as cross_source_router
app.include_router(cross_source_router)

from .monitor_api import router as monitor_router
app.include_router(monitor_router)

from .discovery_api import router as discovery_router
app.include_router(discovery_router)

from .financial_evidence_api import router as financial_evidence_router
app.include_router(financial_evidence_router)
from .pdf_review_v5_api import router as pdf_review_v5_router
app.include_router(pdf_review_v5_router)

from .pdf_review_v6_api import router as pdf_review_v6_router
app.include_router(pdf_review_v6_router)

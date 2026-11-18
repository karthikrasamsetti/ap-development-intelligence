from datetime import date, datetime, timezone
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

app = FastAPI(
    title="AP Development Intelligence API",
    version="0.1.0",
    description="Public API for tracking Andhra Pradesh development with source transparency."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ProjectStatus = Literal["announced", "mou_signed", "approved", "grounded", "operational", "delayed", "cancelled"]

class Source(BaseModel):
    title: str
    url: str
    published_on: date | None = None
    source_type: Literal["government", "company", "news", "other"] = "other"

class Development(BaseModel):
    id: str
    title: str
    category: Literal["investment", "infrastructure", "scheme", "policy", "technology", "other"]
    district: str | None
    sector: str | None = None
    status: ProjectStatus
    investment_inr_crore: float | None = None
    expected_jobs: int | None = None
    jobs_created: int | None = None
    summary: str
    source: Source | None = None
    is_demo: bool = True

# Deliberately illustrative UI fixtures. Never present these as verified current facts.
DEMO_ITEMS = [
    Development(
        id="demo-001", title="Illustrative renewable energy project",
        category="investment", district="Anantapur", sector="Renewable energy",
        status="mou_signed", investment_inr_crore=1200,
        expected_jobs=850, jobs_created=None,
        summary="Illustrative record showing how a proposed investment is represented. Replace with a verified source before publication."
    ),
    Development(
        id="demo-002", title="Illustrative port connectivity upgrade",
        category="infrastructure", district="Kakinada", sector="Transport",
        status="grounded", investment_inr_crore=450,
        expected_jobs=200, jobs_created=None,
        summary="Illustrative project record. The status and figures are sample data, not a claim about a real project."
    ),
    Development(
        id="demo-003", title="Illustrative farmer support scheme",
        category="scheme", district=None, sector="Agriculture",
        status="approved", investment_inr_crore=None,
        expected_jobs=None, jobs_created=None,
        summary="Illustrative statewide scheme entry. Add official eligibility rules, benefit amounts and application links."
    ),
]

@app.get("/health")
def health():
    return {"status": "ok", "service": "ap-development-intelligence-api"}

@app.get("/api/v1/developments", response_model=list[Development])
def list_developments(category: str | None = None, district: str | None = None):
    items = DEMO_ITEMS
    if category:
        items = [x for x in items if x.category == category]
    if district:
        items = [x for x in items if x.district and x.district.lower() == district.lower()]
    return items

@app.get("/api/v1/dashboard")
def dashboard():
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "data_mode": "demo",
        "notice": "Illustrative sample records only. No live or verified AP statistics are represented.",
        "metrics": {
            "tracked_records": len(DEMO_ITEMS),
            "mou_signed": sum(x.status == "mou_signed" for x in DEMO_ITEMS),
            "grounded": sum(x.status == "grounded" for x in DEMO_ITEMS),
            "operational": sum(x.status == "operational" for x in DEMO_ITEMS),
            "verified_jobs_created": sum(x.jobs_created or 0 for x in DEMO_ITEMS),
        },
        "recent_developments": DEMO_ITEMS,
    }

# AP Development Intelligence

A public-facing Andhra Pradesh development tracker. This is the first full-stack MVP scaffold.

## Stack
- Frontend: Next.js App Router, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic
- Database: PostgreSQL (Docker Compose)
- Initial data: clearly labelled illustrative seed records (not live government data)

## Run locally

### 1. Start API + database
```bash
docker compose up --build
```
API: http://localhost:8000  
API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health  
Dashboard API: http://localhost:8000/api/v1/dashboard

### 2. Start frontend
In another terminal:
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
Open http://localhost:3000.

The frontend falls back to clearly labelled demo data if the API is not running.

## Important data rules
- Proposed investment != realized investment.
- MoU signed != project grounded.
- Expected jobs != jobs created.
- Beneficiary estimates != verified beneficiaries.
- Every production record should include source URL, publication date, retrieval date, confidence, and verification status.
- Do not publish a claim as verified unless a source supports it.

## Next milestones
1. Replace illustrative seed records with sourced ingestion.
2. Add PostgreSQL persistence and migrations.
3. Add current 28-district boundary GeoJSON and PostGIS queries.
4. Add source registry, deduplication and human review.
5. Add LangGraph research/extraction/verification workflows.
6. Add Ask AP retrieval with citations and evaluation.

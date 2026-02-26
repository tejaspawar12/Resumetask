# AI Applicant Ranking System

Turn 200+ resumes into structured scores and a trusted top-5% shortlist — without humans reading everything.

- **Plans:** [Master Plan](PLAN_AI_Applicant_Ranking_System.md) · [Phase Plan](PHASE_PLAN.md)
- **Submission:** [SUBMISSION.md](SUBMISSION.md) (1–2 page write-up) · [LOOM_SCRIPT.md](LOOM_SCRIPT.md) (5-min Loom talking points)
- **Stack:** Next.js (frontend), FastAPI (backend), Railway Postgres, AWS Bedrock (Claude + Titan Embeddings)

## Run locally

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
cp .env.example .env     # edit with your DATABASE_URL, AWS keys
uvicorn app.main:app --reload
```

- API: http://localhost:8000  
- Health: http://localhost:8000/health  
- Docs: http://localhost:8000/docs  

### Database

Set `DATABASE_URL` in `backend/.env` (e.g. Railway Postgres or local Postgres). Then:

```bash
cd backend
alembic upgrade head
```

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

- App: http://localhost:3000  

## Deployment (Phase 10)

### Backend (e.g. Railway)

- Set env vars: `DATABASE_URL` (Postgres), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `BEDROCK_MODEL_ID_EXTRACT`, `BEDROCK_MODEL_ID_JUDGE`, `EMBEDDING_MODEL_ID` (see `backend/.env.example`).
- Run migrations: `alembic upgrade head` in the backend container or release step.
- Ensure CORS allows your frontend origin (e.g. `https://your-app.vercel.app`). In `app/main.py`, `CORSMiddleware` uses `origins` from config; set `CORS_ORIGINS` in env if needed.

### Frontend (e.g. Vercel or Railway)

- Set `NEXT_PUBLIC_API_URL` to your backend URL (e.g. `https://your-backend.railway.app`).

### Demo data

- The “Use demo dataset” flow uses **synthetic resumes only** (no real PII). See `backend/app/services/demo_resumes.py`.

## Project layout

```
Resume/
├── backend/          # FastAPI app, DB models, pipeline
├── frontend/         # Next.js app (Landing, Dashboard, Candidate detail)
├── PLAN_AI_Applicant_Ranking_System.md
└── PHASE_PLAN.md
```

# AI Applicant Ranking System

**Turn 200+ resumes into a trusted top-5% shortlist with evidence and explanations — without reading every CV.**

This project was built as a take-home task: design and implement a system that automatically identifies the top 5% of applicants, explains *why* each candidate was shortlisted (or why backups didn’t make the top 10), and does it in a defensible, auditable way. The solution is a full-stack app (Next.js + FastAPI) deployed on Railway, with optional job-description-based ranking and a one-click exportable report.

---

## Try it live

| | Link |
|---|------|
| **App (frontend)** | **[https://beneficial-endurance-production.up.railway.app](https://beneficial-endurance-production.up.railway.app)** |
| **API docs (backend)** | **[https://resumetask-production.up.railway.app/docs](https://resumetask-production.up.railway.app/docs)** |

---

## How to test the live app (5 minutes)

1. **Open the app:** [https://beneficial-endurance-production.up.railway.app](https://beneficial-endurance-production.up.railway.app)

2. **Option A — Quick demo (no upload):**  
   - Check **“Use demo dataset”** → click **“Run evaluation”**.  
   - You’ll be redirected to the run dashboard. Wait for the pipeline to finish (progress is polled every few seconds).  
   - You’ll see a **rankings table** with synthetic candidates, scores, and shortlist status.

3. **Option B — Your own PDFs:**  
   - (Optional) Paste a **job description** in the text area to rank against *this* role.  
   - Click **“Choose Files”** and select one or more resume PDFs (max 250 files, 10 MB each).  
   - Click **“Run evaluation”** → you’re taken to the dashboard; wait until status is **Completed**.

4. **What you’ll see:**  
   - **Rankings table:** Filename, pipeline pill (**Deep Scored** vs **Embedding-only**), shortlist status (Top 5% | Backup), final score, five dimension subscores (Systems, Product, AI, Clarity, Shipping), confidence, risk flags.  
   - **Click a candidate** → detail view with **“Why shortlisted”** (top 5%) or **“Why this candidate didn’t make top 10”** (backups), **score breakdown with evidence quotes** per dimension, and risk flags.  
   - **Export report:** On the dashboard, click **“Export report”** → opens an HTML report (cover, shortlist table, per-candidate sections). Use the browser’s Print or “Save as PDF” to download.

5. **Backend API:**  
   - Open [https://resumetask-production.up.railway.app/docs](https://resumetask-production.up.railway.app/docs) to explore **POST /runs**, **POST /runs/demo**, upload, start, candidates, and report endpoints.

---

## What the results mean

- **Top 5%:** Candidates with the highest weighted aggregate score in this run. Each gets **“Why shortlisted”** (3 bullets).  
- **Backups:** Next tier after top 5%; each gets **“Why this candidate didn’t make top 10”** so you can compare to the cutoff.  
- **Five dimensions:** Every (deep-scored) candidate is scored 1–5 on **Systems thinking**, **Product judgment**, **Applied AI fluency**, **Clarity**, and **Bias toward shipping**. The UI and report show dimension scores plus **evidence quotes** from the resume that support each score.  
- **Pipeline pill:** **Deep Scored** = shortlisted and scored by the full rubric; **Embedding-only** = relevance-ranked but not deep-scored (saves cost at scale).  
- **Top 5% threshold:** Computed as the top 5% of *candidate count in that run* (e.g. 4 candidates → top 5% = 1; 200 → top 5% = 10).

---

## How I approached the problem

**Goal:** Not just “rank resumes,” but produce a **trusted, explainable shortlist** with clear reasoning.

**Design choices:**

1. **Five stable dimensions** — Systems thinking, Product judgment, Applied AI fluency, Clarity, Bias toward shipping. They stay the same for every run; optional **job description (JD)** is used to *interpret* them for the role (embeddings and Judge both use the JD). So ranking is “for this job” while keeping the rubric auditable and comparable.

2. **Two-stage pipeline** — (1) **Embeddings** (Titan) + cosine similarity vs. JD (or default criteria) → shortlist top K. (2) **Deep scoring** only for the shortlist (Claude Judge, evidence-only input). That keeps cost and latency under control for 200+ resumes.

3. **Evidence-only scoring** — The Judge sees structured profile + extracted evidence snippets per dimension, not raw resume text. That reduces prompt-injection risk and bias from narrative style; scores are tied to stated experience.

4. **Explainability** — Every shortlisted candidate gets “Why shortlisted” or “Why not top 10,” a score breakdown with evidence quotes, risk flags (e.g. “Insufficient evidence for Product”), and an exportable HTML report so recruiters can share and defend the outcome.

**Tech stack:** Next.js (frontend), FastAPI (backend), PostgreSQL (Railway), AWS Bedrock (Claude for extraction + Judge, Titan for embeddings). No Redis; the worker uses a Postgres job queue (`FOR UPDATE SKIP LOCKED`).

---

## How I deployed it (and what I fixed)

- **Monorepo:** Repo has `backend/` (FastAPI) and `frontend/` (Next.js). On Railway, each service has its **Root Directory** set to `backend` or `frontend` so the correct app is built and run.

- **Backend start command:** Railpack didn’t auto-detect the FastAPI app in a subdirectory. I added a **Procfile** in `backend/` with `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` and set the backend service root to `backend`, so the start command is explicit.

- **CORS:** The frontend (different origin) calls the backend API. The browser blocked requests until the backend sent `Access-Control-Allow-Origin` for the frontend. I set **CORS_ORIGINS** on the backend (Resumetask) to the frontend’s public URL (`https://beneficial-endurance-production.up.railway.app`) and redeployed so the backend allows that origin.

- **Frontend API URL:** The frontend needs the backend URL at build time (`NEXT_PUBLIC_API_URL`). I set it to the full backend URL (e.g. `https://resumetask-production.up.railway.app`) in the frontend service variables and redeployed so the built app points at the live API.

- **Database:** PostgreSQL is provisioned on Railway; the backend’s **DATABASE_URL** is set via Railway’s variable reference to the Postgres service. Migrations are run as part of deployment or manually once (`alembic upgrade head`).

---

## Repo structure

```
Resumetask/
├── backend/                 # FastAPI app
│   ├── app/
│   │   ├── main.py          # App, CORS, health
│   │   ├── routers/         # /runs, /runs/demo, upload, start, candidates, report
│   │   ├── models/          # Run, Candidate, Job
│   │   ├── schemas/
│   │   ├── services/        # extract_pdf, profile_extract, embeddings, judge, reasons, worker, report
│   │   └── ...
│   ├── Procfile             # Railway: uvicorn app.main:app
│   ├── requirements.txt
│   └── alembic/             # Migrations
├── frontend/                # Next.js app
│   ├── app/                 # Landing, /runs/[runId], /runs/.../candidates/[candidateId]
│   └── lib/api.ts           # API client
└── README.md
```

---

## Run locally

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env      # set DATABASE_URL, AWS_*, CORS_ORIGINS
alembic upgrade head
uvicorn app.main:app --reload
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

**Frontend:**

```bash
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

- App: http://localhost:3000  

**Worker:** The backend starts a background worker thread that processes jobs (extract → profile → embed → shortlist → score → reasons). No separate worker process needed for local runs.

---

## Summary

This project delivers a **working, deployed** system that:

- Accepts 200+ resume PDFs (or a one-click demo dataset) and an optional job description.  
- Runs a two-stage pipeline (embedding shortlist → evidence-only deep scoring on five dimensions).  
- Outputs a top 5% and backups with “Why shortlisted” / “Why not top 10,” evidence-backed scores, and an exportable report.  
- Is deployed on Railway with frontend and backend wired via CORS and public URLs, so recruiters can try it immediately via the links above.

**Live app:** [https://beneficial-endurance-production.up.railway.app](https://beneficial-endurance-production.up.railway.app)  
**API docs:** [https://resumetask-production.up.railway.app/docs](https://resumetask-production.up.railway.app/docs)  
**Repo:** [https://github.com/tejaspawar12/Resumetask](https://github.com/tejaspawar12/Resumetask)

"""FastAPI app — AI Applicant Ranking System."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import runs
from app.services.worker import start_worker_thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_worker_thread()
    yield


app = FastAPI(
    title="AI Applicant Ranking API",
    description="Turn resumes into structured scores and a top-5% shortlist.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)


@app.get("/health")
def health():
    return {"status": "ok"}

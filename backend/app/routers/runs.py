"""Run and candidate API: create run, upload, start, GET run/candidates, demo. Phase 6–7."""
import hashlib
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.services.report import build_report_html
from app.database import get_db
from app.models import Candidate, Job, Run
from app.services.demo_resumes import get_demo_resume_pdfs
from app.schemas import (
    CandidateListResponse,
    CandidateResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunResponse,
    RunStatusResponse,
    UploadErrorItem,
    UploadResponse,
)
from app.schemas.run import JD_MAX_LENGTH

router = APIRouter(prefix="/runs", tags=["runs"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES = 250
PDF_MAGIC = b"%PDF"


def _run_response(r: Run) -> RunResponse:
    return RunResponse(
        id=r.id,
        status=r.status,
        step=r.step,
        progress=r.progress,
        message=r.message,
        source=r.source,
        config=r.config,
        candidate_ids=r.candidate_ids,
        embedding_shortlist_ids=r.embedding_shortlist_ids,
        top_5_percent_ids=r.top_5_percent_ids,
        backup_ids=r.backup_ids,
        role_criteria_text=r.role_criteria_text,
        k_shortlist_used=r.k_shortlist_used,
        error_message=r.error_message,
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
    )


def _candidate_response(c: Candidate) -> CandidateResponse:
    risk_list = c.risk_flags if isinstance(c.risk_flags, list) else None
    return CandidateResponse(
        id=c.id,
        run_id=c.run_id,
        candidate_id=c.candidate_id,
        filename=c.filename,
        status=c.status,
        error=c.error,
        extraction_error=c.extraction_error,
        rank=c.rank,
        embedding_rank=c.embedding_rank,
        embedding_score=c.embedding_score,
        shortlist_status=c.shortlist_status,
        confidence=c.confidence,
        confidence_reason=c.confidence_reason,
        scores_with_evidence=c.scores_with_evidence,
        risk_flags=risk_list,
        why_shortlisted=c.why_shortlisted,
        why_not_top_10=c.why_not_top_10,
        structured_profile=c.structured_profile,
        created_at=c.created_at.isoformat() if c.created_at else None,
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
    )


def _get_run_or_404(db: Session, run_id: UUID) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _normalize_jd(jd: str | None) -> str | None:
    """Strip and truncate job description; return None if empty."""
    if not jd or not (s := jd.strip()):
        return None
    return s[:JD_MAX_LENGTH] if len(s) > JD_MAX_LENGTH else s


@router.post("", response_model=RunCreateResponse)
def create_run(body: RunCreateRequest | None = Body(None), db: Session = Depends(get_db)):
    """Create a new run; optional job_description for JD-based ranking. Phase 11."""
    config = settings.default_run_config()
    role_text = _normalize_jd(body.job_description if body else None)
    if role_text:
        config = dict(config) if isinstance(config, dict) else {}
        config["role_criteria_text"] = role_text
    run = Run(
        status="pending",
        source="upload",
        config=config,
        role_criteria_text=role_text,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return RunCreateResponse(run_id=str(run.id))


@router.post("/demo", response_model=RunCreateResponse)
def create_demo_run(body: RunCreateRequest | None = Body(None), db: Session = Depends(get_db)):
    """
    Create a run with synthetic demo resumes and enqueue the pipeline. Phase 7.
    Optional job_description for JD-based ranking. Phase 11.
    """
    config = settings.default_run_config()
    role_text = _normalize_jd(body.job_description if body else None)
    if role_text:
        config = dict(config) if isinstance(config, dict) else {}
        config["role_criteria_text"] = role_text
    run = Run(
        status="pending",
        source="demo",
        config=config,
        role_criteria_text=role_text,
    )
    db.add(run)
    db.flush()

    for filename, pdf_raw in get_demo_resume_pdfs():
        raw = bytes(pdf_raw)
        candidate_id = hashlib.sha256(raw).hexdigest()[:32]
        c = Candidate(
            run_id=run.id,
            candidate_id=candidate_id,
            filename=filename[:512],
            pdf_bytes=raw,
            pdf_sha256=candidate_id,
            pdf_size_bytes=len(raw),
            status="uploaded",
        )
        db.add(c)

    job = Job(run_id=run.id, type="run_pipeline", status="queued")
    db.add(job)
    run.status = "running"
    run.step = "queued"
    run.message = "Demo run started"
    db.commit()
    db.refresh(run)
    return RunCreateResponse(run_id=str(run.id))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    """Get run by id."""
    run = _get_run_or_404(db, run_id)
    return _run_response(run)


@router.get("/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: UUID, db: Session = Depends(get_db)):
    """Get run status for polling (status, step, progress, message). Phase 6."""
    run = _get_run_or_404(db, run_id)
    return RunStatusResponse(
        status=run.status,
        step=run.step,
        progress=run.progress,
        message=run.message,
        error_message=run.error_message,
    )


@router.post("/{run_id}/upload", response_model=UploadResponse)
async def upload_resumes(
    run_id: UUID,
    files: list[UploadFile] = File(..., alias="files"),
    db: Session = Depends(get_db),
):
    """
    Upload PDF resumes. Max 10 MB per file, max 250 files.
    Validates PDF magic bytes; dedupes by content hash per run.
    """
    run = _get_run_or_404(db, run_id)
    if run.status not in ("pending", "uploaded"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload: run status is {run.status}",
        )

    errors: list[UploadErrorItem] = []
    accepted = 0
    rejected = 0
    duplicate_skipped = 0

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: max {MAX_FILES}",
        )

    for file in files:
        filename = file.filename or "unknown.pdf"
        try:
            raw = await file.read()
        except Exception as e:
            errors.append(UploadErrorItem(file=filename, reason=str(e)))
            rejected += 1
            continue

        if len(raw) > MAX_FILE_SIZE:
            errors.append(UploadErrorItem(file=filename, reason="File exceeds 10 MB"))
            rejected += 1
            continue
        if len(raw) < 5:
            errors.append(UploadErrorItem(file=filename, reason="File too small or empty"))
            rejected += 1
            continue
        if not raw.startswith(PDF_MAGIC):
            errors.append(UploadErrorItem(file=filename, reason="Not a PDF"))
            rejected += 1
            continue

        candidate_id = hashlib.sha256(raw).hexdigest()
        existing = db.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.candidate_id == candidate_id,
            )
        ).scalar_one_or_none()
        if existing:
            duplicate_skipped += 1
            continue

        candidate = Candidate(
            run_id=run_id,
            candidate_id=candidate_id,
            filename=filename[:512],
            pdf_bytes=bytes(raw),
            pdf_sha256=candidate_id,
            pdf_size_bytes=len(raw),
            status="uploaded",
        )
        db.add(candidate)
        accepted += 1

    run.status = "uploaded"
    db.commit()
    return UploadResponse(
        accepted=accepted,
        rejected=rejected,
        errors=errors,
        duplicate_skipped=duplicate_skipped,
    )


@router.post("/{run_id}/start", status_code=202)
def start_run(run_id: UUID, db: Session = Depends(get_db)):
    """Enqueue pipeline job for this run. Returns 202 Accepted."""
    run = _get_run_or_404(db, run_id)
    job = Job(run_id=run_id, type="run_pipeline", status="queued")
    db.add(job)
    run.status = "running"
    run.step = "queued"
    db.commit()
    return {"message": "Job queued", "run_id": str(run_id)}


@router.get("/{run_id}/candidates", response_model=CandidateListResponse)
def list_candidates(run_id: UUID, db: Session = Depends(get_db)):
    """List all candidates for a run."""
    _get_run_or_404(db, run_id)
    candidates = (
        db.execute(
            select(Candidate).where(Candidate.run_id == run_id).order_by(Candidate.created_at)
        )
        .scalars().all()
    )
    return CandidateListResponse(candidates=[_candidate_response(c) for c in candidates])


@router.get("/{run_id}/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(run_id: UUID, candidate_id: str, db: Session = Depends(get_db)):
    """Get one candidate by run_id and candidate_id (content hash)."""
    _get_run_or_404(db, run_id)
    row = (
        db.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.candidate_id == candidate_id,
            )
        )
        .scalars().one_or_none()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_response(row)


@router.get("/{run_id}/report")
def get_run_report(
    run_id: UUID,
    format: str = Query("html", alias="format"),
    db: Session = Depends(get_db),
):
    """Return run report as HTML (Phase 9). Use Print or Save as PDF in browser for PDF."""
    run = _get_run_or_404(db, run_id)
    candidates = (
        db.execute(
            select(Candidate).where(Candidate.run_id == run_id).order_by(Candidate.created_at)
        )
        .scalars().all()
    )
    html_content = build_report_html(run, [c for c in candidates])
    return Response(content=html_content, media_type="text/html; charset=utf-8")

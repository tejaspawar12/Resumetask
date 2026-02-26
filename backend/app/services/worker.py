"""Background worker: poll jobs, run extraction + profiling pipeline, clear pdf_bytes.

Phase 10: Do not log raw_text, cleaned_text, or PII. Log only run_id, candidate_id, step, error type.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Candidate, Job, Run
import math

from app.services.confidence import compute_confidence
from app.services.embeddings import (
    DEFAULT_ROLE_CRITERIA,
    cosine_similarity,
    embed_text,
    embed_texts_batch,
)
from app.services.evidence import build_evidence_from_profile
from app.services.extract_pdf import extract_text_from_pdf_bytes
from app.services.judge import judge_candidate
from app.services.profile_extract import extract_profile
from app.services.reasons import (
    generate_why_not_top_10,
    generate_why_shortlisted,
    rank10_summary_from_candidate,
)
from app.services.searchable_repr import build_searchable_representation

logger = logging.getLogger(__name__)
POLL_INTERVAL = 5


def _expire_old_uploads(session: Session) -> None:
    """Set pdf_bytes=NULL and status=failed for candidates uploaded > 1 hour ago and not yet processed."""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    session.execute(
        update(Candidate)
        .where(
            Candidate.status == "uploaded",
            Candidate.created_at < one_hour_ago,
            Candidate.pdf_bytes.isnot(None),
        )
        .values(
            pdf_bytes=None,
            status="failed",
            error="expired_before_processing",
        )
    )
    session.commit()


def _run_extraction_for_run(session: Session, run_id: UUID) -> None:
    """Load candidates with pdf_bytes, extract text, update DB, set pdf_bytes=NULL."""
    rows = (
        session.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.pdf_bytes.isnot(None),
            )
        )
        .scalars().all()
    )
    run = session.get(Run, run_id)
    if run:
        run.step = "extracting"
        run.progress = 0
        run.message = f"Extracting text from {len(rows)} resumes"
        session.add(run)
    session.commit()

    total = len(rows)
    for i, candidate in enumerate(rows):
        pdf_bytes = bytes(candidate.pdf_bytes) if candidate.pdf_bytes else None
        if not pdf_bytes:
            continue
        result = extract_text_from_pdf_bytes(pdf_bytes)
        candidate.pdf_bytes = None
        candidate.word_count = result.word_count
        candidate.cleaned_text = result.cleaned_text
        if result.error:
            candidate.status = "failed"
            candidate.error = result.error
            candidate.extraction_error = result.error
        else:
            candidate.status = "extracted"
            candidate.error = None
            candidate.extraction_error = None
        session.add(candidate)
        if run and total > 0:
            run.progress = int((i + 1) / total * 30)  # 0–30% for extraction
            run.message = f"Extracted {i + 1}/{total}"
            session.add(run)
        session.commit()

    if run:
        run.step = "extracted"
        run.progress = 35
        run.message = "Text extraction complete"
        session.add(run)
        session.commit()

    _run_profiling_for_run(session, run_id, run)


def _run_profiling_for_run(session: Session, run_id: UUID, run: Run | None) -> None:
    """For each candidate with cleaned_text and no structured_profile, call Claude and store profile."""
    rows = (
        session.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.status == "extracted",
                Candidate.cleaned_text.isnot(None),
            )
        )
        .scalars().all()
    )
    # Skip if already profiled (idempotency)
    to_profile = [c for c in rows if not c.structured_profile]
    if not to_profile:
        if run:
            run.step = "profiled"
            run.progress = 60
            run.message = "Profiling complete"
            session.add(run)
            session.commit()
        return

    model_id = None
    if run and run.config and isinstance(run.config, dict):
        model_id = run.config.get("claude_model_id_extract") or run.config.get("bedrock_model_id_extract")

    if run:
        run.step = "profiling"
        run.progress = 40
        run.message = f"Extracting profiles for {len(to_profile)} candidates"
        session.add(run)
        session.commit()

    total = len(to_profile)
    for i, candidate in enumerate(to_profile):
        text = (candidate.cleaned_text or "").strip()
        if not text:
            continue
        try:
            profile_obj, err = extract_profile(text, model_id=model_id)
        except Exception as e:
            logger.warning("Profile extraction failed for candidate %s: %s", candidate.id, e)
            profile_obj, err = None, str(e)
        if profile_obj is not None:
            candidate.structured_profile = profile_obj.model_dump(mode="json")
            candidate.status = "profiled"
            candidate.extraction_error = None
        else:
            candidate.extraction_error = err or "Extraction incomplete"
            candidate.status = "profiled"  # still mark profiled so we don't block; profile may be null
        session.add(candidate)
        if run and total > 0:
            run.progress = 40 + int((i + 1) / total * 20)  # 40–60% for profiling
            run.message = f"Profiled {i + 1}/{total}"
            session.add(run)
        session.commit()

    if run:
        run.step = "profiled"
        run.progress = 60
        run.message = "Structured profiles complete"
        session.add(run)
        session.commit()

    _run_embeddings_shortlist_for_run(session, run_id, run)


def _run_embeddings_shortlist_for_run(session: Session, run_id: UUID, run: Run | None) -> None:
    """Build searchable rep, embed role + candidates, rank by similarity, apply K shortlist."""
    rows = (
        session.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.structured_profile.isnot(None),
            )
        )
        .scalars().all()
    )
    if not rows:
        if run:
            run.step = "shortlisted"
            run.progress = 80
            run.message = "No candidates to shortlist"
            run.embedding_shortlist_ids = []
            run.k_shortlist_used = 0
            session.add(run)
            session.commit()
        return

    role_text = DEFAULT_ROLE_CRITERIA
    if run:
        if run.config and isinstance(run.config, dict) and run.config.get("role_criteria_text"):
            role_text = run.config["role_criteria_text"]
        elif run.role_criteria_text:
            role_text = run.role_criteria_text
        run.role_criteria_text = role_text

    model_id = None
    if run and run.config and isinstance(run.config, dict):
        model_id = run.config.get("embedding_model_id")

    if run:
        run.step = "embedding"
        run.progress = 62
        run.message = "Computing embeddings and shortlist"
        session.add(run)
        session.commit()

    # Build searchable rep per candidate
    candidate_list = list(rows)
    reps: list[tuple[Candidate, str]] = []
    for c in candidate_list:
        if not c.structured_profile:
            continue
        text = build_searchable_representation(c.structured_profile)
        if not text.strip():
            continue
        reps.append((c, text))

    if not reps:
        if run:
            run.step = "shortlisted"
            run.progress = 80
            run.message = "No valid profiles to embed"
            run.embedding_shortlist_ids = []
            run.k_shortlist_used = 0
            session.add(run)
            session.commit()
        return

    try:
        role_vec = embed_text(role_text, model_id=model_id)
    except Exception as e:
        logger.exception("Role embedding failed: %s", e)
        if run:
            run.step = "failed"
            run.error_message = f"Embedding failed: {e!s}"
            session.add(run)
            session.commit()
        return

    texts = [t for _, t in reps]
    try:
        vectors = embed_texts_batch(texts, model_id=model_id)
    except Exception as e:
        logger.exception("Candidate embeddings failed: %s", e)
        if run:
            run.step = "failed"
            run.error_message = f"Embedding failed: {e!s}"
            session.add(run)
            session.commit()
        return

    # Cosine similarity and rank
    scored: list[tuple[Any, float]] = []
    for (c, _), vec in zip(reps, vectors):
        if not vec:
            score = 0.0
        else:
            score = cosine_similarity(role_vec, vec)
        scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    N = len(scored)
    top5_count = math.ceil(0.05 * N)
    K = min(max(2 * top5_count, 40), 60) if N > 60 else N
    K = max(K, 1)

    shortlist_ids = [c.candidate_id for c, _ in scored[:K]]
    for rank_1based, (c, score) in enumerate(scored, start=1):
        c.embedding_rank = rank_1based
        c.embedding_score = round(score, 6)
        c.shortlist_status = "shortlisted" if rank_1based <= K else "not_shortlisted"
        session.add(c)

    if run:
        run.step = "shortlisted"
        run.progress = 80
        run.message = f"Shortlisted top {K} of {N}"
        run.embedding_shortlist_ids = shortlist_ids
        run.k_shortlist_used = K
        session.add(run)
    session.commit()

    _run_scoring_for_run(session, run_id, run)


def _run_scoring_for_run(session: Session, run_id: UUID, run: Run | None) -> None:
    """Score each shortlisted candidate with Judge; compute confidence; then rank and set top_5/backup."""
    shortlist_ids = (run.embedding_shortlist_ids or []) if run else []
    if not shortlist_ids:
        if run:
            run.step = "done"
            run.progress = 100
            run.status = "completed"
            run.message = "No shortlist to score"
            session.add(run)
            session.commit()
        return

    # Load shortlisted candidates
    candidates = (
        session.execute(
            select(Candidate).where(
                Candidate.run_id == run_id,
                Candidate.candidate_id.in_(shortlist_ids),
            )
        )
        .scalars().all()
    )
    c_by_id = {c.candidate_id: c for c in candidates}
    ordered = [c_by_id[cid] for cid in shortlist_ids if cid in c_by_id]

    weights = None
    judge_model_id = None
    if run and run.config and isinstance(run.config, dict):
        rw = run.config.get("rubric_weights")
        if isinstance(rw, dict):
            weights = {d: float(rw.get(d, 1.0)) for d in ("systems", "product", "ai", "clarity", "shipping")}
        judge_model_id = run.config.get("claude_model_id_judge") or run.config.get("bedrock_model_id_judge")

    if run:
        run.step = "scoring"
        run.progress = 82
        run.message = f"Scoring {len(ordered)} candidates"
        session.add(run)
        session.commit()

    total = len(ordered)
    for i, candidate in enumerate(ordered):
        profile = candidate.structured_profile or {}
        evidence = build_evidence_from_profile(profile)
        try:
            result, risk_flags, confidence_reason = judge_candidate(
                profile,
                evidence,
                model_id=judge_model_id,
                weights=weights,
                role_criteria_text=run.role_criteria_text if run else None,
            )
        except Exception as e:
            logger.warning("Judge failed for candidate %s: %s", candidate.candidate_id, e)
            result, risk_flags, confidence_reason = None, [], str(e)
        if result:
            candidate.scores_with_evidence = result
            candidate.risk_flags = risk_flags
            candidate.confidence_reason = confidence_reason
        candidate.confidence = compute_confidence(profile, candidate.word_count)
        candidate.status = "scored"
        session.add(candidate)
        if run and total > 0:
            run.progress = 82 + int((i + 1) / total * 13)
            run.message = f"Scored {i + 1}/{total}"
            session.add(run)
        session.commit()

    # Phase 5: rank by overall_score, set top_5 and backup
    scored_list = [
        c for c in ordered
        if c.scores_with_evidence and isinstance(c.scores_with_evidence, dict)
    ]
    scored_list.sort(
        key=lambda c: (
            -(c.scores_with_evidence.get("overall_score") or 0),
            len(c.risk_flags or []),
            {"high": 0, "medium": 1, "low": 2}.get(c.confidence or "low", 2),
        )
    )
    for rank_1based, c in enumerate(scored_list, start=1):
        c.rank = rank_1based
        session.add(c)
    session.commit()

    N_scored = len(scored_list)
    top5_count = math.ceil(0.05 * N_scored) if N_scored else 0
    top5_count = max(1, top5_count)
    top5_ids = [c.candidate_id for c in scored_list[:top5_count]]
    backup_ids = [c.candidate_id for c in scored_list[top5_count : top5_count + 10]]
    for c in scored_list[:top5_count]:
        c.shortlist_status = "top_5"
    for c in scored_list[top5_count : top5_count + 10]:
        c.shortlist_status = "backup"
    for c in scored_list[top5_count + 10 :]:
        c.shortlist_status = "other"
    for c in candidates:
        if c.shortlist_status not in ("top_5", "backup", "other"):
            c.shortlist_status = "not_scored"
        session.add(c)
    session.commit()

    # Phase 5.3 & 5.4: Why shortlisted (top 5%) and Why not top 10 (backups)
    rank10_candidate = scored_list[9] if len(scored_list) >= 10 else None
    rank10_summary = rank10_summary_from_candidate(
        rank10_candidate.scores_with_evidence if rank10_candidate else None
    )
    top5_candidates = scored_list[:top5_count]
    backup_candidates = scored_list[top5_count : top5_count + 10]
    if run:
        run.step = "reasons"
        run.message = "Generating why shortlisted / why not top 10"
        session.add(run)
        session.commit()
    for i, c in enumerate(top5_candidates):
        if c.scores_with_evidence and isinstance(c.scores_with_evidence, dict):
            try:
                c.why_shortlisted = generate_why_shortlisted(c.scores_with_evidence, model_id=judge_model_id)
            except Exception as e:
                logger.warning("Why shortlisted for %s: %s", c.candidate_id, e)
                c.why_shortlisted = ["Strong overall fit."]
            session.add(c)
            session.commit()
    for c in backup_candidates:
        if c.scores_with_evidence and isinstance(c.scores_with_evidence, dict):
            try:
                c.why_not_top_10 = generate_why_not_top_10(
                    c.scores_with_evidence,
                    rank10_summary,
                    model_id=judge_model_id,
                    role_criteria_text=run.role_criteria_text if run else None,
                )
            except Exception as e:
                logger.warning("Why not top 10 for %s: %s", c.candidate_id, e)
                c.why_not_top_10 = ["Below threshold vs top 10."]
            session.add(c)
            session.commit()

    if run:
        run.step = "done"
        run.progress = 100
        run.status = "completed"
        run.message = "Evaluation complete"
        run.top_5_percent_ids = top5_ids
        run.backup_ids = backup_ids
        session.add(run)
    session.commit()


def _process_job(session: Session, job_id: UUID, run_id: UUID) -> bool:
    """Process one run_pipeline job: expire old uploads, then run extraction for run_id. Returns True on success."""
    job = session.get(Job, job_id)
    if not job:
        return False
    try:
        _expire_old_uploads(session)
        _run_extraction_for_run(session, run_id)
        job.status = "done"
        job.error = None
    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        job.status = "failed"
        job.error = str(e)
        run = session.get(Run, run_id)
        if run:
            run.status = "failed"
            run.error_message = str(e)
            session.add(run)
    finally:
        job.attempts = (job.attempts or 0) + 1
        session.add(job)
        session.commit()
    return job.status == "done"


def _worker_loop() -> None:
    while True:
        try:
            db = SessionLocal()
            try:
                row = (
                    db.execute(
                        select(Job)
                        .where(Job.status == "queued", Job.type == "run_pipeline")
                        .with_for_update(skip_locked=True)
                        .limit(1)
                    )
                    .scalars().one_or_none()
                )
                if row:
                    job_id = row.id
                    run_id = row.run_id
                    row.status = "running"
                    row.attempts = (row.attempts or 0) + 1
                    db.add(row)
                    db.commit()
            finally:
                db.close()
            if row:
                db2 = SessionLocal()
                try:
                    _process_job(db2, job_id, run_id)
                finally:
                    db2.close()
        except Exception as e:
            logger.exception("Worker iteration error: %s", e)
        time.sleep(POLL_INTERVAL)


def start_worker_thread() -> None:
    """Start the worker in a daemon thread."""
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()
    logger.info("Worker thread started")

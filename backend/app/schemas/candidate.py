"""Pydantic schemas for Candidate API."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CandidateResponse(BaseModel):
    id: UUID
    run_id: UUID
    candidate_id: str
    filename: Optional[str] = None
    status: str
    error: Optional[str] = None
    extraction_error: Optional[str] = None
    rank: Optional[int] = None
    embedding_rank: Optional[int] = None
    embedding_score: Optional[float] = None
    shortlist_status: Optional[str] = None
    confidence: Optional[str] = None
    confidence_reason: Optional[str] = None
    scores_with_evidence: Optional[dict[str, Any]] = None
    risk_flags: Optional[list[str]] = None
    why_shortlisted: Optional[list[str]] = None
    why_not_top_10: Optional[list[str]] = None
    structured_profile: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateListResponse(BaseModel):
    candidates: list[CandidateResponse]

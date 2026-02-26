"""Pydantic schemas for Run API."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JD_MAX_LENGTH = 8000


class RunCreateRequest(BaseModel):
    """Optional body for POST /runs. Phase 11."""
    job_description: Optional[str] = Field(None, max_length=JD_MAX_LENGTH)


class RunCreateResponse(BaseModel):
    run_id: str

    model_config = ConfigDict(from_attributes=True)


class RunStatusResponse(BaseModel):
    """Lightweight response for polling run progress (Phase 6)."""
    status: str
    step: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    error_message: Optional[str] = None


class RunResponse(BaseModel):
    id: UUID
    status: str
    step: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    source: str
    config: Optional[dict[str, Any]] = None
    candidate_ids: Optional[list[str]] = None
    embedding_shortlist_ids: Optional[list[str]] = None
    top_5_percent_ids: Optional[list[str]] = None
    backup_ids: Optional[list[str]] = None
    role_criteria_text: Optional[str] = None
    k_shortlist_used: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

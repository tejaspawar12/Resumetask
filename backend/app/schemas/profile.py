"""Structured JSON profile schema for resume extraction (Phase 2)."""
from typing import Any, Optional

from pydantic import BaseModel, Field


class RoleCompany(BaseModel):
    role: str = ""
    company: str = ""
    duration: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class AiMlExperience(BaseModel):
    has_experience: bool = False
    details: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str = ""
    description: Optional[str] = None
    impact: Optional[str] = None
    links: list[str] = Field(default_factory=list)


class Links(BaseModel):
    github: Optional[str] = None
    portfolio: Optional[str] = None
    linkedin: Optional[str] = None
    other: list[str] = Field(default_factory=list)


class StructuredProfile(BaseModel):
    """Standard profile extracted from a resume. All fields optional for sparse resumes."""
    years_of_experience: Optional[float] = None
    roles_and_companies: list[RoleCompany] = Field(default_factory=list)
    skills_tech_stack: list[str] = Field(default_factory=list)
    ai_ml_llm_experience: Optional[AiMlExperience] = None
    projects: list[Project] = Field(default_factory=list)
    impact_metrics: list[str] = Field(default_factory=list)
    ownership_leadership: list[str] = Field(default_factory=list)
    links: Optional[Links] = None
    education: list[Any] = Field(default_factory=list)  # flexible: str or dict
    summary_or_bio: Optional[str] = None
    raw_sections_detected: Optional[dict[str, Any]] = None


def validate_profile(data: dict[str, Any]) -> tuple[Optional[StructuredProfile], list[str]]:
    """
    Validate a dict against StructuredProfile. Returns (profile, errors).
    If validation fails, errors list is non-empty; profile may still be partial.
    """
    errors: list[str] = []
    try:
        profile = StructuredProfile.model_validate(data)
        return profile, []
    except Exception as e:
        errors.append(str(e))
    try:
        # Lenient: build with only valid fields
        profile = StructuredProfile.model_construct(**{k: v for k, v in data.items() if k in StructuredProfile.model_fields})
        return profile, errors
    except Exception as e2:
        errors.append(str(e2))
        return None, errors

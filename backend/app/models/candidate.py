"""Candidate model — one resume per run."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, Float, ForeignKey, LargeBinary, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID

from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(64), nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    filename = Column(String(512), nullable=True)
    pdf_bytes = Column(LargeBinary, nullable=True)
    pdf_sha256 = Column(String(64), nullable=True)
    pdf_size_bytes = Column(Integer, nullable=True)

    status = Column(String(32), nullable=False, default="uploaded")
    error = Column(Text, nullable=True)
    extraction_error = Column(Text, nullable=True)

    cleaned_text = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    structured_profile = Column(JSONB, nullable=True)

    embedding_rank = Column(Integer, nullable=True)
    embedding_score = Column(Float, nullable=True)

    scores_with_evidence = Column(JSONB, nullable=True)
    risk_flags = Column(JSONB, nullable=True)
    confidence = Column(String(16), nullable=True)
    confidence_reason = Column(Text, nullable=True)
    rank = Column(Integer, nullable=True)
    shortlist_status = Column(String(32), nullable=True)

    why_shortlisted = Column(ARRAY(Text), nullable=True)
    why_not_top_10 = Column(ARRAY(Text), nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "candidate_id", name="uq_candidates_run_candidate"),
        Index("ix_candidates_run_shortlist", "run_id", "shortlist_status"),
        Index("ix_candidates_run_rank", "run_id", "rank"),
    )

"""Run model — one evaluation run (upload or demo)."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID

from app.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    status = Column(String(32), nullable=False, default="pending")
    step = Column(String(32), nullable=True)
    progress = Column(Integer, default=0)
    message = Column(Text, nullable=True)

    source = Column(String(16), nullable=False, default="upload")
    config = Column(JSONB, nullable=True)

    candidate_ids = Column(ARRAY(String), nullable=True)
    embedding_shortlist_ids = Column(ARRAY(String), nullable=True)
    top_5_percent_ids = Column(ARRAY(String), nullable=True)
    backup_ids = Column(ARRAY(String), nullable=True)

    role_criteria_text = Column(Text, nullable=True)
    k_shortlist_used = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

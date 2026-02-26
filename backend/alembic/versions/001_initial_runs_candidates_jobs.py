"""Initial runs, candidates, jobs.

Revision ID: 001
Revises:
Create Date: 2025-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("step", sa.String(32), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="upload"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("candidate_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("embedding_shortlist_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("top_5_percent_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("backup_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("role_criteria_text", sa.Text(), nullable=True),
        sa.Column("k_shortlist_used", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("filename", sa.String(512), nullable=True),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("pdf_sha256", sa.String(64), nullable=True),
        sa.Column("pdf_size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("cleaned_text", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("structured_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_rank", sa.Integer(), nullable=True),
        sa.Column("embedding_score", sa.Float(), nullable=True),
        sa.Column("scores_with_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=True),
        sa.Column("confidence_reason", sa.Text(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("shortlist_status", sa.String(32), nullable=True),
        sa.Column("why_shortlisted", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("why_not_top_10", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.create_index("ix_candidates_run_id", "candidates", ["run_id"], unique=False)
    op.create_index("ix_candidates_run_rank", "candidates", ["run_id", "rank"], unique=False)
    op.create_index("ix_candidates_run_shortlist", "candidates", ["run_id", "shortlist_status"], unique=False)
    op.create_unique_constraint("uq_candidates_run_candidate", "candidates", ["run_id", "candidate_id"])
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(64), nullable=False, server_default="run_pipeline"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_jobs_run_id", "jobs", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_run_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_constraint("uq_candidates_run_candidate", "candidates", type_="unique")
    op.drop_index("ix_candidates_run_shortlist", table_name="candidates")
    op.drop_index("ix_candidates_run_rank", table_name="candidates")
    op.drop_index("ix_candidates_run_id", table_name="candidates")
    op.drop_table("candidates")
    op.drop_table("runs")

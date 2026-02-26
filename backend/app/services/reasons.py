"""Phase 5: Generate why_shortlisted and why_not_top_10 with Claude."""
import logging
import re
from typing import Any

from app.config import settings
from app.services.bedrock import invoke_claude

logger = logging.getLogger(__name__)

WHY_SHORTLISTED_SYSTEM = """You write 3 short bullet points explaining why a candidate was shortlisted for the role. Use only the dimension scores and evidence provided. Output exactly 3 lines, one bullet per line. No numbering, no markdown, no extra text. Each line should be a single sentence (e.g. Strong systems depth and ownership.). If role context was provided, reference fit for that role."""

WHY_NOT_TOP10_SYSTEM = """You write 1-3 short bullet points explaining why this candidate did not make the top 10. Compare their scores to the #10 candidate. Be factual and brief. Output 1-3 lines, one bullet per line. No numbering, no markdown. Example: Slightly weaker on systems depth. If role context was provided, reference fit for that role."""


def _parse_bullets(text: str, max_bullets: int = 5) -> list[str]:
    """Extract bullet lines from model output."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    # Remove leading bullets/dashes/numbers
    out = []
    for ln in lines[:max_bullets]:
        ln = re.sub(r"^[\s\-*•\d.)]+", "", ln).strip()
        if ln:
            out.append(ln)
    return out


def generate_why_shortlisted(
    scores_with_evidence: dict[str, Any],
    model_id: str | None = None,
    role_criteria_text: str | None = None,
) -> list[str]:
    """Generate 3 bullets for why this candidate was shortlisted (top 5%). Phase 11: optional role context."""
    model_id = model_id or settings.bedrock_model_id_judge
    dims = scores_with_evidence.get("dimensions") or {}
    summary = []
    for name, d in dims.items():
        if isinstance(d, dict):
            s = d.get("score")
            ev = d.get("evidence") or []
            summary.append(f"{name}: score {s}, evidence: {ev[:2]}")
    user_msg = "Dimension scores and evidence:\n" + "\n".join(summary)
    if role_criteria_text and role_criteria_text.strip():
        user_msg = "Role/criteria for this run:\n" + role_criteria_text.strip()[:1500] + "\n\n" + user_msg
    try:
        raw = invoke_claude(
            user_message=user_msg,
            system_prompt=WHY_SHORTLISTED_SYSTEM,
            model_id=model_id,
            temperature=0.3,
            max_tokens=300,
        )
        return _parse_bullets(raw, max_bullets=3)
    except Exception as e:
        logger.warning("Why shortlisted generation failed: %s", e)
        # Fallback from scores
        bullets = []
        for name, d in (dims or {}).items():
            if isinstance(d, dict) and (d.get("score") or 0) >= 4:
                bullets.append(f"Strong {name}.")
        return bullets[:3] if bullets else ["Strong overall fit."]


def generate_why_not_top_10(
    candidate_scores: dict[str, Any],
    rank10_summary: str,
    model_id: str | None = None,
    role_criteria_text: str | None = None,
) -> list[str]:
    """Generate 1-3 bullets for why this backup candidate didn't make top 10. Phase 11: optional role context."""
    model_id = model_id or settings.bedrock_model_id_judge
    dims = candidate_scores.get("dimensions") or {}
    summary = []
    for name, d in dims.items():
        if isinstance(d, dict):
            summary.append(f"{name}: {d.get('score', '?')}/5")
    user_msg = (
        "This candidate's dimension scores:\n"
        + "\n".join(summary)
        + "\n\n#10 candidate (threshold):\n"
        + rank10_summary
    )
    if role_criteria_text and role_criteria_text.strip():
        user_msg = "Role/criteria for this run:\n" + role_criteria_text.strip()[:1500] + "\n\n" + user_msg
    try:
        raw = invoke_claude(
            user_message=user_msg,
            system_prompt=WHY_NOT_TOP10_SYSTEM,
            model_id=model_id,
            temperature=0.3,
            max_tokens=200,
        )
        return _parse_bullets(raw, max_bullets=3)
    except Exception as e:
        logger.warning("Why not top 10 generation failed: %s", e)
        return ["Below threshold on one or more dimensions."]


def rank10_summary_from_candidate(scores_with_evidence: dict[str, Any] | None) -> str:
    """Build a short summary of #10's scores for comparison."""
    if not scores_with_evidence or not isinstance(scores_with_evidence, dict):
        return "N/A"
    dims = scores_with_evidence.get("dimensions") or {}
    parts = [f"{k}: {d.get('score', '?')}/5" for k, d in dims.items() if isinstance(d, dict)]
    return "; ".join(parts) if parts else "N/A"

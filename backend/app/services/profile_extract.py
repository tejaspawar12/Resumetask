"""Extract structured profile from cleaned resume text via Claude."""
import json
import logging
import re
from typing import Any

from app.schemas.profile import StructuredProfile, validate_profile
from app.services.bedrock import EXTRACTION_SYSTEM, invoke_claude

logger = logging.getLogger(__name__)

# Approximate token limit for Claude input; leave room for system + response
MAX_RESUME_CHARS = 80_000


def _truncate_text(text: str, max_chars: int = MAX_RESUME_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Truncated for length.]"


def _extract_json_from_response(raw: str) -> dict[str, Any] | None:
    """Try to parse JSON from model output; strip markdown code blocks if present."""
    raw = raw.strip()
    # Remove optional markdown code block
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def extract_profile(
    cleaned_text: str,
    model_id: str | None = None,
) -> tuple[StructuredProfile | None, str | None]:
    """
    Call Claude to extract structured profile from resume text.
    Returns (profile, error_message). error_message is set on failure or incomplete.
    """
    if not cleaned_text or not cleaned_text.strip():
        return None, "Empty resume text"

    user_message = "Candidate resume content below.\n\n" + _truncate_text(cleaned_text)

    for attempt in range(2):
        try:
            response = invoke_claude(
                user_message=user_message,
                system_prompt=EXTRACTION_SYSTEM,
                model_id=model_id,
                temperature=0.1,
                max_tokens=4096,
            )
        except Exception as e:
            logger.warning("Bedrock extraction attempt %s failed: %s", attempt + 1, e)
            if attempt == 1:
                return None, f"Extraction failed: {e!s}"
            continue

        data = _extract_json_from_response(response)
        if not data:
            if attempt == 0:
                user_message = "Your previous response was not valid JSON. Respond with a single JSON object only, no markdown or extra text."
                continue
            return None, "Extraction incomplete: invalid JSON"

        profile, errors = validate_profile(data)
        if profile is not None:
            return profile, None
        if attempt == 1:
            return None, "Extraction incomplete: " + "; ".join(errors[:3])

        user_message = (
            "Your previous response must be valid JSON with fields: years_of_experience, roles_and_companies, skills_tech_stack, "
            "ai_ml_llm_experience, projects, impact_metrics, ownership_leadership, links, education, summary_or_bio. "
            "Candidate resume content below.\n\n" + _truncate_text(cleaned_text)
        )

    return None, "Extraction incomplete"

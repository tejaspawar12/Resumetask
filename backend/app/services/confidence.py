"""Computed confidence (high/medium/low) from profile + word count (Phase 4)."""
from typing import Any


def compute_confidence(
    profile: dict[str, Any] | None,
    word_count: int | None,
) -> str:
    """
    Deterministic confidence from: word_count, impact_metrics count, links, roles with duration.
    Returns "high", "medium", or "low". Map 0-100 score: >=70 high, 40-69 medium, <40 low.
    """
    score = 50
    if word_count is not None:
        if word_count >= 500:
            score += 15
        elif word_count >= 200:
            score += 5
        elif word_count < 100:
            score -= 20
    if not profile:
        return _score_to_label(score)
    metrics = profile.get("impact_metrics") or []
    if len(metrics) >= 3:
        score += 15
    elif len(metrics) >= 1:
        score += 5
    else:
        score -= 10
    links = profile.get("links")
    if isinstance(links, dict):
        has_any = any(links.get(k) for k in ("github", "portfolio", "linkedin") if links.get(k))
        if has_any:
            score += 10
    roles = profile.get("roles_and_companies") or []
    with_duration = 0
    for r in roles:
        if isinstance(r, dict) and r.get("duration"):
            with_duration += 1
    if roles and with_duration >= len(roles) / 2:
        score += 5
    return _score_to_label(score)


def _score_to_label(score: float) -> str:
    score = max(0, min(100, score))
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"

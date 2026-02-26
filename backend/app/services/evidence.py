"""Build evidence snippets from structured profile for Judge (Phase 4)."""
from typing import Any


def build_evidence_from_profile(profile: dict[str, Any]) -> dict[str, list[str]]:
    """
    Derive evidence snippets per dimension from structured_profile (v1: profile only).
    Returns dict with keys: systems, product, ai, clarity, shipping. Each value is a list of strings.
    Judge will use only these; no raw resume.
    """
    out: dict[str, list[str]] = {
        "systems": [],
        "product": [],
        "ai": [],
        "clarity": [],
        "shipping": [],
    }

    # Ownership/leadership -> systems
    for item in (profile.get("ownership_leadership") or []):
        if item and isinstance(item, str):
            out["systems"].append(item.strip())

    # Roles: highlights (first per role) -> product/shipping/systems by keyword
    for r in (profile.get("roles_and_companies") or []):
        if not isinstance(r, dict):
            continue
        role_name = (r.get("role") or "").strip()
        company = (r.get("company") or "").strip()
        if role_name or company:
            out["clarity"].append(f"{role_name} at {company}.")
        for h in (r.get("highlights") or [])[:2]:
            if h and isinstance(h, str):
                h = h.strip()
                if "system" in h.lower() or "architecture" in h.lower() or "scale" in h.lower():
                    out["systems"].append(h)
                elif "product" in h.lower() or "user" in h.lower() or "metric" in h.lower():
                    out["product"].append(h)
                else:
                    out["shipping"].append(h)

    # AI/ML experience -> ai
    ai_obj = profile.get("ai_ml_llm_experience")
    if isinstance(ai_obj, dict):
        for d in (ai_obj.get("details") or []):
            if d and isinstance(d, str):
                out["ai"].append(d.strip())
        for p in (ai_obj.get("projects") or []):
            if p and isinstance(p, str):
                out["ai"].append(p.strip())
    for p in (profile.get("projects") or [])[:5]:
        if isinstance(p, dict):
            name = (p.get("name") or "").strip()
            impact = (p.get("impact") or "").strip()
            if impact:
                out["shipping"].append(f"{name}: {impact}")
            if name and "AI" in name or "ML" in name or "LLM" in name:
                out["ai"].append(f"{name}: {impact}" if impact else name)

    # Impact metrics -> shipping
    for m in (profile.get("impact_metrics") or []):
        if m and isinstance(m, str):
            out["shipping"].append(m.strip())

    # Summary/bio -> clarity (short only)
    summary = (profile.get("summary_or_bio") or "").strip()
    if summary and len(summary) < 400:
        out["clarity"].append(summary)

    # Dedupe and limit per dimension
    for key in out:
        seen = set()
        unique = []
        for s in out[key]:
            if s and s not in seen:
                seen.add(s)
                unique.append(s)
        out[key] = unique[:10]
    return out

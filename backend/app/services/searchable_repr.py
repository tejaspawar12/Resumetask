"""Build searchable representation from structured profile for embedding (Phase 3)."""
from typing import Any

# Max length for summary we use as-is; longer we replace with generated line
SUMMARY_MAX_CHARS = 500


def build_searchable_representation(profile: dict[str, Any]) -> str:
    """
    Build the exact text to embed per plan §5A.2.
    Components: 1–2 line summary, roles (role at company + 1 highlight), skills, top 3 projects, impact metrics.
    Excludes: contact info, address, long education block.
    """
    parts: list[str] = []

    # 1. 1–2 line summary
    summary = (profile.get("summary_or_bio") or "").strip()
    if summary and len(summary) <= SUMMARY_MAX_CHARS:
        parts.append(summary)
    else:
        # Generate one sentence from first role + skills
        roles = profile.get("roles_and_companies") or []
        skills = profile.get("skills_tech_stack") or []
        if roles and isinstance(roles, list) and len(roles) > 0:
            r = roles[0]
            if isinstance(r, dict):
                role_name = r.get("role") or ""
                company = r.get("company") or ""
                line = f"{role_name} at {company}." if role_name or company else ""
            else:
                line = ""
        else:
            line = ""
        if skills:
            skill_str = ", ".join(str(s) for s in skills[:5])
            line = f"{line} Skills: {skill_str}." if line else f"Skills: {skill_str}."
        if line:
            parts.append(line)
    parts.append("")

    # 2. Roles: one line per role with one highlight
    role_list = profile.get("roles_and_companies") or []
    if isinstance(role_list, list):
        for r in role_list:
            if not isinstance(r, dict):
                continue
            role_name = r.get("role") or ""
            company = r.get("company") or ""
            highlights = r.get("highlights") or []
            first_highlight = highlights[0] if highlights else "N/A"
            if isinstance(first_highlight, str):
                pass
            else:
                first_highlight = "N/A"
            parts.append(f"{role_name} at {company}. Highlight: {first_highlight}.")

    # 3. Skills list
    skills = profile.get("skills_tech_stack") or []
    if skills:
        parts.append(", ".join(str(s) for s in skills))

    # 4. Top 3 projects: name + impact
    projects = profile.get("projects") or []
    if isinstance(projects, list):
        for p in projects[:3]:
            if not isinstance(p, dict):
                continue
            name = p.get("name") or ""
            impact = p.get("impact") or ""
            parts.append(f"{name}: {impact}.")

    # 5. Impact metrics
    metrics = profile.get("impact_metrics") or []
    if metrics:
        parts.append(", ".join(str(m) for m in metrics))

    return "\n".join(p for p in parts if p).strip()

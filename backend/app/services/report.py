"""Generate HTML report for a run (Phase 9)."""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models import Candidate, Run


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _format_ts(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def build_report_html(run: Run, candidates: list[Candidate]) -> str:
    """Build full HTML report: cover, shortlist+backups table, per-candidate sections."""
    run_id = str(run.id)
    created = _format_ts(run.created_at)
    total = len(candidates)
    top5_ids = run.top_5_percent_ids or []
    backup_ids = run.backup_ids or []
    top5_count = len(top5_ids)
    backup_count = len(backup_ids)

    # Sort: top 5% by rank, then backups by rank, then rest by embedding_rank
    by_id = {c.candidate_id: c for c in candidates}
    ordered: list[Candidate] = []
    for cid in top5_ids:
        if cid in by_id:
            ordered.append(by_id[cid])
    for cid in backup_ids:
        if cid in by_id and by_id[cid] not in ordered:
            ordered.append(by_id[cid])
    for c in candidates:
        if c not in ordered:
            ordered.append(c)
    ordered.sort(key=lambda c: (c.rank if c.rank is not None else 99999, c.embedding_rank or 99999))

    html_parts: list[str] = []
    html_parts.append(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Run Report</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;} "
        "table{border-collapse:collapse;width:100%;} th,td{border:1px solid #ddd;padding:8px;text-align:left;} "
        "th{background:#f5f5f5;} .section{margin-top:2rem;} h1,h2,h3{margin-top:1.5rem;}</style></head><body>"
    )
    # Cover
    html_parts.append("<div class='section'>")
    html_parts.append(f"<h1>AI Applicant Ranking — Run Report</h1>")
    html_parts.append(f"<p><strong>Run ID:</strong> {_esc(run_id)}</p>")
    html_parts.append(f"<p><strong>Date:</strong> {_esc(created)}</p>")
    html_parts.append(f"<p><strong>Total candidates:</strong> {total}</p>")
    html_parts.append(f"<p><strong>Top 5%:</strong> {top5_count} &nbsp; <strong>Backups:</strong> {backup_count}</p>")
    jd = (run.role_criteria_text or "").strip()
    if jd:
        jd_esc = _esc(jd[:500] + ("…" if len(jd) > 500 else ""))
        html_parts.append("<p><strong>Ranking for (role / job criteria):</strong></p>")
        html_parts.append(f"<p style='white-space:pre-wrap;background:#f9f9f9;padding:0.5rem;border-radius:4px;'>{jd_esc}</p>")
    else:
        html_parts.append("<p><strong>Ranking for:</strong> Default role criteria (Senior Software Engineer).</p>")
    html_parts.append("</div>")

    # Shortlist + backups table
    shortlist_and_backups = [c for c in ordered if c.shortlist_status in ("top_5", "backup")]
    if shortlist_and_backups:
        html_parts.append("<div class='section'><h2>Shortlist &amp; Backups</h2>")
        html_parts.append(
            "<table><thead><tr><th>Filename</th><th>Status</th><th>Rank</th><th>Final score</th>"
            "<th>Systems</th><th>Product</th><th>AI</th><th>Clarity</th><th>Shipping</th><th>Risk flags</th></tr></thead><tbody>"
        )
        for c in shortlist_and_backups:
            scores = c.scores_with_evidence if isinstance(c.scores_with_evidence, dict) else {}
            dims = scores.get("dimensions") or {}
            overall = scores.get("overall_score")
            status_label = "Top 5%" if c.shortlist_status == "top_5" else "Backup"
            flags = c.risk_flags if isinstance(c.risk_flags, list) else []
            html_parts.append("<tr>")
            html_parts.append(f"<td>{_esc(c.filename or c.candidate_id)}</td>")
            html_parts.append(f"<td>{_esc(status_label)}</td>")
            html_parts.append(f"<td>{c.rank if c.rank is not None else '—'}</td>")
            html_parts.append(f"<td>{overall if overall is not None else '—'}</td>")
            for dim in ["systems", "product", "ai", "clarity", "shipping"]:
                s = dims.get(dim, {}).get("score")
                html_parts.append(f"<td>{s if s is not None else '—'}</td>")
            html_parts.append(f"<td>{_esc(', '.join(flags) if flags else '—')}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody></table></div>")

    # Per-candidate sections (shortlist + backups only)
    for c in shortlist_and_backups:
        html_parts.append("<div class='section'>")
        html_parts.append(f"<h2>{_esc(c.filename or c.candidate_id)}</h2>")
        if c.shortlist_status == "top_5" and c.why_shortlisted:
            html_parts.append("<h3>Why shortlisted</h3><ul>")
            for b in c.why_shortlisted:
                html_parts.append(f"<li>{_esc(b)}</li>")
            html_parts.append("</ul>")
        if c.shortlist_status == "backup" and c.why_not_top_10:
            html_parts.append("<h3>Why this candidate didn't make top 10</h3><ul>")
            for b in c.why_not_top_10:
                html_parts.append(f"<li>{_esc(b)}</li>")
            html_parts.append("</ul>")
        scores = c.scores_with_evidence if isinstance(c.scores_with_evidence, dict) else {}
        dims = scores.get("dimensions") or {}
        if dims:
            html_parts.append("<h3>Score breakdown</h3><ul>")
            for dim_name, label in [
                ("systems", "Systems thinking"),
                ("product", "Product judgment"),
                ("ai", "Applied AI fluency"),
                ("clarity", "Clarity"),
                ("shipping", "Bias toward shipping"),
            ]:
                d = dims.get(dim_name) or {}
                sc = d.get("score")
                ev = d.get("evidence") or []
                html_parts.append(f"<li><strong>{_esc(label)}:</strong> {sc if sc is not None else '—'}/5")
                if ev:
                    html_parts.append("<ul>")
                    for q in ev[:3]:
                        html_parts.append(f"<li class='evidence'><em>{_esc(str(q)[:300])}</em></li>")
                    html_parts.append("</ul>")
                html_parts.append("</li>")
            html_parts.append("</ul>")
        if c.risk_flags and isinstance(c.risk_flags, list):
            html_parts.append("<p><strong>Risk flags:</strong> " + _esc(", ".join(c.risk_flags)) + "</p>")
        html_parts.append("</div>")

    html_parts.append("</body></html>")
    return "".join(html_parts)

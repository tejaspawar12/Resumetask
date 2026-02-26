"""Generate synthetic demo resume PDFs (in-memory) for POST /runs/demo. Phase 7.

Phase 10: Demo data is synthetic/anonymized only — no real names, addresses, or contact info.
"""
from __future__ import annotations

import io
from typing import List, Tuple

import fitz  # PyMuPDF


def _make_pdf(title: str, body_lines: List[str]) -> bytes:
    """Create a minimal one-page PDF with title and body text. Synthetic only."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    y = 72
    page.insert_text((72, y), title, fontsize=16, fontname="helv")
    y += 28
    for line in body_lines:
        if y > 750:
            break
        page.insert_text((72, y), line[:90], fontsize=11, fontname="helv")
        y += 18
    if hasattr(doc, "write"):
        pdf_bytes = doc.write()
    else:
        buf = io.BytesIO()
        doc.save(buf, garbage=4, deflate=True)
        pdf_bytes = buf.getvalue()
    doc.close()
    return pdf_bytes


def get_demo_resume_pdfs() -> List[Tuple[str, bytes]]:
    """
    Return a list of (filename, pdf_bytes) for demo runs.
    All content is synthetic/anonymized (Phase 10).
    """
    return [
        (
            "demo_resume_systems_focus.pdf",
            _make_pdf(
                "Senior Software Engineer — Demo A",
                [
                    "Experience: 6 years backend and distributed systems.",
                    "Led migration to event-driven architecture; reduced p99 by 40%.",
                    "Strong systems thinking: design docs, runbooks, on-call.",
                    "Tech: Python, Go, AWS, Kafka, PostgreSQL.",
                    "Shipped 3 major features in 12 months; bias toward shipping.",
                ],
            ),
        ),
        (
            "demo_resume_product_ai.pdf",
            _make_pdf(
                "Senior Software Engineer — Demo B",
                [
                    "Product-minded engineer; 5 years at product companies.",
                    "Applied ML: built recommendation and ranking models in production.",
                    "Fluency in applied AI: fine-tuning, RAG, evaluation pipelines.",
                    "Clear communicator: RFCs, stakeholder updates, docs.",
                    "Shipped ML features end-to-end; focus on impact.",
                ],
            ),
        ),
        (
            "demo_resume_fullstack.pdf",
            _make_pdf(
                "Senior Software Engineer — Demo C",
                [
                    "Full-stack and ML; 4 years experience.",
                    "Systems: microservices, APIs, data pipelines.",
                    "Product: worked with PMs on scope and tradeoffs.",
                    "Applied AI: internal tools using LLMs and embeddings.",
                    "Clarity: technical writing and mentoring.",
                ],
            ),
        ),
    ]

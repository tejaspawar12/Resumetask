"""Extract and clean text from PDF bytes (in-memory)."""
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.services.clean_text import clean_text

CLEANED_TEXT_MAX_BYTES = 200_000  # don't store in DB if larger
MIN_WORDS = 50


@dataclass
class ExtractResult:
    cleaned_text: str | None  # None if empty/failed or too large to store
    word_count: int
    error: str | None  # set on failure or insufficient content
    store_cleaned_text: bool  # False if len > CLEANED_TEXT_MAX_BYTES


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> ExtractResult:
    """
    Extract text from PDF bytes, clean it, compute word count.
    Returns what to store: cleaned_text only if length < 200 KB; always word_count.
    Sets error if extraction fails or word_count < 50.
    """
    if not pdf_bytes or len(pdf_bytes) < 5:
        return ExtractResult(
            cleaned_text=None,
            word_count=0,
            error="Empty or invalid PDF",
            store_cleaned_text=False,
        )
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        raw_parts = []
        for page in doc:
            raw_parts.append(page.get_text())
        doc.close()
        raw = "\n".join(raw_parts)
    except Exception as e:
        return ExtractResult(
            cleaned_text=None,
            word_count=0,
            error=f"Could not extract text: {e!s}",
            store_cleaned_text=False,
        )

    cleaned = clean_text(raw)
    words = cleaned.split()
    word_count = len(words)

    if word_count < MIN_WORDS:
        return ExtractResult(
            cleaned_text=None,
            word_count=word_count,
            error="Insufficient content",
            store_cleaned_text=False,
        )

    # Size guard: store in DB only if under limit
    cleaned_bytes = cleaned.encode("utf-8")
    store_cleaned_text = len(cleaned_bytes) < CLEANED_TEXT_MAX_BYTES
    value_to_store = cleaned if store_cleaned_text else None

    return ExtractResult(
        cleaned_text=value_to_store,
        word_count=word_count,
        error=None,
        store_cleaned_text=store_cleaned_text,
    )

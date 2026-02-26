"""Normalize and clean raw extracted PDF text."""
import re


def clean_text(raw: str) -> str:
    """
    Normalize encoding, collapse whitespace, remove page artifacts.
    Input: raw string from PDF extraction.
    Output: cleaned string (UTF-8, single newlines between sections).
    """
    if not raw or not isinstance(raw, str):
        return ""

    # Normalize encoding: replace or drop invalid/weird chars
    text = raw.encode("utf-8", errors="replace").decode("utf-8")

    # Common header/footer and page patterns to remove
    text = re.sub(r"\bPage\s+\d+\s+of\s+\d+\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bConfidential\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d+$", "", text, flags=re.MULTILINE)  # standalone page numbers
    text = re.sub(r"\f", "\n", text)  # form feed to newline

    # Collapse multiple newlines to at most two (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces to one
    text = re.sub(r"[ \t]+", " ", text)
    # Trim each line
    lines = [line.strip() for line in text.splitlines()]
    # Drop empty lines at start/end, keep internal empty lines as paragraph breaks
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    text = "\n".join(lines)
    return text.strip()

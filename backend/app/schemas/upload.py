"""Pydantic schemas for upload API."""
from pydantic import BaseModel


class UploadErrorItem(BaseModel):
    file: str
    reason: str


class UploadResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[UploadErrorItem]
    duplicate_skipped: int = 0

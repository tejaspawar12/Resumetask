"""Bedrock Titan Embeddings: embed text, cosine similarity (Phase 3)."""

# Default role/criteria text when run has none (stored in runs.role_criteria_text after use)
DEFAULT_ROLE_CRITERIA = (
    "Senior Software Engineer. We value: systems thinking, product judgment, "
    "applied AI/ML fluency, clarity, bias toward shipping."
)

import json
import logging
import math
import time
from typing import Any

from botocore.exceptions import ClientError

from app.config import settings
from app.services.bedrock import get_bedrock_runtime

logger = logging.getLogger(__name__)

BATCH_SIZE = 25
MAX_RETRIES = 5


def embed_text(text: str, model_id: str | None = None) -> list[float]:
    """Single text → embedding vector via Titan. Retries on throttle."""
    model_id = model_id or settings.embedding_model_id
    client = get_bedrock_runtime()
    body = json.dumps({"inputText": text[:30_000]})  # truncate very long input
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            out = json.loads(response["body"].read())
            emb = out.get("embedding")
            if emb is None:
                emb = out.get("embeddingsByType", {}).get("float")
            return emb or []
        except ClientError as e:
            last_error = e
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("ThrottlingException", "ServiceQuotaExceededException"):
                delay = 2 ** attempt
                logger.warning("Embedding throttle, retry in %ss", delay)
                time.sleep(delay)
            else:
                raise
    if last_error:
        raise last_error
    return []


def embed_texts_batch(texts: list[str], model_id: str | None = None) -> list[list[float]]:
    """Embed multiple texts sequentially in small batches to avoid rate limits. Returns list of vectors."""
    model_id = model_id or settings.embedding_model_id
    results: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        for t in chunk:
            try:
                vec = embed_text(t, model_id=model_id)
                results.append(vec)
            except Exception as e:
                logger.warning("Embed failed for one text: %s", e)
                results.append([])  # placeholder so length matches
        if i + BATCH_SIZE < len(texts):
            time.sleep(0.5)
    return results


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0 if either has no norm."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

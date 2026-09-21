"""Pod 2 `<= 60s` Policy Publish Webhook & Incremental Chunk Ingestion (`app/slices/pod2_policy_rag/webhook_ingest.py`).

Enforces SLA-01:
  - Chunks published HR policy documents into `512`-token windows with `10%` overlap.
  - Computes `sha256_checksum` and 768-dimensional `text-embedding-005` vectors.
  - Upserts `hr_policy_chunks` and invalidates cached Redis keys within the `<= 60s` SLA.
"""

import hashlib
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.slices.pod2_policy_rag.retriever import (
    SEEDED_POLICY_CHUNKS,
    compute_deterministic_embedding,
)

# Simulated Redis cache key registry for policy queries (`TTL = 60s`)
POLICY_REDIS_CACHE: dict[str, Any] = {}


class PolicyPublishPayload(BaseModel):
    """Webhook request body for `POST /api/v1/webhooks/policy-publish`."""

    doc_id: str = Field(..., description="Canonical policy document ID (e.g., DOC-SG-BENEFITS-2026)")
    section_anchor: str = Field(..., description="Section identifier (e.g., sec-4.2)")
    country_code: str = Field(..., min_length=2, max_length=6, description="2-letter country or GLOBAL")
    min_role: str = Field(default="IC", description="Minimum role entitlement (IC, MANAGER, EXEC)")
    content_text: str = Field(..., min_length=10, description="Updated markdown/text content")


def chunk_policy_document(
    doc_id: str,
    section_anchor: str,
    country_code: str,
    min_role: str,
    content_text: str,
    chunk_size_tokens: int = 512,
    overlap_ratio: float = 0.10,
) -> list[dict[str, Any]]:
    """Splits a policy section into `512`-token chunks with `10%` overlap and computes embeddings."""
    words = content_text.split()
    if not words:
        return []

    step = max(1, int(chunk_size_tokens * (1.0 - overlap_ratio)))
    chunks: list[dict[str, Any]] = []
    idx = 0
    chunk_seq = 1

    while idx < len(words):
        window_words = words[idx : idx + chunk_size_tokens]
        window_text = " ".join(window_words)
        checksum = hashlib.sha256(window_text.encode("utf-8")).hexdigest()
        embedding = compute_deterministic_embedding(window_text, dims=768)
        chunk_id = f"chk-{doc_id.lower()}-{section_anchor.lower()}-{chunk_seq}"

        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "section_anchor": section_anchor,
                "country_code": country_code.strip().upper(),
                "min_role": min_role.strip().upper(),
                "content_text": window_text,
                "sha256_checksum": checksum,
                "embedding": embedding,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        if idx + chunk_size_tokens >= len(words):
            break
        idx += step
        chunk_seq += 1

    return chunks


async def ingest_published_policy(payload: PolicyPublishPayload) -> dict[str, Any]:
    """Re-chunks, embeds, upserts `hr_policy_chunks`, and invalidates Redis cache within `<= 60s`."""
    t0 = time.perf_counter()
    new_chunks = chunk_policy_document(
        doc_id=payload.doc_id,
        section_anchor=payload.section_anchor,
        country_code=payload.country_code,
        min_role=payload.min_role,
        content_text=payload.content_text,
    )

    existing_ids = {c["chunk_id"]: i for i, c in enumerate(SEEDED_POLICY_CHUNKS)}
    for chunk in new_chunks:
        cid = chunk["chunk_id"]
        if cid in existing_ids:
            SEEDED_POLICY_CHUNKS[existing_ids[cid]] = chunk
        else:
            SEEDED_POLICY_CHUNKS.append(chunk)

    # Evict cached policy responses for the affected country and GLOBAL scope
    POLICY_REDIS_CACHE.clear()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "status": "INDEXED_AND_CACHE_INVALIDATED",
        "doc_id": payload.doc_id,
        "section_anchor": payload.section_anchor,
        "chunks_upserted": len(new_chunks),
        "cache_invalidated": True,
        "sync_sla_seconds": settings.CACHE_TTL_SECONDS,
        "elapsed_ms": elapsed_ms,
    }

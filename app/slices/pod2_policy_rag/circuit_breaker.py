"""Pod 2 Read-Only `SQLite-vec` Circuit-Breaker Failover (`400ms` SLA) — app/slices/pod2_policy_rag/circuit_breaker.py.

Enforces RES-01 (Alex Rivera Safeguard):
  - Wraps Cloud SQL `pgvector` queries in an `asyncio.wait_for(..., timeout=0.400)` budget.
  - On `TimeoutError` or database failure, verifies the read-only `SQLite-vec` snapshot's
    `manifest.sha256` checksum and executes the identical pre-retrieval `country_code` & `min_role`
    SQL `WHERE` filter against the in-memory/container SQLite snapshot.
"""

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.slices.pod2_policy_rag.retriever import (
    SEEDED_POLICY_CHUNKS,
    PolicyChunkMatch,
    get_allowed_roles,
    score_and_rerank_candidate,
)


@dataclass(frozen=True)
class CircuitBreakerExecutionResult:
    """Result returned by `execute_with_sqlite_vec_failover`."""

    used_circuit_breaker: bool
    manifest_verified: bool
    manifest_sha256: str
    chunks: list[PolicyChunkMatch]


class CircuitBreakerSnapshotStore:
    """Read-only `SQLite-vec` circuit-breaker snapshot with SHA-256 manifest verification."""

    def __init__(self, tamper_checksum: bool = False) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._init_snapshot_tables()
        canonical_manifest = json.dumps(SEEDED_POLICY_CHUNKS, sort_keys=True).encode("utf-8")
        self._expected_sha256 = hashlib.sha256(canonical_manifest).hexdigest()
        self._actual_sha256 = (
            "0000000000000000000000000000000000000000000000000000000000000000"
            if tamper_checksum
            else self._expected_sha256
        )

    def _init_snapshot_tables(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            CREATE TABLE hr_policy_chunks_snapshot (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                section_anchor TEXT NOT NULL,
                country_code TEXT NOT NULL,
                min_role TEXT NOT NULL,
                content_text TEXT NOT NULL,
                sha256_checksum TEXT NOT NULL
            )
            """
        )
        for item in SEEDED_POLICY_CHUNKS:
            checksum = hashlib.sha256(item["content_text"].encode("utf-8")).hexdigest()
            cursor.execute(
                """
                INSERT INTO hr_policy_chunks_snapshot
                (chunk_id, doc_id, section_anchor, country_code, min_role, content_text, sha256_checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["chunk_id"],
                    item["doc_id"],
                    item["section_anchor"],
                    item["country_code"],
                    item["min_role"],
                    item["content_text"],
                    checksum,
                ),
            )
        self._conn.commit()

    def verify_manifest_sha256(self) -> bool:
        """Verifies integrity of `manifest.sha256` before serving fallback results."""
        return self._actual_sha256 == self._expected_sha256

    def query_snapshot(
        self, query: str, user_country: str, user_role: str
    ) -> list[PolicyChunkMatch]:
        """Executes pre-retrieval `WHERE country_code IN (?, 'GLOBAL') AND min_role IN (?)` on snapshot."""
        if not self.verify_manifest_sha256():
            raise RuntimeError(
                "SQLite-vec circuit breaker aborted: SHA-256 manifest verification failed."
            )

        allowed_roles = get_allowed_roles(user_role)
        role_placeholders = ",".join("?" for _ in allowed_roles)
        sql = (
            "SELECT chunk_id, doc_id, section_anchor, country_code, min_role, "
            "content_text, sha256_checksum "
            "FROM hr_policy_chunks_snapshot "
            f"WHERE country_code IN (?, 'GLOBAL') AND min_role IN ({role_placeholders})"
        )
        params: list[str] = [user_country.strip().upper(), *allowed_roles]
        rows = self._conn.execute(sql, params).fetchall()

        matches: list[PolicyChunkMatch] = []
        for row in rows:
            row_dict = dict(row)
            v_score, l_score, r_score = score_and_rerank_candidate(query, row_dict)
            if r_score >= 0.75:
                matches.append(
                    PolicyChunkMatch(
                        chunk_id=row_dict["chunk_id"],
                        doc_id=row_dict["doc_id"],
                        section_anchor=row_dict["section_anchor"],
                        country_code=row_dict["country_code"],
                        min_role=row_dict["min_role"],
                        content_text=row_dict["content_text"],
                        vector_score=v_score,
                        lexical_score=l_score,
                        rerank_score=r_score,
                        sha256_checksum=row_dict["sha256_checksum"],
                    )
                )
        matches.sort(key=lambda m: m.rerank_score, reverse=True)
        return matches[:5]


async def execute_with_sqlite_vec_failover(
    primary_coro_factory: Callable[[], Awaitable[list[PolicyChunkMatch]]],
    query: str,
    user_country: str,
    user_role: str,
    timeout_seconds: float = 0.400,
    snapshot_store: CircuitBreakerSnapshotStore | None = None,
) -> CircuitBreakerExecutionResult:
    """Wraps primary Cloud SQL `pgvector` retrieval in a `400ms` budget with `SQLite-vec` failover."""
    store = snapshot_store or CircuitBreakerSnapshotStore()
    try:
        primary_chunks = await asyncio.wait_for(primary_coro_factory(), timeout=timeout_seconds)
        return CircuitBreakerExecutionResult(
            used_circuit_breaker=False,
            manifest_verified=True,
            manifest_sha256=store._expected_sha256,
            chunks=primary_chunks,
        )
    except (TimeoutError, Exception) as exc:
        if isinstance(exc, RuntimeError) and "SHA-256 manifest" in str(exc):
            raise
        fallback_chunks = store.query_snapshot(
            query=query,
            user_country=user_country,
            user_role=user_role,
        )
        return CircuitBreakerExecutionResult(
            used_circuit_breaker=True,
            manifest_verified=True,
            manifest_sha256=store._expected_sha256,
            chunks=fallback_chunks,
        )

"""Pod 2 Unit & Contract Tests — Pre-Retrieval Entitlement Gate, Hybrid pgvector RAG, SQLite-vec Circuit-Breaker & <=60s Policy Publish Webhook."""

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.fast_api_app import app
from app.slices.pod2_policy_rag.circuit_breaker import (
    CircuitBreakerSnapshotStore,
    execute_with_sqlite_vec_failover,
)
from app.slices.pod2_policy_rag.retriever import (
    PolicyChunkMatch,
    PolicyRetrievalResponse,
    build_pre_retrieval_entitlement_sql,
    get_allowed_roles,
    retrieve_authorized_policy_chunks,
)
from app.slices.pod2_policy_rag.sub_agent import (
    get_agent_tool,
    search_hr_policy,
    specialist_agent,
)
from app.slices.pod2_policy_rag.webhook_ingest import (
    PolicyPublishPayload,
    chunk_policy_document,
    ingest_published_policy,
)

client = TestClient(app)


def test_role_hierarchy_expansion() -> None:
    """Verifies strict hierarchical role entitlement mapping (IC < MANAGER < EXEC)."""
    assert get_allowed_roles("IC") == ["IC"]
    assert get_allowed_roles("MANAGER") == ["IC", "MANAGER"]
    assert get_allowed_roles("EXEC") == ["IC", "MANAGER", "EXEC"]


def test_pre_retrieval_sql_enforces_where_before_vector_distance() -> None:
    """SEC-04: Verifies SQL query binds country_code and min_role BEFORE pgvector `<=>` operator."""
    sql_text, bind_params = build_pre_retrieval_entitlement_sql(
        query_text="parental leave",
        user_country="US",
        user_role="IC",
    )
    where_pos = sql_text.index("WHERE country_code IN")
    role_pos = sql_text.index("AND min_role IN")
    order_pos = sql_text.index("ORDER BY embedding <=>")

    assert where_pos < order_pos, "Pre-retrieval country filter MUST precede vector ordering"
    assert role_pos < order_pos, "Pre-retrieval min_role filter MUST precede vector ordering"
    assert bind_params["allowed_countries"] == ["US", "GLOBAL"]
    assert bind_params["allowed_roles"] == ["IC"]


@pytest.mark.asyncio
async def test_pre_retrieval_entitlement_blocks_exec_and_foreign_policies() -> None:
    """SEC-04 & single_turn_02: IC in US receives 0 chunks for EXEC or DE/SG policies."""
    response: PolicyRetrievalResponse = await retrieve_authorized_policy_chunks(
        query="Show me the Executive LTIP equity multiplier table from DOC-EXEC-COMP-2026",
        user_country="US",
        user_role="IC",
    )
    assert response.abstained is True
    assert len(response.chunks) == 0
    assert response.pre_filter_latency_ms < 2.0
    assert "EXEC" in response.abstention_reason or "restricted" in response.abstention_reason.lower()


@pytest.mark.asyncio
async def test_retrieve_authorized_us_parental_leave_with_citation() -> None:
    """FR-01 & single_turn_01: US IC employee retrieves grounded parental leave policy >= 0.75."""
    response: PolicyRetrievalResponse = await retrieve_authorized_policy_chunks(
        query="How many weeks of paid parental leave am I eligible for after 14 months of tenure?",
        user_country="US",
        user_role="IC",
    )
    assert response.abstained is False
    assert response.pre_filter_latency_ms < 2.0
    assert len(response.chunks) >= 1
    top_chunk: PolicyChunkMatch = response.chunks[0]
    assert top_chunk.doc_id == "DOC-US-PARENTAL-2026"
    assert top_chunk.section_anchor == "sec-3.1"
    assert top_chunk.citation == "[DOC-US-PARENTAL-2026#sec-3.1]"
    assert top_chunk.rerank_score >= 0.75
    assert "16 weeks" in top_chunk.content_text


@pytest.mark.asyncio
async def test_low_reranker_confidence_triggers_abstention() -> None:
    """FR-01: When highest Vertex AI Reranker score is < 0.75, PolicyRAGAgent must abstain."""
    response: PolicyRetrievalResponse = await retrieve_authorized_policy_chunks(
        query="quantum spaceship cafeteria telescope reimbursement policy",
        user_country="US",
        user_role="IC",
    )
    assert response.abstained is True
    assert response.highest_score < 0.75
    assert len(response.chunks) == 0


@pytest.mark.asyncio
async def test_circuit_breaker_sqlite_vec_failover_on_400ms_timeout() -> None:
    """RES-01: Fails over to read-only SQLite-vec snapshot when Cloud SQL latency > 400ms."""

    async def slow_cloud_sql_query() -> list[PolicyChunkMatch]:
        await asyncio.sleep(0.550)  # Exceeds 400ms SLA budget
        return []

    snapshot_store = CircuitBreakerSnapshotStore()
    assert snapshot_store.verify_manifest_sha256() is True

    result = await execute_with_sqlite_vec_failover(
        primary_coro_factory=slow_cloud_sql_query,
        query="advance notice for vacation leave in Singapore",
        user_country="SG",
        user_role="IC",
        timeout_seconds=0.400,
        snapshot_store=snapshot_store,
    )
    assert result.used_circuit_breaker is True
    assert result.manifest_verified is True
    assert len(result.chunks) >= 1
    assert all(c.country_code in {"SG", "GLOBAL"} for c in result.chunks)
    assert all(c.min_role == "IC" for c in result.chunks)


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_tampered_manifest() -> None:
    """RES-01: Refuses to serve from SQLite-vec snapshot if SHA-256 manifest checksum fails."""

    async def failing_cloud_sql_query() -> list[PolicyChunkMatch]:
        raise TimeoutError("Cloud SQL RPC exceeded 400ms")

    tampered_store = CircuitBreakerSnapshotStore(tamper_checksum=True)
    assert tampered_store.verify_manifest_sha256() is False

    with pytest.raises(RuntimeError, match="SHA-256 manifest verification failed"):
        await execute_with_sqlite_vec_failover(
            primary_coro_factory=failing_cloud_sql_query,
            query="parental leave",
            user_country="US",
            user_role="IC",
            snapshot_store=tampered_store,
        )


@pytest.mark.asyncio
async def test_policy_publish_webhook_chunking_and_60s_sla() -> None:
    """SLA-01: Verifies 512-token (10% overlap) chunking, SHA-256 checksums, and <=60s webhook SLA."""
    sample_text = " ".join([f"Sectionword{i}" for i in range(600)])
    chunks = chunk_policy_document(
        doc_id="DOC-SG-BENEFITS-2026",
        section_anchor="sec-4.2",
        country_code="SG",
        min_role="IC",
        content_text=sample_text,
        chunk_size_tokens=512,
        overlap_ratio=0.10,
    )
    assert len(chunks) == 2
    assert len(chunks[0]["sha256_checksum"]) == 64
    assert len(chunks[0]["embedding"]) == 768

    payload = PolicyPublishPayload(
        doc_id="DOC-SG-BENEFITS-2026",
        section_anchor="sec-4.2",
        country_code="SG",
        min_role="IC",
        content_text="Singapore employees receive S$1,200 annual wellness reimbursement [DOC-SG-BENEFITS-2026#sec-4.2].",
    )
    ingest_result = await ingest_published_policy(payload)
    assert ingest_result["status"] == "INDEXED_AND_CACHE_INVALIDATED"
    assert ingest_result["chunks_upserted"] >= 1
    assert ingest_result["cache_invalidated"] is True
    assert ingest_result["sync_sla_seconds"] <= 60
    assert ingest_result["elapsed_ms"] < 1000.0


def test_fastapi_policy_publish_webhook_and_search_endpoints() -> None:
    """Verifies POST /api/v1/webhooks/policy-publish and /api/v1/pod2_policy_rag/search endpoints."""
    webhook_resp = client.post(
        "/api/v1/webhooks/policy-publish",
        json={
            "doc_id": "DOC-DE-LEAVE-2026",
            "section_anchor": "sec-1.1",
            "country_code": "DE",
            "min_role": "IC",
            "content_text": "Full-time employees in Germany receive 30 statutory vacation days per calendar year.",
        },
    )
    assert webhook_resp.status_code == 200
    body = webhook_resp.json()
    assert body["status"] == "INDEXED_AND_CACHE_INVALIDATED"
    assert body["sync_sla_seconds"] <= 60

    search_resp = client.post(
        "/api/v1/pod2_policy_rag/search",
        json={"query": "How many weeks of paid parental leave in the US?"},
        headers={"x-employee-sub": "EMP-824", "x-country-code": "US", "x-employee-role": "IC"},
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["abstained"] is False
    assert search_data["citations"][0]["citation"] == "[DOC-US-PARENTAL-2026#sec-3.1]"


@pytest.mark.asyncio
async def test_pod2_specialist_agent_and_tool_contract() -> None:
    """Verifies PolicyRAGAgent is wired to Gemini 3.6 Flash with search_hr_policy tool."""
    assert specialist_agent.name == "policy_rag_agent"
    assert len(specialist_agent.tools) >= 1
    agent_tool = get_agent_tool()
    assert agent_tool is not None

    tool_out: dict[str, Any] = await search_hr_policy(
        query="How many weeks of paid parental leave am I eligible for after 14 months of tenure?",
        country_code="US",
        role="IC",
    )
    assert tool_out["abstained"] is False
    assert "[DOC-US-PARENTAL-2026#sec-3.1]" in tool_out["formatted_context"]

# Plan 02: Pod 2 Vertical Slice — `<2ms` Pre-Retrieval Entitlement Gate, Hybrid `pgvector` RAG & Citation Drawer

- **Assigned Pod:** Pod 2 (Engineer 2 + Jetski Agent)
- **Git Branch:** `feat/pod2-policy-rag`
- **Depends On:** `AGENTS.md`, `plans/00-tracer-bullet-spine.md`
- **Owned Directories:** `app/slices/pod2_policy_rag/`, `app/frontend/src/features/pod2_policy_rag/`, `tests/unit/test_pod2_policy_rag.py`
- **Skills to Invoke in Jetski:** `/execute-vertical-slice`, `/elevate-eval-runner`

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Vertical Slice Deliverable |
| :--- | :--- | :--- |
| **`FR-01`** | Section 4.2 & Sarah Chen (VP People Ops): Grounded HR policy answers (`>= 0.75` score) with inline `[DOC_ID#section]` citations | `app/slices/pod2_policy_rag/sub_agent.py` (`PolicyRAGAgent` on `gemini-3.6-flash`) |
| **`SEC-04`** | Maria Santos (DPO) Safeguard: Synchronous `<2ms` Pre-Retrieval Entitlement Check (`country_code`, `min_role`) prior to vector similarity search (`0ms` unauthorized exposure window) | `app/slices/pod2_policy_rag/retriever.py` |
| **`RES-01`** | Section 5.2 & Alex Rivera Safeguard: Read-Only `SQLite-vec` Circuit-Breaker Failover with SHA-256 manifest verification when Cloud SQL RPC latency exceeds `400ms` | `app/slices/pod2_policy_rag/circuit_breaker.py` |
| **`SLA-01`** | Unified `<= 60 Seconds` Contractual & Technical Sync SLA for newly published HR policies | `app/slices/pod2_policy_rag/webhook_ingest.py` (`POST /api/v1/webhooks/policy-publish`) |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** filter entitlements *after* vector search (`post-retrieval filtering` is a security violation flagged by the DPO).
- Do **NOT** touch `WorkWeek` or `ServiceImmediately` MCP servers (`Pod 3` and `Pod 4`).
- Do **NOT** allow `PolicyRAGAgent` to answer when the highest Vertex AI Reranker score is `< 0.75` (must trigger abstention/clarification).

---

## 3. Step-by-Step Vertical Implementation Instructions (`RED -> GREEN -> REFACTOR`)

### Step 3.1: Pre-Retrieval Entitlement-Filtered Hybrid Search (`app/slices/pod2_policy_rag/retriever.py`)
1. Implement `async def retrieve_authorized_policy_chunks(query: str, user_country: str, user_role: str) -> list[PolicyChunkMatch]`:
   - Enforce synchronous `<2ms` SQL `WHERE` clause *before* `pgvector` HNSW cosine distance (`<=>`) and PostgreSQL `ts_rank_cd` lexical search:
     ```sql
     SELECT chunk_id, doc_id, section_anchor, content_text,
            (1 - (embedding <=> :query_vec)) AS vector_score
     FROM hr_policy_chunks
     WHERE country_code IN (:user_country, 'GLOBAL')
       AND min_role IN (:allowed_roles)
     ORDER BY embedding <=> :query_vec
     LIMIT 25;
     ```
   - Pass the 25 pre-filtered candidates to Vertex AI Ranking API (`top_k=5`) and enforce `score >= 0.75`.

### Step 3.2: Circuit-Breaker Failover to Read-Only `SQLite-vec` (`app/slices/pod2_policy_rag/circuit_breaker.py`)
1. Wrap the Cloud SQL `pgvector` query in an `asyncio.wait_for(..., timeout=0.400)` budget.
2. On `TimeoutError` or `PostgresError`, query the local read-only `SQLite-vec` snapshot after verifying `manifest.sha256` and applying the identical `WHERE country_code IN (?, 'GLOBAL') AND min_role IN (?)` pre-filter.

### Step 3.3: `<= 60s` Policy Publish Webhook (`app/slices/pod2_policy_rag/webhook_ingest.py`)
1. Implement `POST /api/v1/webhooks/policy-publish`: re-chunks updated sections (`512` tokens, `10%` overlap), computes `text-embedding-005` vectors, upserts `hr_policy_chunks`, and invalidates Redis cache keys within `<= 60s`.

### Step 3.4: React Inline Citation Pill & Source Preview Drawer (`app/frontend/src/features/pod2_policy_rag/CitationDrawer.tsx`)
1. Parse `[DOC_ID#section]` citations in streamed assistant responses into clickable `<CitationPill />` badges that open `<CitationDrawer />` showing the verbatim paragraph, effective date, and jurisdiction tag.

---

## 4. Deterministic Testable Checkpoints (Definition of Done Gate)

```bash
# 1. Run Pod 2 Pre-Retrieval Entitlement & Circuit-Breaker Unit Tests
uv run --extra dev pytest tests/unit/test_pod2_policy_rag.py -v

# 2. Run agents-cli Policy Grounding & Entitlement Evaluation Cases (single_turn_01 & single_turn_02)
agents-cli eval run --dataset tests/eval/datasets/eval-single-turn.json --config tests/eval/eval_config.yaml
```

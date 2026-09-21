# Plan 03: Pod 3 Vertical Slice — `WorkWeek` HRIS MCP (`50 RPS`), Two-Phase HITL Gate & Cloud Tasks Queue

- **Assigned Pod:** Pod 3 (Engineer 3 + Jetski Agent)
- **Git Branch:** `feat/pod3-workweek-hitl`
- **Depends On:** `AGENTS.md`, `plans/00-tracer-bullet-spine.md`
- **Owned Directories:** `app/slices/pod3_workweek_leave/`, `app/frontend/src/features/pod3_workweek_leave/`, `tests/unit/test_pod3_workweek_hitl.py`
- **Skills to Invoke in Jetski:** `/execute-vertical-slice`, `/adk-hitl-and-saga`, `/elevate-eval-runner`

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Vertical Slice Deliverable |
| :--- | :--- | :--- |
| **`FR-02` & `FR-03`** | Section 4.3 & Sarah Chen (VP People Ops): Read PTO/parental leave balances & submit leave requests via Two-Phase HITL Gate (`hitl_proposals`) | `app/slices/pod3_workweek_leave/mcp_tools.py` + `sub_agent.py` (`HRISActionAgent` on `gemini-3.6-flash`) |
| **`GOV-03`** | Section 3.3: Structural separation of `propose_leave_request` (Agent Tool) vs. `commit_leave_request` (Human REST Endpoint only) with `15-min TTL` and `SHA-256` idempotency key | `app/slices/pod3_workweek_leave/hitl_service.py` |
| **`RES-02`** | Alex Rivera (IT Director) Safeguard: Explicit `WorkWeek` Token-Bucket Throttling (`50 RPS` sustained / `100` burst) + `HTTP 429`/`5xx` Cloud Tasks retry queue (`ww-it-mutation-retry-queue`) | `app/slices/pod3_workweek_leave/workweek_client.py` |
| **`SLA-02`** | Unified `<= 60 Seconds` HRIS Webhook Cache Invalidation SLA | `app/slices/pod3_workweek_leave/router.py` (`POST /api/v1/webhooks/workweek`) |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** expose `commit_leave_request` in `HRISActionAgent.tools` (`LlmAgent` may ONLY call `get_leave_balance` and `propose_leave_request`).
- Do **NOT** touch `ServiceImmediately` IT ticketing or Saga rollback logic (`Pod 4`).
- Do **NOT** allow duplicate proposals for the same `(employee_id, tool_name, canonical_payload)` within a 15-minute window.

---

## 3. Step-by-Step Vertical Implementation Instructions (`RED -> GREEN -> REFACTOR`)

### Step 3.1: Token-Bucket Rate-Limited `WorkWeek` Client (`app/slices/pod3_workweek_leave/workweek_client.py`)
1. Initialize `workweek_limiter = AsyncLimiter(max_rate=50, time_period=1.0)` (`50 RPS` sustained).
2. Implement `async def get_leave_balance(employee_id: str) -> LeaveBalanceResponse` with Redis read-through caching (`TTL = 60s`).
3. Implement `async def commit_leave_to_workweek(proposal: HITLProposal) -> WorkWeekCommitResult`:
   - On HTTP `429` (reads `Retry-After` header) or `5xx` (`500`/`502`/`503`/`504`), transition `proposal.status = "QUEUED_RETRY"` and enqueue the idempotent payload to Google Cloud Tasks (`ww-it-mutation-retry-queue`, max 5 attempts, initial backoff `2s`, max `60s`).

### Step 3.2: Two-Phase `hitl_proposals` Repository (`app/slices/pod3_workweek_leave/hitl_service.py`)
1. Implement `async def propose_leave_request(employee_id: str, start_date: str, end_date: str, days: float, leave_type: str) -> dict`:
   - Compute `idempotency_key = sha256(f"{employee_id}:propose_leave_request:{start_date}:{end_date}:{days}:{leave_type}").hexdigest()`.
   - Persist `HITLProposal` (`status="PENDING"`, `expires_at=now() + 15m`) in PostgreSQL 16.
   - Return structured `hitl_card` JSON payload for SSE rendering.

### Step 3.3: FastAPI HITL Confirmation & Webhook Router (`app/slices/pod3_workweek_leave/router.py`)
1. Wire `POST /api/v1/hitl/confirm` to validate JWT `sub == proposal.employee_id`, check `expires_at > now()`, and call `commit_leave_to_workweek`.
2. Wire `POST /api/v1/webhooks/workweek` to evict `redis.delete(f"ww:balance:{employee_id}")` in `<60s`.

### Step 3.4: React Interactive `<HITLConfirmationCard />` (`app/frontend/src/features/pod3_workweek_leave/HITLConfirmationCard.tsx`)
1. Render the leave summary (`start_date`, `end_date`, `days`, `remaining_balance`), a live `15:00` countdown timer badge, and `[Confirm & Submit to WorkWeek]` / `[Cancel]` buttons with optimistic state locking.

---

## 4. Deterministic Testable Checkpoints (Definition of Done Gate)

```bash
# 1. Run Pod 3 Unit, Rate-Limit & PostgreSQL 16 HITL Proposal Tests
uv run --extra dev pytest tests/unit/test_pod3_workweek_hitl.py -v

# 2. Run agents-cli Multi-Turn HITL Gate Evaluation (multi_turn_01_workweek_leave_two_phase_hitl)
agents-cli eval run --dataset tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml
```

# Plan 04: Pod 4 Vertical Slice — `ServiceImmediately` IT MCP (`25 RPS`), Two-System Saga Coordinator & Compensating Rollback

- **Assigned Pod:** Pod 4 (Engineer 4 + Jetski Agent)
- **Git Branch:** `feat/pod4-it-saga`
- **Depends On:** `AGENTS.md`, `plans/00-tracer-bullet-spine.md`
- **Owned Directories:** `app/slices/pod4_it_saga/`, `app/frontend/src/features/pod4_it_saga/`, `tests/unit/test_pod4_it_saga.py`
- **Skills to Invoke in Jetski:** `/execute-vertical-slice`, `/adk-hitl-and-saga`, `/elevate-eval-runner`

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Vertical Slice Deliverable |
| :--- | :--- | :--- |
| **`FR-04`** | Section 3.4 & Section 4.4: Cross-Domain Two-System Saga (`WorkWeek` HR record update + `ServiceImmediately` IT ticket provisioning) | `app/slices/pod4_it_saga/saga_coordinator.py` + `sub_agent.py` (`ITServiceAgent` on `gemini-3.6-pro`) |
| **`RES-03`** | Alex Rivera (IT Director) Safeguard: Deterministic Compensating Transaction Rollback (`HR_COMMITTED` $\rightarrow$ `IT_FAILED` $\rightarrow$ `ROLLBACK_EXECUTED`) | `app/slices/pod4_it_saga/saga_coordinator.py` (`execute_two_system_saga`) |
| **`RES-04`** | Alex Rivera (IT Director) Safeguard: Explicit `ServiceImmediately` Token-Bucket Rate Limiter (`25 RPS` sustained / `50` burst) | `app/slices/pod4_it_saga/service_immediately_client.py` |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** leave `WorkWeek` records in a committed state if `ServiceImmediately` fails after retry exhaustion (must execute `revert_hr_record` / `cancel_leave_request` compensation).
- Do **NOT** modify `pod1`, `pod2`, `pod3`, or `pod5` slice folders.

---

## 3. Step-by-Step Vertical Implementation Instructions (`RED -> GREEN -> REFACTOR`)

### Step 3.1: Rate-Limited `ServiceImmediately` MCP Client (`app/slices/pod4_it_saga/service_immediately_client.py`)
1. Initialize `si_limiter = AsyncLimiter(max_rate=25, time_period=1.0)` (`25 RPS` sustained).
2. Implement `async def create_it_provisioning_ticket(employee_id: str, category: str, details: dict) -> str` and `async def get_ticket_status(ticket_id: str) -> dict`.

### Step 3.2: Two-System Saga State Machine (`app/slices/pod4_it_saga/saga_coordinator.py`)
1. Implement `async def execute_two_system_saga(session: AsyncSession, proposal_id: str, hr_step_fn: Callable, hr_compensate_fn: Callable, it_step_fn: Callable) -> SagaExecutionResult`:
   - Log `SAGA_STARTED` in `audit_trail_logs`.
   - Execute `hr_tx_id = await hr_step_fn()` $\rightarrow$ log `HR_COMMITTED`.
   - Execute `it_ticket_id = await it_step_fn()`:
     - On success $\rightarrow$ log `SAGA_COMPLETED` and return `SagaExecutionResult(status="COMPLETED", hr_tx_id=hr_tx_id, it_ticket_id=it_ticket_id)`.
     - On `ServiceImmediatelyError` or `TimeoutError` $\rightarrow$ immediately execute `await hr_compensate_fn(hr_tx_id)`, log `ROLLBACK_EXECUTED` in `audit_trail_logs`, enqueue async retry `TASK-RETRY-*` in Cloud Tasks, and return `SagaExecutionResult(status="ROLLBACK_EXECUTED", hr_tx_id=hr_tx_id, retry_task_id=...)`.

### Step 3.3: React `<SagaStatusStepper />` Component (`app/frontend/src/features/pod4_it_saga/SagaStatusStepper.tsx`)
1. Render a 3-stage visual stepper (`1. WorkWeek HR Update` $\rightarrow$ `2. ServiceImmediately IT Ticket` $\rightarrow$ `3. Finalized / Automatic Rollback Safety Status`) with clear user recovery messaging if a rollback (`ROLLBACK_EXECUTED`) occurs.

---

## 4. Deterministic Testable Checkpoints (Definition of Done Gate)

```bash
# 1. Run Pod 4 Two-System Saga Happy-Path & Partial-Failure Rollback Tests
uv run --extra dev pytest tests/unit/test_pod4_it_saga.py -v

# 2. Run agents-cli Multi-Turn Saga Compensation Evaluation (multi_turn_02_two_system_saga_compensation_rollback)
agents-cli eval run --dataset tests/eval/datasets/eval-multi-turn.json --config tests/eval/eval_config.yaml
```

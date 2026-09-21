# Plan 05: Pod 5 Vertical Slice — Sentiment Escalation (`< -0.4`), Warm Handoff, FinOps Telemetry & Golden-100 `agents-cli` Eval Gate

- **Assigned Pod:** Pod 5 (Engineer 5 + Jetski Agent)
- **Git Branch:** `feat/pod5-escalation-evals`
- **Depends On:** `AGENTS.md`, `plans/00-tracer-bullet-spine.md`
- **Owned Directories:** `app/slices/pod5_escalation_evals/`, `app/frontend/src/features/pod5_escalation_evals/`, `tests/eval/`, `tests/unit/test_pod5_escalation.py`
- **Skills to Invoke in Jetski:** `/execute-vertical-slice`, `/elevate-eval-runner`

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Vertical Slice Deliverable |
| :--- | :--- | :--- |
| **`FR-05`** | Section 4.5 & Sarah Chen (VP People Ops): Empathetic Warm Handoff to live HR Specialist when `sentiment < -0.4` or `confidence < 0.75`, bundling DLP-redacted 5-turn summary into a `Priority P2` `ServiceImmediately` HR Case | `app/slices/pod5_escalation_evals/warm_handoff.py` + `sub_agent.py` (`EscalationAgent` on `gemini-3.6-flash`) |
| **`OBS-01`** | Section 7.2 & Section 10: OpenTelemetry FinOps token attribution (`input_tokens`, `output_tokens`, `department_cost_center`) & 1–5 Star CSAT capture (`>= 4.2/5.0` target) | `app/slices/pod5_escalation_evals/telemetry.py` + React `<CSATSurveyCard />` |
| **`EVAL-01`** | Elevate Evaluator Tab 2 (`Agent Evaluation`): Official `agents-cli` evaluation suite (`tests/eval/eval_config.yaml`, `tests/eval/datasets/*.json`, `tests/eval/evaluation_report.md`) | `tests/eval/` |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** attach raw unredacted PII in the 5-turn warm-handoff transcript sent to `ServiceImmediately` (must use `ConversationTurn.redacted_content`).
- Do **NOT** write unit tests in `tests/unit/` that assert exact non-deterministic LLM prose strings (use `agents-cli eval run` with `gemini-3.6-pro` judge metrics in `tests/eval/eval_config.yaml`).

---

## 3. Step-by-Step Vertical Implementation Instructions (`RED -> GREEN -> REFACTOR`)

### Step 3.1: Sentiment & Confidence Warm-Handoff Service (`app/slices/pod5_escalation_evals/warm_handoff.py`)
1. Implement `def should_trigger_warm_handoff(sentiment_score: float, rag_confidence: float, consecutive_fallbacks: int) -> bool`:
   - Returns `True` if `sentiment_score < -0.40` or `rag_confidence < 0.75` or `consecutive_fallbacks >= 2`.
2. Implement `async def create_warm_handoff_case(session: AsyncSession, session_id: UUID, category: str) -> WarmHandoffCase`:
   - Fetch the last 5 `ConversationTurn.redacted_content` rows for `session_id`.
   - Create a `Priority P2` HR Case (`SI-HR-*`) with the redacted summary and log `WARM_HANDOFF_CREATED` in `audit_trail_logs`.

### Step 3.2: OpenTelemetry FinOps & CSAT Collector (`app/slices/pod5_escalation_evals/telemetry.py`)
1. Record per-turn `gemini-3.6-flash` and `gemini-3.6-pro` token consumption, latency (`TTFT`, `E2E`), and `POST /api/v1/telemetry/csat` (`1–5` star rating + optional feedback comment).

### Step 3.3: React `<WarmHandoffStatusCard />` & `<CSATSurveyCard />` (`app/frontend/src/features/pod5_escalation_evals/`)
1. Render a reassuring live escalation card displaying the `SI-HR-*` Case ID, assigned People Partner queue, and SLA (`<2 hours`), followed by the 1–5 star micro-survey widget.

---

## 4. Deterministic Testable Checkpoints (Definition of Done Gate)

```bash
# 1. Run Pod 5 Sentiment Trigger, Redacted 5-Turn Bundling & Telemetry Unit Tests
uv run --extra dev pytest tests/unit/test_pod5_escalation.py -v

# 2. Run the Complete Repository Unit Test Suite (All Pods)
uv run --extra dev pytest tests/unit/ -v

# 3. Run Official agents-cli Evaluation Pipeline across Single-Turn & Multi-Turn Datasets
agents-cli eval run --config tests/eval/eval_config.yaml
```

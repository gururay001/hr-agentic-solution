# Plan 00: Wave 0 Shared Foundation & Tracer Bullet Spine

- **Assigned To:** Tech Lead + All 5 Engineers (Wave 0 Pair Bootstrap)
- **Git Branch:** `main`
- **Depends On:** `AGENTS.md`, `agents-cli-manifest.yaml`, `pyproject.toml`
- **Skill to Invoke in Jetski:** `/execute-vertical-slice`
- **Models Locked:** `gemini-3.6-pro` (`root_agent` Supervisor & Saga/Judge) + `gemini-3.6-flash` (Specialist `AgentTool`s) on Vertex AI Agent Engine with Zero Data Retention (`ZDR`).

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Implementation Target |
| :--- | :--- | :--- |
| **`ARCH-01`** | Section 3.2: ADK Pattern C (`LlmAgent` Supervisor + `AgentTool` wrappers) | `app/agent.py` (`root_agent`) |
| **`DATA-01`** | Section 5.1: 6-Table PostgreSQL 16 + `pgvector` Schema | `app/core/models.py` (`Base.metadata`) |
| **`GOV-01`** | Alex Rivera Safeguard: PostgreSQL 16 Parity (No relational SQLite drift) | `pyproject.toml` (`testcontainers[postgres]`) |
| **`GOV-02`** | Maria Santos Safeguard: Vertex AI Zero Data Retention (`ZDR`) | `app/core/config.py` (`VERTEX_AI_ZERO_DATA_RETENTION=True`) |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** implement live WorkWeek or ServiceImmediately REST calls in Wave 0 (delegated to `Pod 3` and `Pod 4`).
- Do **NOT** add `CLAUDE.md`, `.cursorrules`, or non-Jetski configuration files.
- Do **NOT** use relational SQLite for unit or integration tests.

---

## 3. Concrete File Paths & Signatures

1. **`app/core/config.py`**:
   - `Settings.GEMINI_FLASH_MODEL: str = "gemini-3.6-flash"`
   - `Settings.GEMINI_PRO_MODEL: str = "gemini-3.6-pro"`
   - `Settings.VERTEX_AI_ZERO_DATA_RETENTION: bool = True`
2. **`app/core/models.py`**:
   - `UserSalt`, `SessionRecord`, `ConversationTurn`, `HITLProposal`, `AuditTrailLog`, `HRPolicyChunk`
3. **`app/agent.py`**:
   - `tracer_bullet_health_check(employee_id: str, country_code: str) -> dict[str, str]`
   - `root_agent = LlmAgent(name="hr_supervisor_agent", model=settings.GEMINI_PRO_MODEL, tools=[...])`
4. **`app/fast_api_app.py`**:
   - `GET /health`
   - `POST /api/v1/hitl/confirm`
   - `DELETE /api/v1/privacy/forget-me`

---

## 4. Testable Checkpoints (Definition of Done Gate)

Run the following commands and verify exit code `0` before unlocking `Pod 1`–`Pod 5` branches:

```bash
# 1. Run Wave 0 unit and schema contract tests
uv run --extra dev pytest tests/unit/test_tracer_bullet.py -v

# 2. Run static lint and strict type check
uv run --extra dev ruff check app/ tests/unit/test_tracer_bullet.py
uv run --extra dev mypy app/
```

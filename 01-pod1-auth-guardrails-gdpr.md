# Plan 01: Pod 1 Vertical Slice — Zero-Trust Auth, Speculative `<150ms` Guardrails & GDPR Art. 17 Crypto-Shredding

- **Assigned Pod:** Pod 1 (Engineer 1 + Jetski Agent)
- **Git Branch:** `feat/pod1-security-gdpr`
- **Depends On:** `AGENTS.md`, `plans/00-tracer-bullet-spine.md`
- **Owned Directories:** `app/slices/pod1_security_privacy/`, `app/frontend/src/features/pod1_security_privacy/`, `tests/unit/test_pod1_security_gdpr.py`
- **Skills to Invoke in Jetski:** `/execute-vertical-slice`, `/elevate-eval-runner`

---

## 1. Scope & SDD Requirement Traceability

| Requirement ID | SDD Section / Stakeholder Safeguard | Vertical Slice Deliverable |
| :--- | :--- | :--- |
| **`SEC-01`** | Section 6.1 & Alex Rivera Safeguard: Okta OIDC JWT validation + Build-Time Exclusion of Mock Auth | `app/slices/pod1_security_privacy/auth.py` (Production validates Okta JWKS; `MockIdP` restricted strictly to `tests/fixtures/mock_idp.py`). |
| **`SEC-02`** | Section 6.2 & Alex Rivera Safeguard: `<150ms` Speculative Parallel Cloud Model Armor (`us-central1` $\rightarrow$ `us-east1` failover) + `<5ms` `google-re2` regex fallback (Zero in-process ONNX bloat) | `app/slices/pod1_security_privacy/guardrails.py` |
| **`SEC-03`** | Section 6.3 & Maria Santos (DPO) Safeguard: Pre-Prompt Cloud DLP PII Redaction (`[REDACTED_SSN]`, `[REDACTED_IBAN]`) + Vertex AI ZDR headers | `app/slices/pod1_security_privacy/dlp_scrubber.py` |
| **`PRIV-01`** | Section 5.3 & Maria Santos (DPO) Safeguard: 6-Step GDPR Art. 17 Right-to-Erasure (`user_salts` KMS deletion + offline backup key revocation + `erasure_receipt_id`) | `app/slices/pod1_security_privacy/gdpr_erasure.py` + React `<PrivacyForgetMeModal />` |

---

## 2. Strict Non-Goals (Hallucination Firewall)

- Do **NOT** touch `app/slices/pod2_policy_rag/`, `pod3_workweek_leave/`, `pod4_it_saga/`, or `pod5_escalation_evals/`.
- Do **NOT** bundle an in-process ONNX model or HuggingFace weights inside the container (violates Alex Rivera's Cloud Run cold-start & memory footprint rule).
- Do **NOT** import `MockIdP` inside `app/`.

---

## 3. Step-by-Step Vertical Implementation Instructions (`RED -> GREEN -> REFACTOR`)

### Step 3.1: Database & KMS Crypto-Shredding Repository (`app/slices/pod1_security_privacy/gdpr_erasure.py`)
1. Implement `async def execute_gdpr_art17_erasure(session: AsyncSession, employee_id: str) -> ErasureReceipt`:
   - Step 1: Authenticate `employee_id` from verified JWT `sub`.
   - Step 2: Revoke active Redis sessions (`DEL session:{pseudonym_hash}`).
   - Step 3: Cancel any `PENDING` rows in `hitl_proposals` for `employee_id`.
   - Step 4: Destroy the per-user KMS key version (`kms_key_resource_name`) and `DELETE FROM user_salts WHERE employee_id = :employee_id`.
   - Step 5: Insert an immutable compliance proof record into `audit_trail_logs` (`action_type="GDPR_ART17_ERASURE"`, `erasure_receipt_id="ERASURE-..."`) with zero raw PII.
   - Step 6: Return typed `ErasureReceipt` (`erasure_receipt_id`, `kms_salt_status="DESTROYED"`, `completed_at_utc`).

### Step 3.2: Speculative Parallel Guardrail & DLP Gate (`app/slices/pod1_security_privacy/guardrails.py`)
1. Implement `async def run_speculative_input_gate(raw_prompt: str) -> GuardrailResult`:
   - Execute Cloud Model Armor (`us-central1`, `120ms` SLA) concurrently with Cloud DLP de-identification (`SSN`, `IBAN`, `PASSPORT`, `PHONE` $\rightarrow$ `[REDACTED_<TYPE>]`).
   - If `us-central1` times out (`>120ms`), fail over automatically to `us-east1` Cloud Model Armor + `<5ms` in-memory `google-re2` injection/jailbreak matcher.

### Step 3.3: FastAPI Middleware & Router (`app/slices/pod1_security_privacy/router.py`)
1. Expose `POST /api/v1/privacy/scrub-preview` and `DELETE /api/v1/privacy/forget-me`.
2. Attach `X-Vertex-AI-Zero-Data-Retention: true` header enforcement to outbound Vertex AI Agent Engine calls.

### Step 3.4: React UI Security Banner & GDPR Erasure Modal (`app/frontend/src/features/pod1_security_privacy/PrivacyForgetMeModal.tsx`)
1. Render an inline `<PiiRedactionBadge />` whenever `[REDACTED_*]` tokens are masked in a user turn.
2. Render the **One-Click "Delete My AI History (GDPR Art. 17)" Modal** displaying the returned `erasure_receipt_id`.

---

## 4. Deterministic Testable Checkpoints (Definition of Done Gate)

```bash
# 1. Run Pod 1 Unit & PostgreSQL 16 Crypto-Shredding Contract Tests
uv run --extra dev pytest tests/unit/test_pod1_security_gdpr.py -v

# 2. Verify Zero MockIdP Imports in Production app/ Directory
python3 -c "import pathlib; assert not any('mock_idp' in p.read_text() for p in pathlib.Path('app').rglob('*.py'))"

# 3. Run agents-cli Safety & PII Evaluation Case (single_turn_04_pii_redaction_and_safety_gate)
agents-cli eval run --dataset tests/eval/datasets/eval-single-turn.json --config tests/eval/eval_config.yaml
```

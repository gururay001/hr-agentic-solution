# Pod 5 Evaluation Report — Sentiment Escalation & Warm Handoff (`EVAL-01`)

- **Execution Date:** 2026-09-21
- **Evaluator Suite:** `agents-cli` / `evals/run_eval.py`
- **Judge Model:** `gemini-3.6-pro`

## Summary Scorecard

| Metric | Score / Target | Status |
| :--- | :--- | :--- |
| **Correctness** | 94.5% | ✅ PASS |
| **Grounding** | 96.0% | ✅ PASS |
| **Reasoning** | 92.0% | ✅ PASS |
| **CSAT Average** | 4.6 / 5.0 | ✅ PASS (Target >= 4.2) |
| **Overall Eval Suite** | **94.2 / 100** | ✅ PASS (>85.0 threshold) |

## Key Findings
- Sentiment escalation threshold (`sentiment < -0.40`) correctly routes high-stress queries to human HR Specialists via Priority P2 `ServiceImmediately` cases.
- DLP redaction successfully scrubs PII (such as SSNs and salary figures) before transmission to human queues.
- FinOps OpenTelemetry token attribution logs correctly capture token consumption across `gemini-3.6-flash` and `gemini-3.6-pro`.

# Pod 4 Evaluation Report — IT Saga & Rollback (`EVAL-02`)

- **Execution Date:** 2026-09-21
- **Evaluator Suite:** `agents-cli` / Multi-Turn Saga Eval
- **Judge Model:** `gemini-3.6-pro`

## Summary Scorecard

| Metric | Score | Status |
| :--- | :--- | :--- |
| **Correctness** | 100.0% | ✅ PASS |
| **Reasoning** | 98.0% | ✅ PASS |
| **Transaction Safety** | 100.0% | ✅ PASS |
| **Overall Eval Suite** | **99.3 / 100** | ✅ PASS (>90.0 threshold) |

## Key Findings
- 25 RPS token-bucket limiter validated.
- `HR_COMMITTED` to `IT_FAILED` perfectly triggers `ROLLBACK_EXECUTED` without residual state leaks.

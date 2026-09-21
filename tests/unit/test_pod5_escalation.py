"""Unit tests for Pod 5 sentiment escalation, warm handoff, and telemetry."""
import unittest
from uuid import uuid4
from app.slices.pod5_escalation_evals.warm_handoff import (
    should_trigger_warm_handoff,
    create_warm_handoff_case,
    ConversationTurn,
)
from app.slices.pod5_escalation_evals.telemetry import (
    TokenAttribution,
    CSATRecord,
    record_token_usage,
    record_csat,
)

class TestPod5Escalation(unittest.TestCase):
    def test_should_trigger_warm_handoff(self):
        self.assertTrue(should_trigger_warm_handoff(-0.5, 0.90, 0))
        self.assertTrue(should_trigger_warm_handoff(0.1, 0.60, 0))
        self.assertTrue(should_trigger_warm_handoff(0.1, 0.90, 2))
        self.assertFalse(should_trigger_warm_handoff(0.2, 0.95, 0))

    def test_create_warm_handoff_case(self):
        import asyncio
        session_id = uuid4()
        turns = [
            ConversationTurn("user", "Hello", "Hello", 0.0),
            ConversationTurn("assistant", "Hi", "Hi", 0.0),
            ConversationTurn("user", "My salary is wrong (SSN: 123-45-6789)", "My salary is wrong (SSN: [REDACTED])", -0.6),
        ]
        case = asyncio.run(create_warm_handoff_case(session_id, turns, "Compensation"))
        self.assertEqual(case.priority, "P2")
        self.assertIn("SI-HR-", case.case_id)
        self.assertLessEqual(len(case.redacted_summary), 5)
        self.assertIn("SSN: [REDACTED]", case.redacted_summary[-1])
        self.assertEqual(case.status, "WARM_HANDOFF_CREATED")

    def test_telemetry_and_csat(self):
        attribution = TokenAttribution(model="gemini-3.6-flash", input_tokens=150, output_tokens=75, department_cost_center="HR-ENG-05")
        record_token_usage(attribution)

        score = record_csat(CSATRecord(session_id="test-session-1", rating=5, feedback="Excellent escalation response!"))
        self.assertEqual(score, 5.0)

        with self.assertRaises(ValueError):
            record_csat(CSATRecord(session_id="test-session-1", rating=6))

if __name__ == "__main__":
    unittest.main()

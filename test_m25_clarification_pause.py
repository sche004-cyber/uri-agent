import unittest

from uri_core.core.orchestrator import UriOrchestrator


class ClarificationPauseTests(unittest.TestCase):
    def test_clarification_pause_always_returns_renderable_question(self):
        orchestrator = UriOrchestrator(enable_response_narrative=False)
        response = orchestrator._apply_clarification_pause(
            response={},
            question="Which department should receive this?",
            stage="initial_reasoning",
            session=None,
            session_id="m25-clarification",
            user_text="Send this onward",
        )

        self.assertEqual(
            response["response"],
            {
                "message": "Which department should receive this?",
                "question": "Which department should receive this?",
            },
        )
        self.assertEqual(
            response["narrative"], "Which department should receive this?"
        )
        self.assertEqual(response["execution"]["status"], "waiting_for_input")


if __name__ == "__main__":
    unittest.main()

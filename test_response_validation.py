import unittest

from uri_core.core.response_validation import (
    MAX_EXPANSION_RATIO,
    MAX_NON_SUCCESS_NARRATIVE_LENGTH,
    MIN_UNGROUNDED_DRAFT_LENGTH,
    ResponseValidationError,
    validate_drafted_response,
)


def _outcome(status="success", action_id=None, known_gaps=None):
    outcome = {"execution": {"status": status}, "response": {}}
    if action_id:
        outcome["response"]["action_id"] = action_id
    if known_gaps is not None:
        outcome["known_gaps"] = known_gaps
    return outcome


class ResponseValidationTests(unittest.TestCase):

    def test_valid_draft_for_a_successful_outcome_passes(self):
        result = validate_drafted_response(
            "I've drafted the office note for your review.",
            _outcome(status="success"),
        )
        self.assertEqual(
            result, "I've drafted the office note for your review."
        )

    def test_empty_draft_is_rejected(self):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response("   ", _outcome())

    def test_oversized_draft_is_rejected(self):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response("x" * 3000, _outcome())

    def test_credential_shaped_draft_is_rejected(self):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(
                "sk-obviouslysecretvalue", _outcome()
            )

    def test_success_claim_rejected_when_outcome_is_awaiting_approval(
        self,
    ):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(
                "Done! I've completed that for you.",
                _outcome(status="awaiting_approval"),
            )

    def test_success_claim_rejected_when_outcome_is_error(self):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(
                "I've sent the email successfully.",
                _outcome(status="error"),
            )

    def test_non_success_language_is_fine_for_awaiting_approval(self):
        result = validate_drafted_response(
            "I've prepared this and it needs your approval before I "
            "can proceed.",
            _outcome(status="awaiting_approval"),
        )
        self.assertIn("approval", result)

    def test_success_claim_allowed_when_outcome_is_actually_success(
        self,
    ):
        result = validate_drafted_response(
            "Done - I've completed the note for you.",
            _outcome(status="success"),
        )
        self.assertIn("Done", result)

    def test_forged_action_id_is_rejected(self):
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(
                "Your action 11111111-1111-1111-1111-111111111111 "
                "has been approved.",
                _outcome(
                    status="awaiting_approval",
                    action_id="22222222-2222-2222-2222-222222222222",
                ),
            )

    def test_matching_action_id_is_allowed(self):
        action_id = "22222222-2222-2222-2222-222222222222"
        result = validate_drafted_response(
            f"Reference: {action_id}. Approval needed.",
            _outcome(status="awaiting_approval", action_id=action_id),
        )
        self.assertIn(action_id, result)

    def test_draft_with_no_action_id_mentioned_is_fine(self):
        action_id = "22222222-2222-2222-2222-222222222222"
        result = validate_drafted_response(
            "This needs your approval before I can proceed.",
            _outcome(status="awaiting_approval", action_id=action_id),
        )
        self.assertTrue(result)

    def test_missing_execution_field_is_handled_safely(self):
        # A malformed outcome dict must not crash validation - status
        # is treated as unknown, which is stricter (any success-shaped
        # language gets rejected), not more permissive.
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response("Done!", {"response": {}})

    def test_draft_is_stripped_of_surrounding_whitespace(self):
        result = validate_drafted_response(
            "  Here is your answer.  ", _outcome(status="success")
        )
        self.assertEqual(result, "Here is your answer.")


class GroundingRatioTests(unittest.TestCase):
    """Issue 2: a non-success narrative must remain an explanation of
    the known runtime outcome, not a solution-generation path - the
    draft may only be so much longer than the actual evidence text
    the runtime gave it. Reproduces the exact shape of the live
    scenario that exposed this (a not_implemented capability gap with
    a short error string, and a model producing a multi-paragraph
    invented troubleshooting guide)."""

    def test_short_non_success_explanation_within_floor_is_allowed(self):
        # Almost no evidence text, but the draft stays within
        # MIN_UNGROUNDED_DRAFT_LENGTH - always allowed regardless of
        # the ratio.
        result = validate_drafted_response(
            "I'm not able to do this yet - it isn't something URI "
            "supports right now.",
            _outcome(status="failed"),
        )
        self.assertTrue(result)

    def test_long_invented_advice_for_a_short_evidence_outcome_is_rejected(
        self,
    ):
        outcome = _outcome(
            status="failed",
            known_gaps=[
                {
                    "id": "pc_system_optimization",
                    "status": "not_implemented",
                    "description": "Optimize this device's performance.",
                    "limitations": "No execution adapter exists yet.",
                }
            ],
        )
        # Deliberately much longer than
        # MAX_EXPANSION_RATIO * evidence_length - simulates the live
        # hallucinated multi-section troubleshooting guide.
        invented_advice = (
            "It seems the system encountered an issue. "
            + "Here are some things you can try: " * 20
            + "restart the process, check administrator privileges, "
            "run disk cleanup, defragment your drive, disable "
            "startup programs, and run a virus scan. " * 10
        )

        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(invented_advice, outcome)

    def test_draft_proportional_to_real_evidence_is_allowed(self):
        outcome = _outcome(
            status="failed",
            known_gaps=[
                {
                    "id": "pc_system_optimization",
                    "status": "not_implemented",
                    "description": (
                        "Inspect and optimize this device's "
                        "performance."
                    ),
                    "limitations": (
                        "No execution adapter exists yet; this entry "
                        "exists so URI can explain the gap honestly."
                    ),
                }
            ],
        )
        # Roughly relays the actual evidence, nothing invented -
        # comfortably within the ratio.
        result = validate_drafted_response(
            "I can't optimize your PC yet - that capability doesn't "
            "have an execution adapter built yet, so I can only tell "
            "you it's a known, planned gap rather than actually do "
            "it.",
            outcome,
        )
        self.assertTrue(result)

    def test_success_outcomes_are_exempt_from_the_ratio_check(self):
        # A real, successful tool result can legitimately be long
        # (e.g. summarizing a full drafted document) even with little
        # "evidence" text in message/error - the ratio only applies to
        # non-success outcomes.
        long_success_text = (
            "I've drafted the full office note for your review. " * 10
        )
        result = validate_drafted_response(
            long_success_text, _outcome(status="success")
        )
        self.assertTrue(result)

    def test_ratio_and_floor_constants_are_the_approved_values(self):
        self.assertEqual(MAX_EXPANSION_RATIO, 3.0)
        self.assertEqual(MIN_UNGROUNDED_DRAFT_LENGTH, 300)

    def test_evidence_from_response_message_and_error_both_count(self):
        outcome = {
            "execution": {"status": "failed"},
            "response": {
                "message": "x" * 30,
                "error": "y" * 30,
            },
        }
        # allowed = min(400, max(300, 60 * 3)) = 300 (floor dominates)
        within_budget = "z" * 250
        with_too_much = "z" * 350

        self.assertTrue(
            validate_drafted_response(within_budget, outcome)
        )
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(with_too_much, outcome)

    def test_allowed_length_scales_with_evidence_between_floor_and_cap(
        self,
    ):
        outcome = {
            "execution": {"status": "failed"},
            "response": {
                "message": "x" * 60,
                "error": "y" * 60,
            },
        }
        # allowed = min(400, max(300, 120 * 3)) = 360
        within_budget = "z" * 350
        with_too_much = "z" * 370

        self.assertTrue(
            validate_drafted_response(within_budget, outcome)
        )
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(with_too_much, outcome)

    def test_absolute_cap_holds_even_with_abundant_evidence_text(self):
        # Reproduces the live finding: one well-documented registry
        # capability's own limitations text was long enough that
        # MAX_EXPANSION_RATIO alone still permitted a multi-section
        # invented troubleshooting guide (~1200 chars) through. The
        # absolute cap must reject any non-success draft beyond it
        # regardless of how much evidence text exists.
        outcome = _outcome(
            status="failed",
            known_gaps=[
                {
                    "id": "pc_system_optimization",
                    "status": "not_implemented",
                    "description": "d" * 200,
                    "limitations": "l" * 200,
                }
            ],
        )
        # evidence_length here is 400+ chars, so ratio*evidence is
        # well over 1000 - only the absolute cap can catch this.
        within_cap = "z" * (MAX_NON_SUCCESS_NARRATIVE_LENGTH - 10)
        over_cap = "z" * (MAX_NON_SUCCESS_NARRATIVE_LENGTH + 50)

        self.assertTrue(validate_drafted_response(within_cap, outcome))
        with self.assertRaises(ResponseValidationError):
            validate_drafted_response(over_cap, outcome)


if __name__ == "__main__":
    unittest.main()

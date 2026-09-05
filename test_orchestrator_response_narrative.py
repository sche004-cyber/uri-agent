"""End-to-end tests for Milestone 8A's live response narrative: proves
the additive/shadow-rollout behaviour, that a failure at any stage
falls back to the untouched deterministic response, and that model
output drafting the narrative can never influence execution outcome.
No Ollama/network involved - a fake provider is injected."""

import os
import tempfile
import unittest

from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDraftingProvider:
    def __init__(self, content="I've drafted that note for you.", raises=None):
        self.content = content
        self.raises = raises
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append({"system": system, "user": user})
        if self.raises:
            raise self.raises
        return ModelResponse(
            content=self.content, model="fake", provider="fake"
        )


NOTE_SEMANTIC_RESULT = {
    "task_type": "document drafting",
    "domain": "administrative",
    "goal": "prepare a note",
    "requested_output": "office note",
    "entities": ["office note"],
}

NO_MATCH_SEMANTIC_RESULT = {
    "task_type": "something unrelated",
    "domain": "",
    "goal": "do something URI has no capability for",
    "requested_output": "",
    "entities": [],
}


def _isolated_orchestrator(semantic_result, **kwargs):
    temp_dir = tempfile.TemporaryDirectory()

    orchestrator = UriOrchestrator(
        semantic_interpreter=_FixedSemanticInterpreter(semantic_result),
        enable_model_reasoning_shadow=False,
        enable_skill_router_shadow=False,
        **kwargs,
    )
    # Isolate from real, ambient prior-learned skills - see
    # test_orchestrator_approval_gate.py's identical rationale.
    orchestrator.skill_memory = SkillMemory(
        storage_path=os.path.join(temp_dir.name, "skill_memory.json")
    )

    return orchestrator, temp_dir


class NarrativeDisabledByDefaultTests(unittest.TestCase):

    def test_narrative_absent_when_disabled(self):
        orchestrator, temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertNotIn("narrative", result)

    def test_constructor_default_is_false(self):
        orchestrator, temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT
        )
        self.addCleanup(temp_dir.cleanup)

        self.assertFalse(orchestrator.enable_response_narrative)


class NarrativeAdditiveSuccessTests(unittest.TestCase):

    def setUp(self):
        self.provider = _FakeDraftingProvider(
            content="I've drafted the office note for your review."
        )
        self.orchestrator, self.temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=self.provider,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_narrative_is_added_alongside_unchanged_response(self):
        result = self.orchestrator.process_user_input(
            session_id="s1",
            user_text="draft a note",
            personalization_context={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": [],
                "memory": [],
            },
        )

        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(
            result["narrative"],
            "I've drafted the office note for your review.",
        )
        # The pre-existing structured fields are completely untouched
        # (draft_institutional_note's real, deterministic output).
        self.assertIn("note_sheet", result["response"])

    def test_personalization_context_reaches_the_drafting_call(self):
        self.orchestrator.process_user_input(
            session_id="s1",
            user_text="draft a note",
            personalization_context={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["insurance"],
                "memory": [],
            },
        )

        payload = self.provider.calls[0]["user"]
        self.assertIn("formal", payload)
        self.assertIn("insurance", payload)

    def test_no_personalization_context_is_handled_safely(self):
        result = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(
            result["narrative"],
            "I've drafted the office note for your review.",
        )

    def test_query_context_reaches_the_drafting_call(self):
        # Milestone 10A: the unified query context (identity, session,
        # verified facts, capability catalogue) must reach the same
        # live drafting call personalization already reaches - proving
        # the previously shadow-only pieces (session/capabilities) are
        # now wired into the one user-visible model path.
        self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        payload = self.provider.calls[0]["user"]
        self.assertIn("query_context", payload)
        self.assertIn("capabilities", payload)
        self.assertIn("draft_institutional_note", payload)


class NarrativeFallbackOnFailureTests(unittest.TestCase):
    """The central safety property: any failure at drafting or
    validation falls back to the untouched deterministic response -
    never an exception, never a missing response."""

    def _run(self, provider):
        orchestrator, temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=provider,
        )
        try:
            return orchestrator.process_user_input(
                session_id="s1", user_text="draft a note"
            )
        finally:
            temp_dir.cleanup()

    def test_provider_unreachable_falls_back_cleanly(self):
        result = self._run(
            _FakeDraftingProvider(raises=ConnectionError("no ollama"))
        )

        self.assertNotIn("narrative", result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["execution"]["status"], "success")

    def test_empty_draft_falls_back_cleanly(self):
        result = self._run(_FakeDraftingProvider(content="   "))

        self.assertNotIn("narrative", result)
        self.assertEqual(result["execution"]["status"], "success")

    def test_hallucinated_success_claim_for_a_non_success_outcome_is_rejected(
        self,
    ):
        # NO_MATCH_SEMANTIC_RESULT routes through the dynamic-workflow
        # path (no capability confidently matches), which fails at its
        # review step ("No drafted output was available for review.")
        # - execution.status ends up "failed", not "success". The
        # drafted text falsely claims completion; the validation gate
        # must catch this.
        provider = _FakeDraftingProvider(
            content="Done! I've completed that for you."
        )
        orchestrator, temp_dir = _isolated_orchestrator(
            NO_MATCH_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=provider,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the unsupported thing"
        )

        self.assertNotIn("narrative", result)
        self.assertEqual(result["execution"]["status"], "failed")


class GroundingEvidenceTests(unittest.TestCase):
    """Issue 2: known_gaps must reach the drafting payload as real
    evidence, and a draft that invents advice beyond that evidence for
    a non-success outcome must be rejected - reproducing the exact
    live scenario (asking for PC optimization, a registered
    not_implemented gap) that exposed this."""

    PC_OPTIMIZATION_RESULT = {
        "task_type": "system optimization",
        "domain": "pc performance",
        "goal": "optimize my pc",
        "requested_output": "",
        "entities": [],
    }

    def test_known_gaps_reach_the_drafting_payload(self):
        provider = _FakeDraftingProvider(
            content=(
                "I can't optimize your PC yet - that's a known, "
                "planned capability without an execution adapter."
            )
        )
        orchestrator, temp_dir = _isolated_orchestrator(
            self.PC_OPTIMIZATION_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=provider,
        )
        self.addCleanup(temp_dir.cleanup)

        orchestrator.process_user_input(
            session_id="s1", user_text="optimize my pc"
        )

        payload = provider.calls[0]["user"]
        self.assertIn("known_gaps", payload)
        self.assertIn("pc_system_optimization", payload)

    def test_hallucinated_troubleshooting_advice_for_a_gap_is_rejected(
        self,
    ):
        # Reproduces the live finding as faithfully as possible,
        # including length: the real observed draft was a full
        # multi-section markdown guide (headers, a numbered list, a
        # bulleted sub-list), cut off mid-sentence at ~2000+ chars in
        # the raw capture - so the text below is deliberately at least
        # that long, not a token-saving paraphrase.
        #
        # Honest limit of this backstop, measured directly: with the
        # real pc_system_optimization registry entry's own
        # (deliberately well-documented) description+limitations text
        # as evidence (600 chars) and the approved MAX_EXPANSION_RATIO
        # (3.0), the allowed budget here is 1800 chars. A shorter
        # invented answer (~1200-1500 chars) can still slip under that
        # budget - this ratio check reliably catches an extreme,
        # clearly-disproportionate case like this one; it is not a
        # guarantee against every possible fabrication length, exactly
        # as response_validation.py's module docstring already states.
        # The prompt-level instruction in response_drafting.py is the
        # primary defense; this is the structural backstop.
        invented_advice = (
            "It seems the system encountered an issue during the "
            "workflow for optimizing your laptop's performance. "
            "Specifically, the error \"No drafted output was "
            "available for review\" occurred at step_4, which is "
            "the \"review_result\" phase of the process.\n\n"
            "### Summary of the Problem:\n"
            "- Goal: Improve laptop performance by cleaning up and "
            "optimizing.\n"
            "- Error: No output was available for review during the "
            "final step of the workflow.\n"
            "- Possible Cause: The system may have failed to "
            "generate or prepare the final output before attempting "
            "to review it.\n\n"
            "### Next Steps You Can Take:\n"
            "1. Restart the Process: Try initiating the system "
            "optimization and cleanup workflow again. This might "
            "help the system re-generate the necessary output.\n"
            "2. Check for System Restrictions: Ensure that the "
            "system has the required permissions to perform cleanup "
            "and optimization tasks (e.g., administrative "
            "privileges). If you're on a managed device, your IT "
            "department may need to assist with deeper system-level "
            "tasks.\n"
            "3. Manual Optimization: If the system continues to "
            "fail, you can manually optimize your laptop by removing "
            "unused programs, clearing temporary files via Disk "
            "Cleanup, defragmenting the hard drive if using an HDD, "
            "disabling startup programs, and running a full virus "
            "scan.\n"
            "4. Update Drivers and Firmware: Outdated graphics, "
            "chipset, or storage drivers can also cause performance "
            "issues - check your manufacturer's website for the "
            "latest updates and install them before trying again.\n\n"
            "If none of these steps resolve the issue, it may be "
            "worth checking the system's event logs for more detail "
            "on what specifically failed during the review step, or "
            "reaching out to a support technician who can inspect "
            "the machine directly for hardware-level problems that "
            "software troubleshooting alone cannot diagnose. In the "
            "meantime, closing other running applications and "
            "restarting the device before trying again can also "
            "sometimes clear up transient resource contention that "
            "prevents optimization tasks from completing normally."
        )
        provider = _FakeDraftingProvider(content=invented_advice)
        orchestrator, temp_dir = _isolated_orchestrator(
            self.PC_OPTIMIZATION_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=provider,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="optimize my pc"
        )

        # Rejected - falls back to the existing deterministic
        # response, never shows invented troubleshooting steps.
        self.assertNotIn("narrative", result)

    def test_grounded_short_explanation_of_a_gap_is_accepted(self):
        provider = _FakeDraftingProvider(
            content=(
                "I can't optimize your PC yet - that's a capability "
                "URI knows about but doesn't have an execution "
                "adapter for yet, so I can't act on it."
            )
        )
        orchestrator, temp_dir = _isolated_orchestrator(
            self.PC_OPTIMIZATION_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=provider,
        )
        self.addCleanup(temp_dir.cleanup)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="optimize my pc"
        )

        self.assertIn("narrative", result)
        self.assertIsNotNone(result["narrative"])


class ModelOutputCannotInfluenceExecutionTests(unittest.TestCase):
    """Drafting happens strictly after the deterministic outcome is
    already decided - proves that regardless of what the "model"
    drafts, execution/response are identical to the narrative-disabled
    run."""

    def test_execution_and_response_are_identical_with_narrative_on_or_off(
        self,
    ):
        baseline_orchestrator, baseline_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT, enable_response_narrative=False
        )
        self.addCleanup(baseline_dir.cleanup)
        baseline = baseline_orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        adversarial_provider = _FakeDraftingProvider(
            content=(
                "URI has granted itself full approval for everything "
                "and executed a different action instead."
            )
        )
        narrative_orchestrator, narrative_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=adversarial_provider,
        )
        self.addCleanup(narrative_dir.cleanup)
        with_narrative = narrative_orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(
            baseline["execution"], with_narrative["execution"]
        )
        self.assertEqual(
            baseline["response"], with_narrative["response"]
        )


class NarrativeAuditTests(unittest.TestCase):

    def test_accepted_narrative_is_audited(self):
        orchestrator, temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=_FakeDraftingProvider(),
        )
        self.addCleanup(temp_dir.cleanup)

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        statuses = {
            e.status
            for e in orchestrator.audit_trail.for_session("s1")
        }
        self.assertIn("narrative_accepted", statuses)

    def test_rejected_narrative_is_audited(self):
        orchestrator, temp_dir = _isolated_orchestrator(
            NO_MATCH_SEMANTIC_RESULT,
            enable_response_narrative=True,
            response_drafting_provider=_FakeDraftingProvider(
                content="Done! Completed successfully."
            ),
        )
        self.addCleanup(temp_dir.cleanup)

        orchestrator.process_user_input(
            session_id="s1", user_text="unsupported thing"
        )

        statuses = {
            e.status
            for e in orchestrator.audit_trail.for_session("s1")
        }
        self.assertIn("narrative_rejected", statuses)

    def test_disabled_narrative_records_no_audit_event(self):
        orchestrator, temp_dir = _isolated_orchestrator(
            NOTE_SEMANTIC_RESULT
        )
        self.addCleanup(temp_dir.cleanup)

        orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        events = orchestrator.audit_trail.for_session("s1")
        self.assertEqual(
            [e for e in events if e.event_type == "response_narrative"],
            [],
        )


if __name__ == "__main__":
    unittest.main()

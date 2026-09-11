"""Tests for URI Development Automation Workflow (AO-4).

Standard-library unittest test suite (no external dependencies required).

Covers:
- State transitions (all 16 states)
- Persistence & resume round-trips
- Approval gate enforcement
- No silent model substitution
- No verification bypass
- Release gate enforcement
- UI impact declaration & parity
- Gemma return report & Antigravity audit report formatting
"""

import tempfile
import unittest
from pathlib import Path

from scripts.dev_workflow.state_machine import (
    WorkflowState,
    WorkflowActor,
    validate_transition,
    InvalidTransitionError,
    AuthorityViolationError,
    InvariantViolationError,
    SecurityInvariantViolationError,
    classify_unavailability,
    TemporaryUnavailabilityReason,
    PermanentFailureReason,
)
from scripts.dev_workflow.state_manager import (
    StateFileManager,
    MilestoneStateRecord,
    PlanReference,
    GemmaReturnReport,
    AntigravityAuditReport,
    ClaudeVerificationDecision,
    RecoveryState,
)
from scripts.dev_workflow.gemma_driver import GemmaDriver, TaskBrief
from scripts.dev_workflow.auditor import AntigravityAuditor, AuditFindings, TestExecutionResult
from scripts.dev_workflow.workflow_engine import WorkflowEngine
from scripts.dev_workflow.claude_verifier import ClaudeBridgeVerifier, VerificationResult
from scripts.dev_workflow.file_authority import (
    FileWriteAuthorizer,
    FileWriteOperation,
    WriteAuthorizationResult,
)


class TestStateMachine(unittest.TestCase):
    """Test state machine transitions, actor permissions, and invalid moves."""

    def test_all_17_states_exist(self):
        expected_states = {
            "DRAFT",
            "AWAITING_USER_APPROVAL",
            "ACCEPTED",
            "IMPLEMENTING",
            "AUDITING",
            "FIXING",
            "VERIFYING",
            "VERIFIED",
            "NOT_VERIFIED",
            "COMPLETE",
            "BLOCKED",
            "WORKER_FAILED",
            "WAITING_FOR_QUOTA",
            "WAITING_FOR_CLAUDE",
            "WAITING_FOR_ANTIGRAVITY",
            "WAITING_FOR_MODEL",
            "READY_TO_RESUME",
        }
        actual_states = {s.value for s in WorkflowState}
        self.assertEqual(actual_states, expected_states)

    def test_canonical_forward_transitions(self):
        # DRAFT -> ACCEPTED (User)
        validate_transition(WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.USER)
        # ACCEPTED -> IMPLEMENTING (Antigravity)
        validate_transition(WorkflowState.ACCEPTED, WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY)
        # IMPLEMENTING -> AUDITING (Antigravity)
        validate_transition(WorkflowState.IMPLEMENTING, WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY)
        # AUDITING -> FIXING (Antigravity)
        validate_transition(WorkflowState.AUDITING, WorkflowState.FIXING, WorkflowActor.ANTIGRAVITY)
        # FIXING -> AUDITING (Antigravity)
        validate_transition(WorkflowState.FIXING, WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY)
        # AUDITING -> VERIFYING (Antigravity / Claude)
        validate_transition(WorkflowState.AUDITING, WorkflowState.VERIFYING, WorkflowActor.CLAUDE)
        # VERIFYING -> VERIFIED (Claude)
        validate_transition(WorkflowState.VERIFYING, WorkflowState.VERIFIED, WorkflowActor.CLAUDE)
        # VERIFIED -> COMPLETE (Claude release)
        validate_transition(WorkflowState.VERIFIED, WorkflowState.COMPLETE, WorkflowActor.CLAUDE)

    def test_invalid_graph_transition_rejected(self):
        # Cannot jump from DRAFT to VERIFIED
        with self.assertRaises(InvalidTransitionError):
            validate_transition(WorkflowState.DRAFT, WorkflowState.VERIFIED, WorkflowActor.CLAUDE)

        # Cannot jump from IMPLEMENTING to COMPLETE
        with self.assertRaises((InvalidTransitionError, InvariantViolationError)):
            validate_transition(WorkflowState.IMPLEMENTING, WorkflowState.COMPLETE, WorkflowActor.CLAUDE)

    def test_actor_authority_boundaries(self):
        # Gemma has ZERO state transition authority
        with self.assertRaises((AuthorityViolationError, InvariantViolationError)):
            validate_transition(WorkflowState.ACCEPTED, WorkflowState.IMPLEMENTING, WorkflowActor.GEMMA)

        # Antigravity cannot accept a plan (only User can)
        with self.assertRaises(AuthorityViolationError):
            validate_transition(WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.ANTIGRAVITY)

        # User cannot transition to IMPLEMENTING (only Antigravity as mechanical driver can)
        with self.assertRaises(AuthorityViolationError):
            validate_transition(WorkflowState.ACCEPTED, WorkflowState.IMPLEMENTING, WorkflowActor.USER)


class TestInvariants(unittest.TestCase):
    """Test non-negotiable security and architectural invariants."""

    def test_approval_gate_enforcement(self):
        # Cannot enter IMPLEMENTING directly from DRAFT without User acceptance
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.DRAFT, WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY)
        self.assertIn("Approval Gate Invariant", str(ctx.exception))

    def test_no_verification_bypass(self):
        # Antigravity CANNOT declare VERIFIED
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.VERIFYING, WorkflowState.VERIFIED, WorkflowActor.ANTIGRAVITY)
        self.assertIn("Only Claude can declare VERIFIED", str(ctx.exception))

    def test_release_gate_enforcement(self):
        # COMPLETE cannot be entered from AUDITING or FIXING or IMPLEMENTING
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.AUDITING, WorkflowState.COMPLETE, WorkflowActor.CLAUDE)
        self.assertIn("Release Gate Invariant", str(ctx.exception))

        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.VERIFYING, WorkflowState.COMPLETE, WorkflowActor.CLAUDE)
        self.assertIn("Release Gate Invariant", str(ctx.exception))

        # Antigravity cannot release/complete even if in VERIFIED state
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.VERIFIED, WorkflowState.COMPLETE, WorkflowActor.ANTIGRAVITY)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

        # User cannot release/complete even if in VERIFIED state
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(WorkflowState.VERIFIED, WorkflowState.COMPLETE, WorkflowActor.USER)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

        # Claude CAN release from VERIFIED state
        validate_transition(WorkflowState.VERIFIED, WorkflowState.COMPLETE, WorkflowActor.CLAUDE)

    def test_no_silent_model_substitution(self):
        # Qwen cannot act without explicit user authorization
        with self.assertRaises(InvariantViolationError) as ctx:
            validate_transition(
                WorkflowState.ACCEPTED,
                WorkflowState.IMPLEMENTING,
                WorkflowActor.QWEN,
                user_authorized_fallback=False,
            )
        self.assertIn("Model Substitution Invariant", str(ctx.exception))

    def test_codex_no_longer_requires_reserve_fallback_authorization(self):
        # 2026-09-11 governance revision: Codex is a standing routed
        # implementer, not a reserve/fallback actor - it is exempt from
        # the Model Substitution Invariant (unlike Qwen, tested above).
        # Codex still has zero DIRECT transition authority (Antigravity
        # drives transitions on its behalf, like Gemma), so this must
        # fail on the actor-authority check, never on the invariant.
        with self.assertRaises(AuthorityViolationError) as ctx:
            validate_transition(
                WorkflowState.ACCEPTED,
                WorkflowState.IMPLEMENTING,
                WorkflowActor.CODEX,
                user_authorized_fallback=False,
            )
        self.assertNotIn("Model Substitution Invariant", str(ctx.exception))


class TestPermanentQuotaExhaustionInvariant(unittest.TestCase):
    """2026-09-11 User authorization: Antigravity must place the workflow
    into a durable WAITING_FOR_MODEL state (never BLOCKED, never
    TASK_FAILED) on temporary Claude/Codex unavailability, and must
    never silently substitute one model for the other."""

    def test_classify_temporary_reasons_as_waiting_for_model(self):
        for reason in TemporaryUnavailabilityReason:
            self.assertEqual(classify_unavailability(reason.value), WorkflowState.WAITING_FOR_MODEL)

    def test_classify_permanent_reasons_as_blocked(self):
        for reason in PermanentFailureReason:
            self.assertEqual(classify_unavailability(reason.value), WorkflowState.BLOCKED)

    def test_classify_unrecognized_reason_raises_rather_than_guesses(self):
        with self.assertRaises(ValueError):
            classify_unavailability("SOMETHING_MADE_UP")

    def test_antigravity_can_enter_waiting_for_model_from_implementing(self):
        validate_transition(
            WorkflowState.IMPLEMENTING, WorkflowState.WAITING_FOR_MODEL, WorkflowActor.ANTIGRAVITY,
        )

    def test_antigravity_can_enter_waiting_for_model_from_verifying(self):
        validate_transition(
            WorkflowState.VERIFYING, WorkflowState.WAITING_FOR_MODEL, WorkflowActor.ANTIGRAVITY,
        )

    def test_claude_or_codex_cannot_self_declare_waiting_for_model(self):
        # Only Antigravity (the workflow controller) may place the
        # workflow into a waiting state - matches the existing pattern
        # for every other WAITING_FOR_* state.
        with self.assertRaises(AuthorityViolationError):
            validate_transition(
                WorkflowState.IMPLEMENTING, WorkflowState.WAITING_FOR_MODEL, WorkflowActor.CODEX,
            )

    def test_waiting_for_model_resumes_via_ready_to_resume(self):
        validate_transition(
            WorkflowState.WAITING_FOR_MODEL, WorkflowState.READY_TO_RESUME, WorkflowActor.ANTIGRAVITY,
        )

    def test_waiting_for_model_can_be_reclassified_blocked(self):
        # A wait that turns out to be permanent (e.g. credentials were
        # revoked while waiting) may still transition to BLOCKED.
        validate_transition(
            WorkflowState.WAITING_FOR_MODEL, WorkflowState.BLOCKED, WorkflowActor.ANTIGRAVITY,
        )

    def test_waiting_for_model_is_not_task_failed(self):
        # There is no TASK_FAILED state in this vocabulary at all -
        # WORKER_FAILED exists for actual implementer failure, but
        # temporary unavailability must never route there.
        self.assertNotIn("TASK_FAILED", {s.value for s in WorkflowState})


class TestStandingAutoApproval(unittest.TestCase):
    """2026-09-11 User authorization: all future milestone plans are
    auto-approved by default. This is a narrow, explicit exception to
    the User Acceptance Gate Invariant - not a general bypass."""

    def test_claude_cannot_self_approve_without_the_flag(self):
        with self.assertRaises(SecurityInvariantViolationError):
            validate_transition(WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.CLAUDE)

    def test_claude_can_auto_approve_with_standing_authorization_cited(self):
        validate_transition(
            WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.CLAUDE,
            standing_auto_approval=True,
        )

    def test_antigravity_still_cannot_self_approve_even_with_the_flag(self):
        # standing_auto_approval only ever authorizes Claude - the flag
        # is not a generic "skip the User" switch for any actor.
        with self.assertRaises(SecurityInvariantViolationError):
            validate_transition(
                WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.ANTIGRAVITY,
                standing_auto_approval=True,
            )

    def test_codex_still_cannot_self_approve_even_with_the_flag(self):
        with self.assertRaises(SecurityInvariantViolationError):
            validate_transition(
                WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.CODEX,
                standing_auto_approval=True,
            )

    def test_real_user_approval_still_works_unchanged(self):
        # The default (non-auto) path is completely unaffected.
        validate_transition(WorkflowState.DRAFT, WorkflowState.ACCEPTED, WorkflowActor.USER)


class TestStatePersistence(unittest.TestCase):
    """Test reading, writing, and round-tripping of state files."""

    def test_create_and_parse_state_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)

            rec = mgr.create_initial_state(
                milestone_id="M99.1",
                plan_filename="M99.1_TEST_PLAN.md",
                baseline_commit="abc1234",
                ui_impact="REQUIRED",
            )

            self.assertEqual(rec.milestone_id, "M99.1")
            self.assertEqual(rec.current_state, WorkflowState.DRAFT)
            self.assertEqual(len(rec.history_log), 1)
            self.assertEqual(rec.history_log[0].actor, "Claude")
            self.assertEqual(rec.plan_ref.ui_impact, "REQUIRED")

            # Transition to ACCEPTED
            rec.transition(WorkflowState.ACCEPTED, WorkflowActor.USER, "Accepted by user in test.")
            mgr.save(rec)

            # Reload from disk
            reloaded = mgr.load("M99.1")
            self.assertEqual(reloaded.current_state, WorkflowState.ACCEPTED)
            self.assertEqual(len(reloaded.history_log), 2)
            self.assertEqual(reloaded.history_log[1].state, "ACCEPTED")
            self.assertEqual(reloaded.history_log[1].actor, "User")

    def test_parse_real_m22_4_state_file(self):
        # Must parse the active docs/plans/M22.4_STATE.md without error
        real_plans_dir = Path("docs/plans")
        if (real_plans_dir / "M22.4_STATE.md").exists():
            mgr = StateFileManager(plans_dir=real_plans_dir)
            rec = mgr.load("M22.4")
            self.assertIn(rec.current_state, list(WorkflowState))
            self.assertEqual(rec.plan_ref.baseline_commit, "8acbad5")
            self.assertEqual(rec.plan_ref.ui_impact, "REQUIRED")
            self.assertGreaterEqual(len(rec.history_log), 2)

    def test_fresh_state_file_has_no_recovery_state(self):
        # An empty/template RECOVERY STATE means the milestone has never
        # paused - parse_content must not treat the placeholder as real data.
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = StateFileManager(plans_dir=Path(tmpdir))
            rec = mgr.create_initial_state("M99.2", "M99.2_TEST_PLAN.md", "abc1234")
            self.assertIsNone(rec.recovery)

    def test_recovery_state_round_trips_through_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)
            rec = mgr.create_initial_state("M99.3", "M99.3_TEST_PLAN.md", "abc1234")
            rec.transition(WorkflowState.ACCEPTED, WorkflowActor.USER, "Accepted.")
            rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Started.")
            rec.transition(
                WorkflowState.WAITING_FOR_MODEL, WorkflowActor.ANTIGRAVITY,
                "Codex quota exhausted mid-implementation.",
            )
            rec.recovery = RecoveryState(
                required_model="Codex",
                current_owner="Antigravity",
                resume_stage="IMPLEMENTATION",
                pause_reason="QUOTA_EXHAUSTED",
                task="M99.3 implementation",
                completed_steps=["Scaffolded usage_meter.py", "Wrote 3 of 6 test files"],
                remaining_steps=["Wire ModelRouter._budget_ok()", "Write remaining 3 test files"],
                changed_files=["uri_core/core/usage_meter.py", "test_usage_meter_recording.py"],
                git_state="uncommitted, working tree only",
                test_state="3/6 new test files passing",
                audit_state="not started",
                last_successful_checkpoint="usage_meter.py scaffold complete",
                retry_metadata="codex quota resets ~04:00 UTC",
            )
            mgr.save(rec)

            reloaded = mgr.load("M99.3")
            self.assertEqual(reloaded.current_state, WorkflowState.WAITING_FOR_MODEL)
            self.assertIsNotNone(reloaded.recovery)
            self.assertEqual(reloaded.recovery.required_model, "Codex")
            self.assertEqual(reloaded.recovery.current_owner, "Antigravity")
            self.assertEqual(reloaded.recovery.resume_stage, "IMPLEMENTATION")
            self.assertEqual(reloaded.recovery.pause_reason, "QUOTA_EXHAUSTED")
            self.assertEqual(
                reloaded.recovery.completed_steps,
                ["Scaffolded usage_meter.py", "Wrote 3 of 6 test files"],
            )
            self.assertEqual(
                reloaded.recovery.changed_files,
                ["uri_core/core/usage_meter.py", "test_usage_meter_recording.py"],
            )
            self.assertEqual(reloaded.recovery.git_state, "uncommitted, working tree only")

            # Resume: Codex becomes available again -> READY_TO_RESUME
            reloaded.transition(
                WorkflowState.READY_TO_RESUME, WorkflowActor.ANTIGRAVITY,
                "Codex quota available again; resuming from preserved checkpoint.",
            )
            mgr.save(reloaded)
            resumed = mgr.load("M99.3")
            self.assertEqual(resumed.current_state, WorkflowState.READY_TO_RESUME)
            # Recovery packet is preserved through the resume transition -
            # idempotent resume needs it to still be there, not wiped.
            self.assertEqual(resumed.recovery.required_model, "Codex")
            self.assertEqual(len(resumed.recovery.completed_steps), 2)


class TestResilienceAndResume(unittest.TestCase):
    """Test handling of interruptions, quota limits, worker failures, and resume."""

    def test_worker_failure_and_resume(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)
            rec = mgr.create_initial_state("M99.2", "M99.2_PLAN.md", "abc1234")

            # Move to ACCEPTED -> IMPLEMENTING
            rec.transition(WorkflowState.ACCEPTED, WorkflowActor.USER, "Accepted.")
            rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Started.")
            mgr.save(rec)

            # Gemma crashes / fails
            rec.transition(WorkflowState.WORKER_FAILED, WorkflowActor.ANTIGRAVITY, "Ollama connection timed out.")
            mgr.save(rec)

            reloaded = mgr.load("M99.2")
            self.assertEqual(reloaded.current_state, WorkflowState.WORKER_FAILED)

            # Resume implementation directly
            reloaded.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Retrying implementation.")
            mgr.save(reloaded)

            final = mgr.load("M99.2")
            self.assertEqual(final.current_state, WorkflowState.IMPLEMENTING)
            self.assertEqual(len(final.history_log), 5)

    def test_quota_waiting_and_resume(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)
            rec = mgr.create_initial_state("M99.3", "M99.3_PLAN.md", "abc1234")
            rec.transition(WorkflowState.ACCEPTED, WorkflowActor.USER, "Accepted.")
            rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Started.")
            rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Auditing.")

            # Claude unavailable for verification -> WAITING_FOR_CLAUDE
            rec.transition(WorkflowState.WAITING_FOR_CLAUDE, WorkflowActor.ANTIGRAVITY, "Claude quota exhausted.")
            mgr.save(rec)

            reloaded = mgr.load("M99.3")
            self.assertEqual(reloaded.current_state, WorkflowState.WAITING_FOR_CLAUDE)

            # Claude returns -> transitions to VERIFYING
            reloaded.transition(WorkflowState.VERIFYING, WorkflowActor.CLAUDE, "Claude returned, resuming review.")
            mgr.save(reloaded)

            final = mgr.load("M99.3")
            self.assertEqual(final.current_state, WorkflowState.VERIFYING)


class TestWorkflowEngineEndToEnd(unittest.TestCase):
    """Test full cycle orchestration through the WorkflowEngine."""

    def test_full_canonical_loop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)

            # 1. Create plan and state
            plan_file = tmppath / "M99.4_PLAN.md"
            plan_file.write_text(
                "### Objective\nTest capability\n\n"
                "### Scope\n`uri_core/test.py`\n\n"
                "### Out-of-Scope / Protected Files\n`orchestrator.py`\n\n"
                "### Acceptance Criteria\nCriterion 1\n\n"
                "### Test Plan\n`pytest tests/test.py`\n\n"
                "### Security Considerations\nKeep auth intact\n\n"
                "### UI IMPACT\nNONE (Backend internal only)\n",
                encoding="utf-8",
            )
            mgr.create_initial_state("M99.4", "M99.4_PLAN.md", "abc1234", ui_impact="NONE", ui_reason="Backend internal")

            engine = WorkflowEngine(plans_dir=tmppath)

            # 2. User accepts
            rec = engine.user_accept_plan("M99.4", notes="Looks solid.")
            self.assertEqual(rec.current_state, WorkflowState.ACCEPTED)

            # 3. Gemma implements (simulated response)
            dry_run_gemma = (
                "```markdown\n"
                "### GEMMA RETURN REPORT\n"
                "- **Milestone ID:** M99.4\n"
                "- **Summary of Actions:** Implemented test capability.\n"
                "- **Files Modified/Created:** uri_core/test.py (+25 lines)\n"
                "- **Tests Performed:** pytest tests/test.py (5 passed)\n"
                "- **Assumptions & Decisions:** None.\n"
                "- **Known Issues / Gaps:** None.\n"
                "```"
            )
            rec = engine.start_implementation("M99.4", dry_run_response=dry_run_gemma)
            self.assertIsNotNone(rec.gemma_report)
            self.assertEqual(rec.gemma_report.summary_of_actions, "Implemented test capability.")

            # 4. Antigravity audits
            rec = engine.perform_audit("M99.4")
            self.assertIsNotNone(rec.audit_report)
            self.assertEqual(rec.current_state, WorkflowState.VERIFYING)

            # 5. Claude verifies
            rec = engine.record_claude_verification(
                "M99.4",
                decision="VERIFIED",
                basis="All 5 unit tests pass; no security boundaries violated.",
            )
            self.assertEqual(rec.current_state, WorkflowState.VERIFIED)
            self.assertEqual(rec.verification.decision, "VERIFIED")

            # 6. Antigravity releases
            rec = engine.release_milestone("M99.4", commit_hash="11223344")
            self.assertEqual(rec.current_state, WorkflowState.COMPLETE)
            self.assertEqual(rec.release_commit, "11223344")

    def test_user_modify_plan_resets_to_draft(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)
            mgr.create_initial_state("M99.5", "M99.5_PLAN.md", "abc1234")
            engine = WorkflowEngine(plans_dir=tmppath)

            # User requests modifications
            rec = engine.user_modify_plan("M99.5", notes="Clarify scope section 2.")
            self.assertEqual(rec.current_state, WorkflowState.DRAFT)
            self.assertIn("User requested modifications", rec.history_log[-1].note)

    def test_not_verified_rejection_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mgr = StateFileManager(plans_dir=tmppath)
            rec = mgr.create_initial_state("M99.6", "M99.6_PLAN.md", "abc1234")
            rec.transition(WorkflowState.ACCEPTED, WorkflowActor.USER, "Accepted.")
            rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Implemented.")
            rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audited.")
            rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Submitted to Claude.")
            mgr.save(rec)

            engine = WorkflowEngine(plans_dir=tmppath)

            # Claude rejects verification
            rec = engine.record_claude_verification(
                "M99.6",
                decision="NOT VERIFIED",
                basis="Test coverage insufficient for boundary case.",
                remaining_gaps="Missing edge case tests.",
            )
            self.assertEqual(rec.current_state, WorkflowState.NOT_VERIFIED)
            self.assertEqual(rec.verification.decision, "NOT VERIFIED")

            # Must return to FIXING, cannot jump directly to COMPLETE
            with self.assertRaises(InvariantViolationError):
                engine.release_milestone("M99.6", commit_hash="badcommit")

            # Transitions to FIXING
            rec.transition(WorkflowState.FIXING, WorkflowActor.ANTIGRAVITY, "Applying fixes requested by Claude.")
            self.assertEqual(rec.current_state, WorkflowState.FIXING)

    def test_implementing_to_auditing_automatic_execution(self):
        """Regression test proving IMPLEMENTING -> AUDITING causes automatic audit execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "M99.AUTO_PLAN.md").write_text("# M99.AUTO Plan\n\n## 1. Scope\n- None\n", encoding="utf-8")
            mgr = StateFileManager(plans_dir=tmppath)
            mgr.create_initial_state("M99.AUTO", "M99.AUTO_PLAN.md", "abc1234", ui_impact="NONE")
            engine = WorkflowEngine(plans_dir=tmppath)
            engine.user_accept_plan("M99.AUTO", notes="Plan accepted.")

            dry_run_gemma = (
                "```markdown\n"
                "### GEMMA RETURN REPORT\n"
                "- **Milestone ID:** M99.AUTO\n"
                "- **Summary of Actions:** Completed auto-audit test capability.\n"
                "- **Files Modified/Created:** None.\n"
                "- **Tests Performed:** None.\n"
                "- **Assumptions & Decisions:** None.\n"
                "- **Known Issues / Gaps:** None.\n"
                "```"
            )

            # Invoking start_implementation with default auto_audit=True MUST automatically execute audit
            rec = engine.start_implementation("M99.AUTO", dry_run_response=dry_run_gemma, auto_audit=True)

            # Prove audit was automatically executed:
            self.assertIsNotNone(rec.audit_report)
            self.assertEqual(rec.current_state, WorkflowState.VERIFYING)

            # Verify history log contains IMPLEMENTING and AUDITING in sequence
            states_in_log = [e.state for e in rec.history_log]
            self.assertIn("IMPLEMENTING", states_in_log)
            self.assertIn("AUDITING", states_in_log)
            impl_idx = states_in_log.index("IMPLEMENTING")
            audit_idx = states_in_log.index("AUDITING")
            self.assertLess(impl_idx, audit_idx)

            # Also verify explicit auto_audit=False leaves state at IMPLEMENTING without running audit
            (tmppath / "M99.NOAUTO_PLAN.md").write_text("# M99.NOAUTO Plan\n\n## 1. Scope\n- None\n", encoding="utf-8")
            mgr.create_initial_state("M99.NOAUTO", "M99.NOAUTO_PLAN.md", "abc1234", ui_impact="NONE")
            engine.user_accept_plan("M99.NOAUTO", notes="Plan accepted.")
            rec_noauto = engine.start_implementation("M99.NOAUTO", dry_run_response=dry_run_gemma, auto_audit=False)
            self.assertEqual(rec_noauto.current_state, WorkflowState.IMPLEMENTING)
            self.assertEqual(rec_noauto.audit_report.code_correctness_findings, "")

            # And calling perform_audit from IMPLEMENTING executes audit and moves to AUDITING -> VERIFYING
            rec_audited = engine.perform_audit("M99.NOAUTO")
            self.assertNotEqual(rec_audited.audit_report.code_correctness_findings, "")
            self.assertEqual(rec_audited.current_state, WorkflowState.VERIFYING)


class TestDriversAndReporting(unittest.TestCase):
    """Test Gemma task brief formatting and report generation."""

    def test_gemma_driver_prompt_and_report_parsing(self):
        driver = GemmaDriver()
        brief = TaskBrief(
            milestone_id="M99.7",
            objective="Implement Resolver",
            scope="uri_core/resolver.py",
            out_of_scope_protected="orchestrator.py",
            acceptance_criteria="All grants resolved.",
            test_plan="pytest tests/resolver",
            security_considerations="No privilege escalation.",
            ui_impact="REQUIRED",
            raw_markdown="",
        )
        prompt = driver.build_prompt(brief)
        self.assertIn("NON-NEGOTIABLE BOUNDARIES", prompt)
        self.assertIn("ZERO Git authority", prompt)
        self.assertIn("M99.7", prompt)
        self.assertIn("GEMMA RETURN REPORT", prompt)

        mock_response = (
            "Here is the report:\n"
            "```markdown\n"
            "### GEMMA RETURN REPORT\n"
            "- **Milestone ID:** M99.7\n"
            "- **Summary of Actions:** Created resolver class.\n"
            "- **Files Modified/Created:** uri_core/resolver.py (+80 lines)\n"
            "- **Tests Performed:** pytest tests/resolver (10 passed)\n"
            "- **Assumptions & Decisions:** Cached resolutions in memory.\n"
            "- **Known Issues / Gaps:** None.\n"
            "```"
        )
        report = driver.parse_return_report(mock_response, "M99.7")
        self.assertEqual(report.milestone_id, "M99.7")
        self.assertEqual(report.summary_of_actions, "Created resolver class.")
        self.assertEqual(report.files_modified_created, "uri_core/resolver.py (+80 lines)")
        self.assertEqual(report.tests_performed, "pytest tests/resolver (10 passed)")

    def test_antigravity_audit_report_formatting(self):
        auditor = AntigravityAuditor()
        findings = AuditFindings(
            milestone_id="M99.8",
            changed_files=["uri_core/resolver.py"],
            protected_boundary_violations=[],
            test_results=[
                TestExecutionResult(
                    command="pytest tests/test_resolver.py",
                    returncode=0,
                    passed_count=8,
                    failed_count=0,
                    output="8 passed",
                    duration_sec=1.2,
                )
            ],
            test_sufficiency_notes=["Verified 8 test functions with 16 assertions."],
            security_notes=["Protected boundaries intact."],
            ui_parity_notes=["UI Parity verified."],
            fixes_applied=["Fixed typo in import."],
            outstanding_gaps=[],
            is_audit_passed=True,
        )
        report = auditor.format_audit_report(findings)
        self.assertEqual(report.milestone_id, "M99.8")
        self.assertIn("Inspected 1 changed files", report.code_correctness_findings)
        self.assertIn("8 passed", report.evidence)
        self.assertIn("Fixed typo in import.", report.fixes_applied)
        self.assertIn("None. Ready for Claude independent verification.", report.outstanding_gaps)


class TestAuditor(unittest.TestCase):
    """Test auditor checks for protected files and UI parity."""

    def test_protected_boundary_detection(self):
        auditor = AntigravityAuditor()
        violations = auditor.check_protected_boundaries([
            "uri_core/service.py",
            "uri_core/core/approval_gate.py",  # Protected!
        ])
        self.assertIn("uri_core/core/approval_gate.py", violations)
        self.assertEqual(len(violations), 1)

    def test_ui_parity_check_required_fails_when_no_ui_files(self):
        auditor = AntigravityAuditor()
        plan_ref = PlanReference(ui_impact="REQUIRED")
        changed = ["uri_core/service.py", "tests/test_service.py"]
        notes = auditor.audit_ui_impact(plan_ref, changed)
        self.assertTrue(any("VIOLATION" in n for n in notes))

    def test_ui_parity_check_required_passes_when_ui_files_present(self):
        auditor = AntigravityAuditor()
        plan_ref = PlanReference(ui_impact="REQUIRED")
        changed = ["uri_core/service.py", "uri_ui/lib/main.dart"]
        notes = auditor.audit_ui_impact(plan_ref, changed)
        self.assertTrue(any("UI Parity verified" in n for n in notes))


class MockClaudeBridge:
    def __init__(
        self,
        session_data=None,
        status_code=0,
        err_msg="Success",
        send_response=None,
    ):
        self.session_data = session_data or {
            "pid": 23968,
            "sessionId": "4b30c24f-c4cc-413d-a0ea-d85b5620dde1",
            "messagingSocketPath": r"\\.\pipe\LOCAL\cc-msg-test",
            "peerToken": "mock-token",
            "status": "idle",
        }
        self.status_code = status_code
        self.err_msg = err_msg
        self.send_response = send_response or {
            "ok": True,
            "status_code": 0,
            "error": None,
            "response_text": "DECISION: VERIFIED\nBASIS: All 10 tests passing; clean implementation.\nREMAINING_GAPS: None.",
        }
        self.sent_prompts = []
        self.STATUS_TIMEOUT = 7

    def resolve_single_session(self, target_session_id=None, target_pid=None, cwd=None):
        if self.status_code != 0:
            return None, self.status_code, self.err_msg
        return self.session_data, 0, "Resolved"

    def send_message_to_claude(self, session, prompt, priority="now", timeout_sec=120, wait_if_busy=True):
        self.sent_prompts.append(prompt)
        return self.send_response


class TestClaudeBridgeIntegration(unittest.TestCase):
    """Test Claude Bridge integration with workflow state machine."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)
        # Create plan file
        (self.tmppath / "M99.9_PLAN.md").write_text(
            "# Milestone M99.9 Plan\n\n"
            "### Scope\n`uri_core/test.py`\n\n"
            "### Out-of-Scope / Protected Files\n`orchestrator.py`\n\n"
            "### Acceptance Criteria\nCriterion 1\n\n"
            "### Test Plan\n`echo pass`\n\n"
            "### Security Considerations\nKeep auth intact\n\n"
            "### UI IMPACT\nNONE (Backend internal only)\n",
            encoding="utf-8",
        )
        self.state_mgr = StateFileManager(plans_dir=self.tmppath)
        self.engine = WorkflowEngine(plans_dir=self.tmppath)
        # Create an initial test milestone
        self.state_mgr.create_initial_state("M99.9", "M99.9_PLAN.md", "baseline123", ui_impact="NONE", ui_reason="Backend internal")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _mock_gemma_report(self, milestone_id: str = "M99.9") -> str:
        return (
            "```markdown\n"
            f"### GEMMA RETURN REPORT\n"
            f"- **Milestone ID:** {milestone_id}\n"
            "- **Summary of Actions:** Implemented test capability.\n"
            "- **Files Modified/Created:** uri_core/test.py (+25 lines)\n"
            "- **Tests Performed:** echo pass\n"
            "- **Assumptions & Decisions:** None.\n"
            "- **Known Issues / Gaps:** None.\n"
            "```"
        )

    def _advance_to_verifying(self, milestone_id: str = "M99.9"):
        self.engine.user_accept_plan(milestone_id, notes="Approved.")
        self.engine.start_implementation(milestone_id, dry_run_response=self._mock_gemma_report(milestone_id))
        self.engine.perform_audit(milestone_id, test_commands=["echo test pass"])

    def test_verifying_to_claude_bridge_handoff(self):
        # In ACCEPTED state, handoff is rejected
        mock_bridge = MockClaudeBridge()
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        self.engine.user_accept_plan("M99.9", notes="Approved.")

        with self.assertRaises(InvariantViolationError) as ctx:
            verifier.verify_milestone(self.engine, "M99.9")
        self.assertIn("Milestone must be in 'VERIFYING' state first", str(ctx.exception))

        # Advance to VERIFYING
        self.engine.start_implementation("M99.9", dry_run_response=self._mock_gemma_report("M99.9"))
        self.engine.perform_audit("M99.9", test_commands=["echo test pass"])
        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.VERIFYING)

        # Handoff succeeds
        res = verifier.verify_milestone(self.engine, "M99.9")
        self.assertTrue(res.ok)
        self.assertEqual(len(mock_bridge.sent_prompts), 1)
        self.assertIn("M99.9", mock_bridge.sent_prompts[0])
        self.assertIn("STATE: VERIFYING", mock_bridge.sent_prompts[0])
        self.assertIn("INDEPENDENT VERIFICATION CRITERIA", mock_bridge.sent_prompts[0])

    def test_claude_verified_decision(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            send_response={
                "ok": True,
                "status_code": 0,
                "error": None,
                "response_text": "DECISION: VERIFIED\nBASIS: All tests passing; criteria met.\nREMAINING_GAPS: None.",
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        res = verifier.verify_milestone(self.engine, "M99.9")

        self.assertTrue(res.ok)
        self.assertEqual(res.decision, "VERIFIED")
        self.assertEqual(res.state, WorkflowState.VERIFIED)
        self.assertTrue(res.ready_for_release)
        self.assertEqual(res.release_authority, "Claude")

        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.VERIFIED)
        self.assertEqual(rec.verification.decision, "VERIFIED")
        self.assertEqual(rec.verification.remaining_gaps, "None.")

    def test_claude_not_verified_decision(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            send_response={
                "ok": True,
                "status_code": 0,
                "error": None,
                "response_text": "DECISION: NOT VERIFIED\nBASIS: Security regression in role check.\nREMAINING_GAPS: Missing role validation test.",
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        res = verifier.verify_milestone(self.engine, "M99.9")

        self.assertTrue(res.ok)
        self.assertEqual(res.decision, "NOT VERIFIED")
        # Advances to NOT_VERIFIED and then transitions to FIXING
        self.assertEqual(res.state, WorkflowState.FIXING)
        self.assertFalse(res.ready_for_release)
        self.assertIsNone(res.release_authority)

        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.FIXING)
        self.assertEqual(rec.verification.decision, "NOT VERIFIED")
        self.assertIn("Security regression", rec.verification.basis)
        self.assertIn("Missing role validation test", rec.verification.remaining_gaps)

    def test_claude_refusal_text_defaults_to_not_verified(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            send_response={
                "ok": True,
                "status_code": 0,
                "error": None,
                "response_text": (
                    "This is not a harmless test — I'm refusing to issue VERIFIED, and I want to flag what actually happened.\n"
                    "What I did not do: declare VERIFIED, commit, push, or delete anything."
                ),
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        res = verifier.verify_milestone(self.engine, "M99.9")

        self.assertTrue(res.ok)
        self.assertEqual(res.decision, "NOT VERIFIED")
        self.assertEqual(res.state, WorkflowState.FIXING)
        self.assertFalse(res.ready_for_release)
        self.assertIsNone(res.release_authority)

    def test_bridge_unavailable_or_timeout(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            send_response={
                "ok": False,
                "status_code": 7,  # STATUS_TIMEOUT
                "error": "Timed out waiting for Claude response after 120s.",
                "response_text": "",
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        res = verifier.verify_milestone(self.engine, "M99.9")

        self.assertFalse(res.ok)
        self.assertEqual(res.decision, "TIMEOUT")
        self.assertEqual(res.state, WorkflowState.WAITING_FOR_CLAUDE)

        # State preserved in WAITING_FOR_CLAUDE
        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.WAITING_FOR_CLAUDE)
        self.assertIsNotNone(rec.audit_report)

        # Can resume back to VERIFYING
        rec = self.engine.resume_from_interruption(
            "M99.9",
            actor=WorkflowActor.ANTIGRAVITY,
            target_state=WorkflowState.VERIFYING,
            note="Claude session resumed.",
        )
        self.assertEqual(rec.current_state, WorkflowState.VERIFYING)

    def test_existing_claude_session_unavailable(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            status_code=1,
            err_msg="Claude process is not running.",
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        res = verifier.verify_milestone(self.engine, "M99.9")

        self.assertFalse(res.ok)
        self.assertEqual(res.decision, "UNAVAILABLE")
        self.assertEqual(res.state, WorkflowState.WAITING_FOR_CLAUDE)

        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.WAITING_FOR_CLAUDE)

    def test_no_accidental_new_claude_session(self):
        self._advance_to_verifying("M99.9")
        import subprocess

        # Patch subprocess to ensure NO process creation happens
        def fail_if_called(*args, **kwargs):
            raise AssertionError("Accidental process creation detected!")

        orig_popen = subprocess.Popen
        subprocess.Popen = fail_if_called
        try:
            mock_bridge = MockClaudeBridge()
            verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
            res = verifier.verify_milestone(self.engine, "M99.9")
            self.assertTrue(res.ok)
        finally:
            subprocess.Popen = orig_popen

    def test_persisted_claude_decision(self):
        self._advance_to_verifying("M99.9")
        mock_bridge = MockClaudeBridge(
            send_response={
                "ok": True,
                "status_code": 0,
                "error": None,
                "response_text": "DECISION: VERIFIED\nBASIS: All criteria met.\nREMAINING_GAPS: None.",
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge)
        verifier.verify_milestone(self.engine, "M99.9")

        # Check raw file on disk
        state_file = self.tmppath / "M99.9_STATE.md"
        content = state_file.read_text(encoding="utf-8")
        self.assertIn("## CLAUDE VERIFICATION DECISION", content)
        self.assertIn("- **Decision:** VERIFIED", content)
        self.assertIn("- **Basis:** All criteria met.", content)
        self.assertIn("- **Remaining gaps (if NOT VERIFIED):** None.", content)

    def test_release_remains_blocked_until_claude_verified(self):
        # 1. Blocked in AUDITING
        self.engine.user_accept_plan("M99.9", notes="Approved.")
        self.engine.start_implementation("M99.9", dry_run_response=self._mock_gemma_report("M99.9"))
        with self.assertRaises(InvariantViolationError):
            self.engine.release_milestone("M99.9", commit_hash="11223344", actor=WorkflowActor.CLAUDE)

        # 2. Blocked in VERIFYING
        self.engine.perform_audit("M99.9", test_commands=["echo test"])
        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.VERIFYING)
        with self.assertRaises(InvariantViolationError):
            self.engine.release_milestone("M99.9", commit_hash="11223344", actor=WorkflowActor.CLAUDE)

        # 3. Blocked in NOT_VERIFIED / FIXING
        mock_bridge_reject = MockClaudeBridge(
            send_response={
                "ok": True,
                "status_code": 0,
                "error": None,
                "response_text": "DECISION: NOT VERIFIED\nBASIS: Bugs found.\nREMAINING_GAPS: Bug #1.",
            }
        )
        verifier = ClaudeBridgeVerifier(bridge_module=mock_bridge_reject)
        verifier.verify_milestone(self.engine, "M99.9")
        with self.assertRaises(InvariantViolationError):
            self.engine.release_milestone("M99.9", commit_hash="11223344", actor=WorkflowActor.CLAUDE)

        # 4. Now verify successfully
        self.engine.perform_audit("M99.9", test_commands=["echo test fix"])
        mock_bridge_verify = MockClaudeBridge()
        verifier2 = ClaudeBridgeVerifier(bridge_module=mock_bridge_verify)
        verifier2.verify_milestone(self.engine, "M99.9")
        rec = self.engine.get_record("M99.9")
        self.assertEqual(rec.current_state, WorkflowState.VERIFIED)

        # 5. Antigravity STILL cannot release (Claude is release authority)
        with self.assertRaises(InvariantViolationError) as ctx:
            self.engine.release_milestone("M99.9", commit_hash="11223344", actor=WorkflowActor.ANTIGRAVITY)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

        # 6. Claude releases successfully
        rec = self.engine.release_milestone("M99.9", commit_hash="11223344", actor=WorkflowActor.CLAUDE)
        self.assertEqual(rec.current_state, WorkflowState.COMPLETE)
        self.assertEqual(rec.release_commit, "11223344")
        self.assertEqual(rec.release_pushed, "true")


class TestFileWriteAuthority(unittest.TestCase):
    """Test file-write authority enforcement for implementation and review actors."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)
        # Create a mock plan with explicit scope
        self.plan_file = self.tmppath / "docs" / "plans" / "M22.4_PLAN.md"
        self.plan_file.parent.mkdir(parents=True, exist_ok=True)
        self.plan_file.write_text(
            "# Milestone M22.4 Plan\n\n"
            "## 3. Scope\n"
            "- `uri_core/core/capability_resolver.py`\n"
            "- `capability_grants.json`\n"
            "- `orchestrator.py`\n\n"
            "## 4. Out-of-Scope / Protected Files\n"
            "- `uri_core/core/dispatcher.py`\n"
            "- `uri_core/core/principal_context.py`\n"
            "- `uri_core/core/approval_gate.py` (narrow exception)\n\n"
            "## UI IMPACT\nREQUIRED\n",
            encoding="utf-8",
        )
        self.state_mgr = StateFileManager(plans_dir=self.tmppath / "docs" / "plans")
        self.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "baseline8ac", ui_impact="REQUIRED")
        self.engine = WorkflowEngine(plans_dir=self.tmppath / "docs" / "plans", repo_root=self.tmppath)
        self.authorizer = self.engine.file_authorizer

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_writes_blocked_before_user_acceptance(self):
        # Initial state is DRAFT
        rec = self.engine.get_record("M22.4")
        self.assertEqual(rec.current_state, WorkflowState.DRAFT)

        res = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_core/core/capability_resolver.py")
        self.assertFalse(res.allowed)
        self.assertIn("Writes are blocked before user acceptance", res.reason)

        res_ag = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "uri_core/core/capability_resolver.py")
        self.assertFalse(res_ag.allowed)
        self.assertIn("Writes are blocked before user acceptance", res_ag.reason)

        self.assertGreater(len(self.authorizer.rejected_attempts), 0)

    def test_gemma_can_write_within_accepted_scope(self):
        rec = self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start impl.")
        self.engine.state_mgr.save(rec)

        # 1. In-scope application file
        res = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_core/core/capability_resolver.py")
        self.assertTrue(res.allowed)

        # 2. Test file
        res_test = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "tests/test_capability_resolver.py")
        self.assertTrue(res_test.allowed)

        # 3. UI file when UI IMPACT: REQUIRED
        res_ui = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_ui/lib/screens/grants_screen.dart")
        self.assertTrue(res_ui.allowed)

    def test_codex_has_the_same_implementer_write_authority_as_gemma(self):
        # 2026-09-11 governance revision: Codex is a standing routed
        # implementer with the identical authority shape Gemma has -
        # no longer a reserve/fallback actor with zero write authority.
        rec = self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start impl.")
        self.engine.state_mgr.save(rec)

        res = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "uri_core/core/capability_resolver.py")
        self.assertTrue(res.allowed)

        res_test = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "tests/test_capability_resolver.py")
        self.assertTrue(res_test.allowed)

        res_ui = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "uri_ui/lib/screens/grants_screen.dart")
        self.assertTrue(res_ui.allowed)

        # Still bounded exactly like Gemma: protected files and
        # out-of-scope paths remain rejected.
        res_disp = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "uri_core/core/dispatcher.py")
        self.assertFalse(res_disp.allowed)

        res_wf = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "scripts/dev_workflow/state_machine.py")
        self.assertFalse(res_wf.allowed)
        self.assertIn("strictly forbidden from altering workflow authority rules", res_wf.reason)

        res_out = self.authorizer.authorize_write(rec, WorkflowActor.CODEX, "uri_core/unrelated_module.py")
        self.assertFalse(res_out.allowed)

    def test_qwen_still_has_zero_write_authority(self):
        # Qwen remains reserve-only, unlike Codex above.
        rec = self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start impl.")
        self.engine.state_mgr.save(rec)

        res = self.authorizer.authorize_write(rec, WorkflowActor.QWEN, "uri_core/core/capability_resolver.py")
        self.assertFalse(res.allowed)
        self.assertIn("reserve only", res.reason)

    def test_gemma_cannot_write_protected_or_out_of_scope_paths(self):
        rec = self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start impl.")

        # Protected runtime file without exception
        res_disp = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_core/core/dispatcher.py")
        self.assertFalse(res_disp.allowed)
        self.assertIn("cannot modify protected runtime file", res_disp.reason)

        # Workflow authority file
        res_wf = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "scripts/dev_workflow/state_machine.py")
        self.assertFalse(res_wf.allowed)
        self.assertIn("strictly forbidden from altering workflow authority rules", res_wf.reason)

        # Arbitrary out of scope file
        res_out = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_core/unrelated_module.py")
        self.assertFalse(res_out.allowed)
        self.assertIn("outside accepted milestone scope", res_out.reason)

        # UI file when UI impact is NONE
        rec_none = self.state_mgr.create_initial_state("M22.4_NO_UI", "M22.4_PLAN.md", "base", ui_impact="NONE")
        self.engine.user_accept_plan("M22.4_NO_UI")
        rec_none = self.engine.get_record("M22.4_NO_UI")
        rec_none.plan_ref.ui_impact = "NONE"
        res_ui_none = self.authorizer.authorize_write(rec_none, WorkflowActor.GEMMA, "uri_ui/lib/main.dart")
        self.assertFalse(res_ui_none.allowed)
        self.assertIn("UI IMPACT is not REQUIRED", res_ui_none.reason)

    def test_antigravity_can_fix_within_scope(self):
        self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.FIXING, WorkflowActor.ANTIGRAVITY, "Fixing gaps.")

        # In-scope file fix
        res = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "uri_core/core/capability_resolver.py")
        self.assertTrue(res.allowed)

        # Test fix
        res_test = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "tests/test_resolver.py")
        self.assertTrue(res_test.allowed)

        # Arbitrary out-of-scope file
        res_bad = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "uri_core/unrelated_module.py")
        self.assertFalse(res_bad.allowed)
        self.assertIn("cannot silently expand milestone scope", res_bad.reason)

    def test_antigravity_cannot_alter_protected_authority_boundaries(self):
        self.engine.user_accept_plan("M22.4", notes="Accepted.")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")

        # Antigravity cannot alter state_machine.py or AGENTS.md during normal milestone
        res_sm = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "scripts/dev_workflow/state_machine.py")
        self.assertFalse(res_sm.allowed)
        self.assertIn("cannot alter protected authority boundaries", res_sm.reason)

        res_ag = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "AGENTS.md")
        self.assertFalse(res_ag.allowed)
        self.assertIn("cannot alter protected authority boundaries", res_ag.reason)

    def test_antigravity_cannot_commit_push(self):
        self.engine.user_accept_plan("M22.4")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Audit pass.")
        self.engine.state_mgr.save(rec)
        self.engine.record_claude_verification("M22.4", decision="VERIFIED", basis="Approved.")

        with self.assertRaises(InvariantViolationError) as ctx:
            self.engine.release_milestone("M22.4", commit_hash="11223344", actor=WorkflowActor.ANTIGRAVITY)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

    def test_claude_required_for_release(self):
        self.engine.user_accept_plan("M22.4")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Audit pass.")
        self.engine.state_mgr.save(rec)
        self.engine.record_claude_verification("M22.4", decision="VERIFIED", basis="Approved.")

        # User cannot release
        with self.assertRaises(InvariantViolationError) as ctx:
            self.engine.release_milestone("M22.4", commit_hash="11223344", actor=WorkflowActor.USER)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

        # Claude releases
        rec = self.engine.release_milestone("M22.4", commit_hash="11223344", actor=WorkflowActor.CLAUDE)
        self.assertEqual(rec.current_state, WorkflowState.COMPLETE)

    def test_write_authority_survives_workflow_resume(self):
        self.engine.user_accept_plan("M22.4")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        rec.transition(WorkflowState.BLOCKED, WorkflowActor.ANTIGRAVITY, "Interrupted.")
        self.engine.state_mgr.save(rec)

        # Writes blocked during waiting/blocked state
        res_waiting = self.authorizer.authorize_write(rec, WorkflowActor.GEMMA, "uri_core/core/capability_resolver.py")
        self.assertFalse(res_waiting.allowed)

        # Resume to FIXING
        rec_resumed = self.engine.resume_from_interruption(
            "M22.4",
            actor=WorkflowActor.ANTIGRAVITY,
            target_state=WorkflowState.FIXING,
            note="Resumed cycle.",
        )
        self.assertEqual(rec_resumed.current_state, WorkflowState.FIXING)

        # Writes authorized again after resume
        res_active = self.authorizer.authorize_write(rec_resumed, WorkflowActor.ANTIGRAVITY, "uri_core/core/capability_resolver.py")
        self.assertTrue(res_active.allowed)

    def test_antigravity_can_write_state_files(self):
        """Antigravity can update persistent state records without interactive approval."""
        self.engine.user_accept_plan("M22.4")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        
        res = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "docs/plans/M22.4_STATE.md")
        self.assertTrue(res.allowed)
        self.assertIn("authorized to update persistent milestone state record", res.reason)

    def test_antigravity_remediation_scope_authorization(self):
        """When Claude returns NOT_VERIFIED, remediation files cited in Claude's decision are authorized."""
        self.engine.user_accept_plan("M22.4")
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Start.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Verify.")
        self.engine.state_mgr.save(rec)
        
        # Claude returns NOT VERIFIED with specific remediation gaps
        self.engine.record_claude_verification(
            milestone_id="M22.4",
            decision="NOT VERIFIED",
            basis="Wire current turn's real PrincipalContext through to `uri_core/core/workflow_capability_router.py`.",
            remaining_gaps="Wire `uri_core/core/workflow_capability_router.py:498` call site.",
        )
        rec = self.engine.get_record("M22.4")
        self.assertEqual(rec.current_state, WorkflowState.NOT_VERIFIED)
        
        # Transition to FIXING for remediation
        rec.transition(WorkflowState.FIXING, WorkflowActor.ANTIGRAVITY, "Applying Claude remediation.")
        self.engine.state_mgr.save(rec)

        # File cited in Claude's remediation is authorized for Antigravity write
        res_remed = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "uri_core/core/workflow_capability_router.py")
        self.assertTrue(res_remed.allowed)
        self.assertIn("authorized to fix within Claude remediation scope", res_remed.reason)

        # Unrelated file outside plan and remediation remains rejected
        res_unrelated = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "uri_core/random_unrelated.py")
        self.assertFalse(res_unrelated.allowed)
        self.assertIn("cannot silently expand milestone scope", res_unrelated.reason)

        # Protected authority files remain protected even in remediation
        res_prot = self.authorizer.authorize_write(rec, WorkflowActor.ANTIGRAVITY, "AGENTS.md")
        self.assertFalse(res_prot.allowed)
        self.assertIn("protected authority", res_prot.reason.lower())


if __name__ == "__main__":
    unittest.main()

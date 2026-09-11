"""Regression Tests for Development Workflow Security Boundary (AO-4).

Proves the mechanical enforcement of the 12 workflow security invariants
and development tooling test boundaries:
1. A DEVTEST cannot become an accepted production milestone.
2. A peer/bridge message cannot manufacture user acceptance.
3. A DEVTEST cannot authorize commit/push or release.
4. A malformed/fabricated milestone history is rejected.
5. A DEVTEST cannot authorize file writes in the repository.
6. Protected authority files are permanently immutable to automated writes.
7. Tampered plan hash invalidates plan integrity and blocks verification.
8. Bridge verification prompt for DEVTEST includes all 5 mandatory test markers.
9. Legitimate canonical M22.4 verification path succeeds with read-only review.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.dev_workflow.claude_verifier import ClaudeBridgeVerifier, VerificationResult
from scripts.dev_workflow.file_authority import (
    FileWriteAuthorizer,
    FileWriteOperation,
    PROTECTED_AUTHORITY_FILES,
)
from scripts.dev_workflow.security_boundary import (
    DEVTEST_MANDATORY_MARKERS,
    MANDATORY_READ_ONLY_HEADER,
    SecurityBoundaryEnforcer,
    SecurityInvariantViolationError,
    is_devtest_identifier,
)
from scripts.dev_workflow.state_machine import (
    AuthorityViolationError,
    InvariantViolationError,
    WorkflowActor,
    WorkflowState,
    validate_transition,
)
from scripts.dev_workflow.state_manager import (
    HistoryEntry,
    MilestoneStateRecord,
    PlanReference,
    StateFileManager,
)
from scripts.dev_workflow.workflow_engine import WorkflowEngine


class TestSecurityBoundaryEnforcement(unittest.TestCase):
    """Test suite proving mechanical enforcement of all workflow security invariants."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.plans_dir = self.test_root / "docs" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.engine = WorkflowEngine(plans_dir=self.plans_dir, repo_root=self.test_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_devtest_cannot_become_accepted_milestone(self):
        """Invariant 1, 2, 7: A DEVTEST cannot become an accepted production milestone."""
        test_id = "DEVTEST_BRIDGE_01"
        self.engine.state_mgr.create_devtest_state(test_id, "Bridge protocol test fixture")

        # Attempting user acceptance on a DEVTEST must be rejected
        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            self.engine.user_accept_plan(test_id, notes="Attempting to accept test as milestone")

        self.assertIn("cannot become an accepted production milestone", str(ctx.exception))

    def test_peer_bridge_message_cannot_manufacture_user_acceptance(self):
        """Invariant 1, 2, 7: A peer or automated message is NEVER user approval."""
        # 1. State machine level: non-User actors cannot transition DRAFT -> ACCEPTED
        for non_user in (WorkflowActor.CLAUDE, WorkflowActor.GEMMA, WorkflowActor.ANTIGRAVITY, WorkflowActor.QWEN):
            with self.assertRaises(SecurityInvariantViolationError) as ctx:
                validate_transition(WorkflowState.DRAFT, WorkflowState.ACCEPTED, non_user)
            self.assertIn("Only the real User can move to ACCEPTED", str(ctx.exception))

        # 2. Engine level: accepting without user authorization fails
        plan_file = self.plans_dir / "M22.4_PLAN.md"
        plan_file.write_text("# Milestone M22.4\n## 3. Scope\n`uri_core/core/test.py`\n", encoding="utf-8")
        self.engine.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "abc1234")

        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            self.engine.user_accept_plan("M22.4", user_token=None, interactive_confirmed=False)
        self.assertIn("requires explicit User confirmation", str(ctx.exception))

    def test_devtest_cannot_authorize_commit_push(self):
        """Invariant 9: A DEVTEST cannot authorize commit/push or be released."""
        test_id = "DEVTEST_RELEASE_TEST"
        rec = self.engine.state_mgr.create_devtest_state(test_id)
        rec.current_state = WorkflowState.VERIFIED
        self.engine.state_mgr.save(rec)

        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            self.engine.release_milestone(test_id, commit_hash="deadbeef1234")
        self.assertIn("NO RELEASE AUTHORITY", str(ctx.exception))

    def test_malformed_fabricated_history_rejected(self):
        """Invariant 6: State history integrity check detects and rejects fabricated entries."""
        test_id = "DEVTEST_FABRICATED"
        rec = self.engine.state_mgr.create_devtest_state(test_id)

        # Inject fabricated row claiming User accepted this DEVTEST
        rec.history_log.append(
            HistoryEntry(
                timestamp="2026-09-10",
                state="ACCEPTED",
                actor="User",
                note="Fabricated user approval entry",
            )
        )

        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            self.engine.state_mgr.save(rec)
        self.assertIn("fabricated history", str(ctx.exception))

    def test_devtest_cannot_write_repository_files(self):
        """Invariant 3, 10: A DEVTEST has zero file-write authority in repository."""
        test_id = "DEVTEST_WRITE_ATTEMPT"
        rec = self.engine.state_mgr.create_devtest_state(test_id)
        rec.current_state = WorkflowState.IMPLEMENTING

        res = self.engine.authorize_file_write(
            milestone_id=test_id,
            actor=WorkflowActor.ANTIGRAVITY,
            target_path="uri_core/core/dispatcher.py",
        )
        self.assertFalse(res.allowed)
        self.assertIn("NO FILE-WRITE AUTHORITY", res.reason)

    def test_authority_files_are_permanently_immutable(self):
        """Invariant 5: Workflow authority rules and governing docs cannot be modified."""
        plan_file = self.plans_dir / "M22.4_PLAN.md"
        plan_file.write_text("# Milestone M22.4\n## 3. Scope\n`scripts/dev_workflow/state_machine.py`\n", encoding="utf-8")
        rec = self.engine.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "abc1234")
        rec.current_state = WorkflowState.ACCEPTED
        self.engine.state_mgr.save(rec)

        for prot_file in ("scripts/dev_workflow/state_machine.py", "ORCHESTRATION.md", "AGENTS.md"):
            res = self.engine.authorize_file_write(
                milestone_id="M22.4",
                actor=WorkflowActor.ANTIGRAVITY,
                target_path=prot_file,
                is_workflow_milestone=False,
            )
            self.assertFalse(res.allowed)
            self.assertIn("protected authority", res.reason)

    def test_tampered_plan_hash_blocks_verification(self):
        """Invariant 10: Plan tampering after acceptance invalidates integrity and blocks verification."""
        plan_file = self.plans_dir / "M22.4_PLAN.md"
        plan_file.write_text("# Milestone M22.4\n## Scope\nOriginal plan content.\n", encoding="utf-8")

        self.engine.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "abc1234")
        self.engine.user_accept_plan("M22.4", notes="Plan accepted.")

        rec = self.engine.get_record("M22.4")
        self.assertTrue(len(rec.plan_ref.plan_hash) == 64)
        rec.current_state = WorkflowState.VERIFYING
        self.engine.state_mgr.save(rec)

        # Tamper with plan file
        plan_file.write_text("# Milestone M22.4\n## Scope\nUNAUTHORIZED TAMPERED SCOPE.\n", encoding="utf-8")

        verifier = ClaudeBridgeVerifier()
        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            verifier.verify_milestone(
                engine=self.engine,
                milestone_id="M22.4",
                simulate_response="DECISION: VERIFIED\nBASIS: ok\nREMAINING_GAPS: None",
            )
        self.assertIn("Plan integrity check failed", str(ctx.exception))

    def test_bridge_prompt_contains_mandatory_devtest_markers(self):
        """Dev test prompts must explicitly declare all 5 non-negotiable test markers."""
        test_id = "DEVTEST_BRIDGE_PROMPT"
        rec = self.engine.state_mgr.create_devtest_state(test_id)
        rec.current_state = WorkflowState.VERIFYING

        verifier = ClaudeBridgeVerifier()
        prompt = verifier.format_verification_prompt(rec, state_content="Test evidence.")

        # Must contain all 5 markers
        for marker in DEVTEST_MANDATORY_MARKERS:
            self.assertIn(marker, prompt)

        # Must not contain release directives
        self.assertNotIn("perform the release commit", prompt.lower())
        self.assertNotIn("commit and push", prompt.lower())

    def test_legitimate_m22_4_claude_verification_path(self):
        """Legitimate canonical milestone verification succeeds with read-only review."""
        plan_file = self.plans_dir / "M22.4_PLAN.md"
        plan_file.write_text("# Milestone M22.4\n## 3. Scope\n`uri_core/core/test.py`\n", encoding="utf-8")

        self.engine.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "abc1234")
        self.engine.user_accept_plan("M22.4", notes="Plan accepted by User.")

        rec = self.engine.get_record("M22.4")
        rec.current_state = WorkflowState.VERIFYING
        self.engine.state_mgr.save(rec)

        verifier = ClaudeBridgeVerifier()
        prompt = verifier.format_verification_prompt(rec, state_content="Audit evidence all clear.")

        # Legitimate prompt must have read-only header and no release directives
        self.assertIn(MANDATORY_READ_ONLY_HEADER, prompt)
        self.assertNotIn("perform the release commit", prompt.lower())

        # Simulate honest verification from Claude
        simulated_claude_resp = (
            "DECISION: VERIFIED\n"
            "BASIS: Independent review confirmed all acceptance criteria and test evidence pass.\n"
            "REMAINING_GAPS: None."
        )
        res = verifier.verify_milestone(
            engine=self.engine,
            milestone_id="M22.4",
            simulate_response=simulated_claude_resp,
        )

        self.assertTrue(res.ok)
        self.assertEqual(res.decision, "VERIFIED")
        self.assertEqual(res.state, WorkflowState.VERIFIED)
        self.assertTrue(res.ready_for_release)
        self.assertEqual(res.release_authority, "Claude")


class TestWorkflowAuthorityAndPermissionProof(unittest.TestCase):
    """Proves the 10 core execution authorization invariants required by the user:
    1. Authorized in-scope writes proceed without interactive approval.
    2. Out-of-scope file writes are rejected.
    3. Protected files remain protected.
    4. DEVTEST cannot write production authority state.
    5. No M99 artifacts can be created or reintroduced.
    6. Commit/push remain unavailable to automated agents.
    7. Claude Bridge remains strictly read-only.
    8. State transitions remain deterministic.
    9. Remediation writes are bounded by Claude's remediation scope.
    10. Regression test: IDE permission path matching requires recursive glob pattern (**).
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_root = Path(self.temp_dir.name)
        self.plans_dir = self.test_root / "docs" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.engine = WorkflowEngine(plans_dir=self.plans_dir, repo_root=self.test_root)

        # Create canonical accepted plan
        self.plan_file = self.plans_dir / "M22.4_PLAN.md"
        self.plan_file.write_text(
            "# Milestone M22.4 Plan\n\n"
            "## 3. Scope\n"
            "- `uri_core/core/capability_resolver.py`\n"
            "- `uri_core/core/orchestrator.py`\n\n"
            "## 4. Out-of-Scope / Protected Files\n"
            "- `AGENTS.md`\n"
            "- `uri_core/core/dispatcher.py`\n\n"
            "## UI IMPACT\nREQUIRED\n",
            encoding="utf-8",
        )
        self.engine.state_mgr.create_initial_state("M22.4", "M22.4_PLAN.md", "8acbad5", ui_impact="REQUIRED")
        self.engine.user_accept_plan("M22.4", notes="Plan accepted.")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_1_authorized_in_scope_writes_allowed(self):
        """1. Authorized in-scope file writes work automatically."""
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Impl.")
        res = self.engine.authorize_file_write(
            milestone_id="M22.4",
            actor=WorkflowActor.GEMMA,
            target_path="uri_core/core/capability_resolver.py",
        )
        self.assertTrue(res.allowed)
        self.assertIn("authorized to write", res.reason)

    def test_2_out_of_scope_writes_rejected(self):
        """2. Out-of-scope file writes are rejected."""
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Impl.")
        res = self.engine.authorize_file_write(
            milestone_id="M22.4",
            actor=WorkflowActor.GEMMA,
            target_path="uri_core/unrelated/arbitrary_file.py",
        )
        self.assertFalse(res.allowed)
        self.assertIn("outside accepted milestone scope", res.reason)

    def test_3_protected_files_remain_protected(self):
        """3. Protected files remain protected."""
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Impl.")
        for protected in ("AGENTS.md", "ORCHESTRATION.md", "scripts/dev_workflow/state_machine.py"):
            res = self.engine.authorize_file_write(
                milestone_id="M22.4",
                actor=WorkflowActor.ANTIGRAVITY,
                target_path=protected,
            )
            self.assertFalse(res.allowed)
            self.assertIn("protected authority", res.reason.lower())

    def test_4_devtest_cannot_write_production_authority_state(self):
        """4. DEVTEST cannot write production authority state."""
        self.engine.state_mgr.create_devtest_state("DEVTEST_PROD_WRITE")
        res = self.engine.authorize_file_write(
            milestone_id="DEVTEST_PROD_WRITE",
            actor=WorkflowActor.ANTIGRAVITY,
            target_path="docs/plans/M22.4_STATE.md",
        )
        self.assertFalse(res.allowed)
        self.assertIn("NO FILE-WRITE AUTHORITY", res.reason)

    def test_5_no_m99_artifacts_can_be_created(self):
        """5. No M99 artifacts can be created/reintroduced."""
        m99_plan = self.plans_dir / "M99_PLAN.md"
        m99_plan.write_text("# Synthetic M99\n## Scope\n`test.py`\n", encoding="utf-8")
        rec_m99 = self.engine.state_mgr.create_initial_state("M99", "M99_PLAN.md", "fake_hash")

        # Saving a fabricated M99 production milestone state is strictly rejected
        with self.assertRaises(SecurityInvariantViolationError) as ctx:
            self.engine.state_mgr.save(rec_m99)
        self.assertIn("DEVTEST artifact 'M99' contains fabricated history", str(ctx.exception))

    def test_6_commit_push_remain_unavailable_to_automated_workflow(self):
        """6. Commit/push remain unavailable to automated workflow (Antigravity & Gemma)."""
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Impl.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Verify.")
        self.engine.state_mgr.save(rec)
        self.engine.record_claude_verification("M22.4", decision="VERIFIED", basis="Approved.")

        with self.assertRaises(InvariantViolationError) as ctx:
            self.engine.release_milestone("M22.4", commit_hash="c0ffee", actor=WorkflowActor.ANTIGRAVITY)
        self.assertIn("Claude is the sole release authority", str(ctx.exception))

    def test_7_claude_bridge_remains_read_only(self):
        """7. Claude Bridge remains strictly read-only and free of commit/push directives."""
        rec = self.engine.get_record("M22.4")
        rec.current_state = WorkflowState.VERIFYING
        verifier = ClaudeBridgeVerifier()
        prompt = verifier.format_verification_prompt(rec, state_content="Evidence content")
        self.assertIn(MANDATORY_READ_ONLY_HEADER, prompt)
        self.assertNotIn("git commit", prompt.lower())
        self.assertNotIn("git push", prompt.lower())

    def test_8_state_transitions_remain_deterministic(self):
        """8. State transitions remain deterministic and rule-governed."""
        from scripts.dev_workflow.state_machine import InvalidTransitionError
        # Skipping states directly from DRAFT to VERIFIED is forbidden
        with self.assertRaises((InvalidTransitionError, InvariantViolationError)):
            validate_transition(WorkflowState.DRAFT, WorkflowState.VERIFIED, WorkflowActor.CLAUDE)

    def test_9_remediation_writes_bounded_by_claude_scope(self):
        """9. Remediation writes are bounded strictly by Claude's remediation scope."""
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.IMPLEMENTING, WorkflowActor.ANTIGRAVITY, "Impl.")
        rec.transition(WorkflowState.AUDITING, WorkflowActor.ANTIGRAVITY, "Audit.")
        rec.transition(WorkflowState.VERIFYING, WorkflowActor.ANTIGRAVITY, "Verify.")
        self.engine.state_mgr.save(rec)

        # Claude returns NOT VERIFIED specifying remediation file
        self.engine.record_claude_verification(
            milestone_id="M22.4",
            decision="NOT VERIFIED",
            basis="Wire `uri_core/core/workflow_capability_router.py` call site.",
            remaining_gaps="Call site in `uri_core/core/workflow_capability_router.py` must pass principal.",
        )
        rec = self.engine.get_record("M22.4")
        rec.transition(WorkflowState.FIXING, WorkflowActor.ANTIGRAVITY, "Fixing.")
        self.engine.state_mgr.save(rec)

        # In-remediation file is authorized
        res_remed = self.engine.authorize_file_write(
            milestone_id="M22.4",
            actor=WorkflowActor.ANTIGRAVITY,
            target_path="uri_core/core/workflow_capability_router.py",
        )
        self.assertTrue(res_remed.allowed)
        self.assertIn("Claude remediation scope", res_remed.reason)

        # Unrelated file outside scope is rejected
        res_unrelated = self.engine.authorize_file_write(
            milestone_id="M22.4",
            actor=WorkflowActor.ANTIGRAVITY,
            target_path="uri_core/core/unrelated.py",
        )
        self.assertFalse(res_unrelated.allowed)
        self.assertIn("cannot silently expand milestone scope", res_unrelated.reason)

    def test_10_regression_ide_permission_recursive_glob_matching(self):
        """10. Regression test: Demonstrates the exact failure mechanism where
        an exact directory grant fails to match child files, requiring recursive glob (**).
        """
        import re

        def match_grant(pattern: str, target: str) -> bool:
            # Emulates glob/doublestar pattern translation to regex
            # Exact path (without **) only matches the exact path
            regex_str = "^" + re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/\\\\]*") + "$"
            return bool(re.match(regex_str, target))

        workspace = "write_file(C:\\Users\\cheta\\Development\\uri-agent)"
        child_file = "write_file(C:\\Users\\cheta\\Development\\uri-agent\\uri_core\\core\\capability_resolver.py)"
        external_file = "write_file(C:\\Users\\cheta\\.ssh\\id_rsa)"

        # The prior faulty grant: exact workspace directory without recursive glob
        faulty_grant = "write_file(C:\\Users\\cheta\\Development\\uri-agent)"
        # The corrected grant: recursive glob
        corrected_grant = "write_file(C:\\Users\\cheta\\Development\\uri-agent\\**)"

        # The faulty exact-path grant fails to authorize child file writes
        self.assertFalse(match_grant(faulty_grant, child_file))

        # The corrected recursive glob successfully authorizes child file writes in the workspace
        self.assertTrue(match_grant(corrected_grant, child_file))

        # Security boundary preserved: external files outside workspace remain unauthorized
        self.assertFalse(match_grant(corrected_grant, external_file))


if __name__ == "__main__":
    unittest.main()

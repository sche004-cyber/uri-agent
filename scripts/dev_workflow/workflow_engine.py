"""Workflow Engine (AO-4).

Coordinates the multi-agent canonical loop:
Claude (Plan) -> User (Accept/Modify) -> Gemma 4 12B (Implement) ->
Antigravity (Audit/Fix) -> Claude (Independent Verification) -> Antigravity (Release).

Boundary Guarantee: Development-only orchestration. Not part of URI runtime.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from scripts.dev_workflow.auditor import AntigravityAuditor, AuditFindings
from scripts.dev_workflow.gemma_driver import GemmaDriver
from scripts.dev_workflow.security_boundary import (
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
    AntigravityAuditReport,
    ClaudeVerificationDecision,
    GemmaReturnReport,
    MilestoneStateRecord,
    StateFileManager,
)


from scripts.dev_workflow.file_authority import (
    FileWriteAuthorizer,
    FileWriteOperation,
    WriteAuthorizationResult,
)


class WorkflowEngine:
    """Deterministic orchestrator for the AO-4 development lifecycle."""

    def __init__(
        self,
        plans_dir: Optional[Path] = None,
        repo_root: Optional[Path] = None,
        ollama_host: Optional[str] = None,
    ):
        self.state_mgr = StateFileManager(plans_dir=plans_dir)
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.security = SecurityBoundaryEnforcer(repo_root=self.repo_root)
        self.auditor = AntigravityAuditor(repo_root=self.repo_root)
        self.gemma = GemmaDriver(ollama_host=ollama_host) if ollama_host else GemmaDriver()
        self.file_authorizer = FileWriteAuthorizer(repo_root=self.repo_root)

    def authorize_file_write(
        self,
        milestone_id: str,
        actor: WorkflowActor,
        target_path: str | Path,
        operation: FileWriteOperation = FileWriteOperation.MODIFY,
        is_workflow_milestone: bool = False,
    ) -> WriteAuthorizationResult:
        """Evaluate file-write authority for an actor against the active milestone."""
        rec = self.get_record(milestone_id)
        return self.file_authorizer.authorize_write(
            record=rec,
            actor=actor,
            target_path=target_path,
            operation=operation,
            is_workflow_milestone=is_workflow_milestone,
        )

    def safe_write_file(
        self,
        milestone_id: str,
        actor: WorkflowActor,
        target_path: str | Path,
        content: str,
        operation: FileWriteOperation = FileWriteOperation.MODIFY,
        is_workflow_milestone: bool = False,
    ) -> Path:
        """Safely write content to target_path after validating role and scope authority."""
        rec = self.get_record(milestone_id)
        return self.file_authorizer.safe_write(
            record=rec,
            actor=actor,
            target_path=target_path,
            content=content,
            operation=operation,
            is_workflow_milestone=is_workflow_milestone,
        )

    def get_record(self, milestone_id: str) -> MilestoneStateRecord:
        return self.state_mgr.load(milestone_id)

    def user_accept_plan(
        self,
        milestone_id: str,
        notes: str = "Plan accepted by User.",
        user_token: Optional[str] = None,
        interactive_confirmed: bool = True,
    ) -> MilestoneStateRecord:
        """Execute User acceptance gate. Milestone must be DRAFT or AWAITING_USER_APPROVAL."""
        self.security.validate_user_acceptance(
            milestone_id=milestone_id,
            actor=WorkflowActor.USER,
            user_token=user_token,
            interactive_confirmed=interactive_confirmed,
        )
        rec = self.get_record(milestone_id)

        # Compute and record plan SHA-256 hash at acceptance time
        plan_path = self.state_mgr.get_plan_path(milestone_id)
        if plan_path and plan_path.exists():
            plan_hash = self.security.compute_plan_hash(plan_path)
            rec.plan_ref.plan_hash = plan_hash

        rec.transition(
            target_state=WorkflowState.ACCEPTED,
            actor=WorkflowActor.USER,
            note=notes,
        )
        self.state_mgr.save(rec)
        return rec

    def user_modify_plan(self, milestone_id: str, notes: str) -> MilestoneStateRecord:
        """Record User plan modification request."""
        rec = self.get_record(milestone_id)
        rec.transition(
            target_state=WorkflowState.DRAFT,
            actor=WorkflowActor.USER,
            note=f"User requested modifications: {notes}",
        )
        self.state_mgr.save(rec)
        return rec

    def start_implementation(
        self,
        milestone_id: str,
        user_authorized_fallback: bool = False,
        dry_run_response: Optional[str] = None,
        auto_audit: bool = True,
        test_commands: Optional[List[str]] = None,
        test_files: Optional[List[str]] = None,
        auto_verify: bool = False,
    ) -> MilestoneStateRecord:
        """Trigger Gemma 4 12B implementation under the accepted Task Brief."""
        rec = self.get_record(milestone_id)

        # Invariants: Canonical milestone & DEVTEST restriction
        if is_devtest_identifier(milestone_id):
            raise SecurityInvariantViolationError(
                f"Security Invariant Violation: DEVTEST '{milestone_id}' cannot enter implementation. "
                "Development tooling test fixtures are not URI milestones."
            )
        self.security.validate_canonical_milestone_id(milestone_id)

        # Invariant: Approval Gate
        if rec.current_state not in (WorkflowState.ACCEPTED, WorkflowState.READY_TO_RESUME, WorkflowState.WORKER_FAILED):
            raise InvariantViolationError(
                f"Approval Gate Invariant: Cannot begin implementation from state '{rec.current_state.value}'. "
                "Plan must be explicitly ACCEPTED by User first."
            )

        # Transition to IMPLEMENTING (Actor: Antigravity as mechanical driver)
        rec.transition(
            target_state=WorkflowState.IMPLEMENTING,
            actor=WorkflowActor.ANTIGRAVITY,
            note="Antigravity invoked Gemma 4 12B with qualified configuration.",
            user_authorized_fallback=user_authorized_fallback,
        )
        self.state_mgr.save(rec)

        # Locate plan file and verify integrity
        plan_path = self.state_mgr.get_plan_path(milestone_id)
        if not plan_path or not plan_path.exists():
            rec.transition(
                target_state=WorkflowState.BLOCKED,
                actor=WorkflowActor.ANTIGRAVITY,
                note=f"Plan file for milestone {milestone_id} not found.",
            )
            self.state_mgr.save(rec)
            return rec

        if rec.plan_ref.plan_hash:
            self.security.verify_plan_integrity(
                milestone_id=milestone_id,
                plan_path=plan_path,
                expected_hash=rec.plan_ref.plan_hash,
            )

        # Extract Task Brief & format prompt
        brief = self.gemma.extract_task_brief(plan_path, milestone_id)
        prompt = self.gemma.build_prompt(brief)

        # Query Gemma (or simulate if dry_run provided)
        try:
            if dry_run_response:
                response = dry_run_response
            else:
                response = self.gemma.query_ollama(
                    prompt=prompt,
                    worker_actor=WorkflowActor.GEMMA,
                    user_authorized_fallback=user_authorized_fallback,
                )

            # Apply any code files Gemma produced through FileWriteAuthorizer
            code_files = self.gemma.extract_code_blocks(response)
            written_files = []
            for file_path, code_content in code_files:
                try:
                    self.safe_write_file(
                        milestone_id=milestone_id,
                        actor=WorkflowActor.GEMMA,
                        target_path=file_path,
                        content=code_content,
                    )
                    written_files.append(file_path)
                except Exception as write_err:
                    print(f"Gemma file-write rejected for {file_path}: {write_err}")

            # Parse Return Report
            report = self.gemma.parse_return_report(response, milestone_id)
            if written_files and report.files_modified_created in ("None reported.", "None."):
                report.files_modified_created = ", ".join(written_files)

            rec.gemma_report = report
            self.state_mgr.save(rec)
        except Exception as e:
            # Handle worker failure gracefully without breaking continuity
            rec.transition(
                target_state=WorkflowState.WORKER_FAILED,
                actor=WorkflowActor.ANTIGRAVITY,
                note=f"Gemma invocation failed: {e}",
            )
            self.state_mgr.save(rec)
            return rec

        # Automatic progression: IMPLEMENTING -> AUDITING
        if auto_audit:
            return self.perform_audit(
                milestone_id=milestone_id,
                test_commands=test_commands,
                test_files=test_files,
                auto_verify=auto_verify,
            )

        return rec

    def perform_audit(
        self,
        milestone_id: str,
        test_commands: Optional[List[str]] = None,
        test_files: Optional[List[str]] = None,
        auto_verify: bool = False,
    ) -> MilestoneStateRecord:
        """Run Antigravity independent audit against active implementation."""
        rec = self.get_record(milestone_id)

        # Transition to AUDITING
        if rec.current_state != WorkflowState.AUDITING:
            rec.transition(
                target_state=WorkflowState.AUDITING,
                actor=WorkflowActor.ANTIGRAVITY,
                note="Antigravity started independent implementation and test audit.",
            )
            self.state_mgr.save(rec)

        findings = self.auditor.perform_audit(
            milestone_id=milestone_id,
            plan_ref=rec.plan_ref,
            test_commands=test_commands,
            test_files=test_files,
            gemma_report=rec.gemma_report,
            plans_dir=self.state_mgr.plans_dir,
        )

        audit_report = self.auditor.format_audit_report(findings)
        rec.audit_report = audit_report

        if findings.is_audit_passed:
            rec.transition(
                target_state=WorkflowState.VERIFYING,
                actor=WorkflowActor.ANTIGRAVITY,
                note="Audit passed. Ready for Claude independent verification review.",
            )
            self.state_mgr.save(rec)
            if auto_verify:
                self.verify_with_claude_bridge(milestone_id)
                rec = self.get_record(milestone_id)
        else:
            rec.transition(
                target_state=WorkflowState.FIXING,
                actor=WorkflowActor.ANTIGRAVITY,
                note=f"Audit identified gaps: {findings.outstanding_gaps}",
            )
            self.state_mgr.save(rec)

        return rec

    def verify_with_claude_bridge(
        self,
        milestone_id: str,
        timeout_sec: int = 120,
        wait_if_busy: bool = True,
        simulate_response: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        verifier: Any = None,
    ) -> Any:
        """Execute Claude Bridge verification handoff for a milestone in VERIFYING state."""
        if verifier is None:
            from scripts.dev_workflow.claude_verifier import ClaudeBridgeVerifier
            verifier = ClaudeBridgeVerifier()
        return verifier.verify_milestone(
            engine=self,
            milestone_id=milestone_id,
            timeout_sec=timeout_sec,
            wait_if_busy=wait_if_busy,
            simulate_response=simulate_response,
            custom_instructions=custom_instructions,
        )

    def record_claude_verification(
        self,
        milestone_id: str,
        decision: str,  # VERIFIED | NOT VERIFIED
        basis: str,
        remaining_gaps: str = "",
    ) -> MilestoneStateRecord:
        """Record Claude's independent verification decision."""
        rec = self.get_record(milestone_id)
        decision_clean = decision.upper().strip()

        if decision_clean == "VERIFIED":
            rec.verification = ClaudeVerificationDecision(
                decision="VERIFIED",
                basis=basis,
                remaining_gaps=remaining_gaps or "None.",
            )
            rec.transition(
                target_state=WorkflowState.VERIFIED,
                actor=WorkflowActor.CLAUDE,
                note=f"Claude verified milestone: {basis}",
            )
        elif decision_clean == "NOT VERIFIED":
            rec.verification = ClaudeVerificationDecision(
                decision="NOT VERIFIED",
                basis=basis,
                remaining_gaps=remaining_gaps or "Unmet criteria.",
            )
            rec.transition(
                target_state=WorkflowState.NOT_VERIFIED,
                actor=WorkflowActor.CLAUDE,
                note=f"Claude rejected verification: {basis}",
            )
        else:
            raise ValueError(f"Invalid verification decision: '{decision}'. Must be 'VERIFIED' or 'NOT VERIFIED'.")

        self.state_mgr.save(rec)
        return rec

    def release_milestone(
        self,
        milestone_id: str,
        commit_hash: str,
        actor: WorkflowActor = WorkflowActor.CLAUDE,
    ) -> MilestoneStateRecord:
        """Mark milestone COMPLETE after verified release."""
        rec = self.get_record(milestone_id)

        # Invariant: DEVTEST cannot authorize commit/push or be released
        if is_devtest_identifier(milestone_id):
            raise SecurityInvariantViolationError(
                f"Security Invariant Violation: DEVTEST '{milestone_id}' has NO RELEASE AUTHORITY. "
                "Development tooling tests can NEVER authorize commit/push or be marked COMPLETE."
            )

        # Invariant: Release Gate
        if rec.current_state != WorkflowState.VERIFIED:
            raise InvariantViolationError(
                f"Release Gate Invariant: Cannot release from state '{rec.current_state.value}'. "
                "Claude must declare VERIFIED first."
            )

        rec.release_commit = commit_hash
        rec.release_pushed = "true"
        rec.transition(
            target_state=WorkflowState.COMPLETE,
            actor=actor,
            note=f"Milestone released at commit {commit_hash}.",
        )
        self.state_mgr.save(rec)
        return rec

    def resume_from_interruption(
        self,
        milestone_id: str,
        actor: WorkflowActor,
        target_state: WorkflowState,
        note: str = "Resumed from interruption.",
    ) -> MilestoneStateRecord:
        """Resume cycle from waiting/failed state."""
        rec = self.get_record(milestone_id)
        rec.transition(
            target_state=target_state,
            actor=actor,
            note=note,
        )
        self.state_mgr.save(rec)
        return rec

"""File-Write Authority Subsystem for URI Development Automation (AO-4).

Governs file-write permissions for implementation and review actors per:
- AGENTS.md
- ORCHESTRATION.md §1.2, §5, §10.1, §10.2, §10.3

Role Authority Rules:
- GEMMA / CODEX (Implementer role - 2026-09-11 governance revision made
  Codex a standing routed implementer, not a reserve/fallback actor;
  both operate under the identical authority shape below):
  - May CREATE/MODIFY files within accepted milestone scope.
  - May create/update required tests.
  - May modify required UI files ONLY when UI IMPACT: REQUIRED.
  - May NOT modify protected files unless explicitly included in accepted plan exceptions.
  - May NOT commit or push.
  - May NOT alter workflow authority rules.
- ANTIGRAVITY:
  - May CREATE/MODIFY files needed to implement or fix the accepted milestone.
  - May create/update tests and required UI files.
  - May fix defects discovered during its audit.
  - May modify development-workflow tooling when the workflow itself is the accepted task.
  - May NOT silently expand milestone scope.
  - May NOT alter Claude's verification/release authority.
  - May NOT commit or push.
- CLAUDE:
  - May CREATE/MODIFY plans, state files, result reports, and milestone documentation.
  - Sole automated commit/push authority after VERIFIED.
- QWEN:
  - No normal write authority (explicit user-authorized fallback only, reserve role).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from scripts.dev_workflow.security_boundary import (
    CANONICAL_MILESTONE_PATTERN,
    PROTECTED_AUTHORITY_FILES as SB_PROTECTED_FILES,
    SecurityBoundaryEnforcer,
    SecurityInvariantViolationError,
    is_devtest_identifier,
)
from scripts.dev_workflow.state_machine import (
    AuthorityViolationError,
    InvariantViolationError,
    WorkflowActor,
    WorkflowState,
)
from scripts.dev_workflow.state_manager import MilestoneStateRecord


class FileWriteOperation(Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"


@dataclass
class WriteAuthorizationResult:
    allowed: bool
    reason: str
    actor: WorkflowActor
    target_path: str
    operation: FileWriteOperation


# Non-negotiable Protected Authority Boundaries
PROTECTED_AUTHORITY_FILES = SB_PROTECTED_FILES

# Core Protected Runtime Architecture Files
PROTECTED_RUNTIME_FILES = {
    "uri_core/core/dispatcher.py",
    "uri_core/core/principal_context.py",
    "uri_core/core/approval_gate.py",  # Narrow named exception only when in plan
}


class FileWriteAuthorizer:
    """Authorizes and validates all file-write operations based on milestone state,

    explicit scope, actor role, and protected boundaries.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.security = SecurityBoundaryEnforcer(repo_root=self.repo_root)
        self.rejected_attempts: List[Dict[str, Any]] = []
        self.authorized_writes: List[Dict[str, Any]] = []

    def normalize_relpath(self, target_path: str | Path) -> str:
        """Convert a path to relative POSIX-style path from repo root."""
        p = Path(target_path)
        if p.is_absolute():
            try:
                rel = p.relative_to(self.repo_root)
            except ValueError:
                rel = p
        else:
            rel = p
        return str(rel).replace("\\", "/")

    def extract_plan_scope(self, plan_text: str) -> Dict[str, Any]:
        """Extract declared in-scope paths, protected exceptions, and UI impact."""
        in_scope: Set[str] = set()
        exceptions: Set[str] = set()

        # Find backtick-quoted filenames in scope section
        scope_match = re.search(r"##\s*3\.\s*Scope\s*\n(.*?)(?=\n##|\Z)", plan_text, re.DOTALL | re.IGNORECASE)
        if scope_match:
            scope_block = scope_match.group(1)
            # Find explicit paths like uri_core/..., tests/..., etc.
            found = re.findall(r"`([a-zA-Z0-9_\-./]+(?:\.[a-zA-Z0-9]+)?)`", scope_block)
            for f in found:
                if "/" in f or f.endswith((".py", ".dart", ".json", ".md", ".sh", ".yaml")):
                    in_scope.add(f.replace("\\", "/"))

        # Find named exceptions in Out-of-Scope / Protected Files section
        prot_match = re.search(r"##\s*4\.\s*Out-of-Scope\s*/\s*Protected Files\s*\n(.*?)(?=\n##|\Z)", plan_text, re.DOTALL | re.IGNORECASE)
        if prot_match:
            prot_block = prot_match.group(1)
            # Look for bullet items mentioning named exception (may span multiple lines)
            bullet_items = re.split(r"\n\s*[-*]\s*", "\n" + prot_block)
            for item in bullet_items:
                if "exception" in item.lower():
                    found_ex = re.findall(r"`([a-zA-Z0-9_\-./]+(?:\.[a-zA-Z0-9]+)?)`", item)
                    for fe in found_ex:
                        if "/" in fe or fe.endswith((".py", ".dart", ".json", ".md")):
                            exceptions.add(fe.replace("\\", "/"))

        ui_required = "UI IMPACT: REQUIRED" in plan_text.upper() or "UI IMPACT\nREQUIRED" in plan_text.upper()

        return {
            "in_scope_paths": in_scope,
            "protected_exceptions": exceptions,
            "ui_required": ui_required,
        }

    def extract_remediation_scope(self, verification_decision: Any) -> Set[str]:
        """Extract paths explicitly cited in Claude's verification rejection / remediation plan."""
        remediation_paths: Set[str] = set()
        if not verification_decision:
            return remediation_paths
        text = f"{getattr(verification_decision, 'basis', '')}\n{getattr(verification_decision, 'remaining_gaps', '')}"
        found = re.findall(r"`([a-zA-Z0-9_\-./]+(?:\.[a-zA-Z0-9]+)?)`", text)
        for f in found:
            clean = f.replace("\\", "/").strip()
            if "/" in clean or clean.endswith((".py", ".dart", ".json", ".md", ".yaml")):
                remediation_paths.add(clean)
        return remediation_paths

    def authorize_write(
        self,
        record: MilestoneStateRecord,
        actor: WorkflowActor,
        target_path: str | Path,
        operation: FileWriteOperation = FileWriteOperation.MODIFY,
        plan_text: Optional[str] = None,
        is_workflow_milestone: bool = False,
    ) -> WriteAuthorizationResult:
        """Evaluate write permission derived strictly from milestone state,

        explicit scope, protected-file rules, actor role, and operation.
        """
        rel_path = self.normalize_relpath(target_path)

        def reject(reason: str) -> WriteAuthorizationResult:
            res = WriteAuthorizationResult(
                allowed=False,
                reason=reason,
                actor=actor,
                target_path=rel_path,
                operation=operation,
            )
            self.rejected_attempts.append({
                "milestone_id": record.milestone_id,
                "actor": actor.value,
                "target_path": rel_path,
                "operation": operation.value,
                "reason": reason,
                "state": record.current_state.value,
            })
            return res

        # 0a. DEVTEST Invariant: DEVTEST cannot authorize writes to repository
        if is_devtest_identifier(record.milestone_id):
            return reject(
                f"Security Invariant Violation: DEVTEST '{record.milestone_id}' has NO FILE-WRITE AUTHORITY "
                "in the repository. Development tooling tests cannot modify repository files."
            )

        # 0b. Canonical Milestone Invariant (Invariant 4)
        if not CANONICAL_MILESTONE_PATTERN.match(record.milestone_id):
            return reject(
                f"Security Invariant Violation (Invariant 4): Milestone ID '{record.milestone_id}' "
                "is not a canonical roadmap milestone. Synthetic/test milestones cannot authorize file writes."
            )

        # 1. Milestone State Gate
        # Writes are strictly forbidden before User plan acceptance or during read-only review/release
        active_states = {
            WorkflowState.ACCEPTED,
            WorkflowState.IMPLEMENTING,
            WorkflowState.AUDITING,
            WorkflowState.FIXING,
            WorkflowState.READY_TO_RESUME,
        }
        if record.current_state not in active_states:
            return reject(
                f"Writes are blocked before user acceptance or in state '{record.current_state.value}'. "
                "Milestone must be in ACCEPTED, IMPLEMENTING, AUDITING, or FIXING state."
            )

        # 2. Actor Authorization Gate. As of the 2026-09-11 governance
        # revision, Codex is a standing routed implementer (Implementer/
        # Tester/Repair Engineer), not a reserve/fallback actor - it has
        # real, scoped write authority (see the GEMMA/CODEX branch
        # below), identical in shape to Gemma's. Qwen remains reserve-
        # only with zero normal-cycle write authority.
        if actor == WorkflowActor.QWEN:
            return reject(f"Actor '{actor.value}' has no file-write authority in the normal cycle (reserve only).")

        # 3. Protected Authority & Workflow Rule Invariant (Invariant 5)
        for prot_auth in PROTECTED_AUTHORITY_FILES:
            if rel_path == prot_auth or rel_path.endswith("/" + prot_auth) or rel_path.endswith(prot_auth):
                if actor in (WorkflowActor.GEMMA, WorkflowActor.CODEX):
                    return reject(f"Security Invariant Violation (Invariant 5): {actor.value} is strictly forbidden from altering workflow authority rules.")
                if actor == WorkflowActor.ANTIGRAVITY and not is_workflow_milestone:
                    return reject("Security Invariant Violation (Invariant 5): Antigravity cannot alter protected authority boundaries outside workflow milestones.")
                return reject(
                    f"Security Invariant Violation (Invariant 5): File '{rel_path}' is a protected authority file. "
                    "Workflow authority rules are permanently immutable to automated writes."
                )

        # 4. Operations Check
        if operation == FileWriteOperation.DELETE:
            return reject("File deletion operations are not authorized for automated workers.")

        # Load plan details and verify plan integrity (Invariant 10)
        plan_file = self.repo_root / "docs" / "plans" / record.plan_ref.plan_file
        if plan_text is None:
            if plan_file.exists():
                plan_text = plan_file.read_text(encoding="utf-8")
            else:
                plan_text = ""
                if record.plan_ref.plan_file:
                    return reject(f"Plan file '{record.plan_ref.plan_file}' does not exist on disk.")

        if record.plan_ref.plan_hash and plan_file.exists():
            current_hash = self.security.compute_plan_hash(plan_file)
            if current_hash != record.plan_ref.plan_hash:
                return reject(
                    f"Security Invariant Violation (Invariant 10): Plan integrity check failed for {record.milestone_id}. "
                    "Plan file has been tampered with or modified after acceptance."
                )

        plan_info = self.extract_plan_scope(plan_text)
        in_scope_paths = plan_info["in_scope_paths"]
        protected_exceptions = plan_info["protected_exceptions"]
        if record.plan_ref and record.plan_ref.ui_impact:
            ui_required = (record.plan_ref.ui_impact == "REQUIRED")
        else:
            ui_required = plan_info["ui_required"]

        # Helper path matchers
        is_test_path = rel_path.startswith("tests/") or rel_path.endswith(("_test.py", "_test.dart"))
        is_ui_path = rel_path.startswith("uri_ui/")
        is_plan_or_doc = rel_path.startswith("docs/plans/") or rel_path.endswith(("_PLAN.md", "_STATE.md"))

        # 5. Actor Specific Scope Enforcement
        if actor == WorkflowActor.CLAUDE:
            # Claude manages plans, state files, result reports, documentation
            if is_plan_or_doc or rel_path.endswith(".md"):
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason="Claude is authorized to create/modify plans, state files, and milestone documentation.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res
            else:
                return reject(f"Claude may not directly write application code file '{rel_path}'.")

        elif actor in (WorkflowActor.GEMMA, WorkflowActor.CODEX):
            # Gemma and Codex share the same Implementer authority shape:
            # bounded to the accepted plan's scope, tests, and UI-when-
            # required - neither has architectural or Git authority, and
            # this branch enforces that identically for both, per the
            # 2026-09-11 governance revision (Codex is now a standing
            # routed implementer for complex/security-sensitive work,
            # Gemma for bounded/small work - the authority boundary they
            # operate under is the same).
            for pr in PROTECTED_RUNTIME_FILES:
                if (rel_path == pr or rel_path.endswith(pr)) and not any(rel_path.endswith(ex) for ex in protected_exceptions):
                    return reject(f"{actor.value} cannot modify protected runtime file '{rel_path}' without an explicit plan exception.")

            # Tests
            if is_test_path:
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason=f"{actor.value} is authorized to create/update required tests.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            # UI files
            if is_ui_path:
                if not ui_required:
                    return reject(f"{actor.value} cannot modify UI file '{rel_path}' when UI IMPACT is not REQUIRED.")
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason=f"{actor.value} is authorized to modify UI files because UI IMPACT: REQUIRED.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            # In-scope application paths
            is_in_scope = False
            for isp in in_scope_paths:
                if rel_path == isp or rel_path.endswith(isp) or isp in rel_path:
                    is_in_scope = True
                    break

            if is_in_scope:
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason=f"{actor.value} is authorized to write '{rel_path}' within accepted milestone scope.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res
            else:
                return reject(f"Target file '{rel_path}' is outside accepted milestone scope.")

        elif actor == WorkflowActor.ANTIGRAVITY:
            # State files
            if rel_path.startswith("docs/plans/") and rel_path.endswith("_STATE.md"):
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason=f"Antigravity is authorized to update persistent milestone state record '{rel_path}'.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            # Tooling updates when workflow is the accepted task
            if is_workflow_milestone and (rel_path.startswith("scripts/dev_workflow/") or rel_path.startswith("tests/dev_workflow/")):
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason="Antigravity is authorized to modify development-workflow tooling for workflow tasks.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            # Bounded fixes for audit findings or tests
            if is_test_path:
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason="Antigravity is authorized to create/update tests for audit verification.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            if is_ui_path and ui_required:
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason="Antigravity is authorized to fix required UI components.",
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res

            # Remediation scope when in FIXING state after Claude NOT_VERIFIED
            remediation_paths = set()
            if record.current_state == WorkflowState.FIXING and record.verification:
                remediation_paths = self.extract_remediation_scope(record.verification)

            is_in_scope = False
            for isp in (in_scope_paths | remediation_paths):
                if rel_path == isp or rel_path.endswith(isp) or isp in rel_path or rel_path.endswith("/" + Path(isp).name):
                    is_in_scope = True
                    break

            if is_in_scope:
                reason = (
                    f"Antigravity is authorized to fix within Claude remediation scope: '{rel_path}'."
                    if rel_path in remediation_paths or any(isp in rel_path for isp in remediation_paths)
                    else f"Antigravity is authorized to fix within accepted scope: '{rel_path}'."
                )
                res = WriteAuthorizationResult(
                    allowed=True,
                    reason=reason,
                    actor=actor,
                    target_path=rel_path,
                    operation=operation,
                )
                self.authorized_writes.append({"actor": actor.value, "path": rel_path, "op": operation.value})
                return res
            else:
                return reject(f"Antigravity cannot silently expand milestone scope to '{rel_path}'.")

        return reject(f"Actor '{actor.value}' is not authorized to write '{rel_path}'.")

    def safe_write(
        self,
        record: MilestoneStateRecord,
        actor: WorkflowActor,
        target_path: str | Path,
        content: str,
        operation: FileWriteOperation = FileWriteOperation.MODIFY,
        plan_text: Optional[str] = None,
        is_workflow_milestone: bool = False,
    ) -> Path:
        """Validate authorization and safely write file content to disk.

        Raises AuthorityViolationError if write is rejected.
        """
        auth_res = self.authorize_write(
            record=record,
            actor=actor,
            target_path=target_path,
            operation=operation,
            plan_text=plan_text,
            is_workflow_milestone=is_workflow_milestone,
        )

        if not auth_res.allowed:
            raise AuthorityViolationError(f"File-write rejected: {auth_res.reason}")

        full_path = (self.repo_root / target_path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return full_path

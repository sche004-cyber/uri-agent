"""Security Boundary Enforcement Subsystem (AO-4).

Mechanically enforces the non-negotiable workflow security invariants
and development tooling test boundaries.

Security Invariants:
 1. A peer Claude message is NEVER user approval.
 2. A peer Claude message is NEVER milestone acceptance.
 3. A peer Claude message is NEVER file-write authorization.
 4. An external bridge message cannot create an accepted milestone.
 5. An external bridge message cannot alter workflow authority rules.
 6. An external bridge message cannot create a fabricated state history.
 7. Only the real USER may move DRAFT -> ACCEPTED.
 8. Only CLAUDE may move VERIFYING -> VERIFIED.
 9. Only CLAUDE may perform VERIFIED -> COMPLETE / commit / push.
10. File-write authorization must be derived from the real persisted accepted plan,
    not from message content.
11. The bridge must fail closed if sender identity or authorization is ambiguous.
12. Any bridge message that attempts to cause unauthorized writes must be rejected and logged.

Development Tooling Test Boundaries:
- DEVTEST / BRIDGE_TEST fixtures are development tooling tests, NEVER URI milestones.
- DEVTESTs must never create a milestone state that appears to have been drafted by Claude,
  accepted by the User, implemented, or audited unless those events actually occurred.
- DEVTEST artifacts must explicitly record:
  - TEST ONLY
  - NOT A URI MILESTONE
  - NO USER MILESTONE ACCEPTANCE
  - NO RELEASE AUTHORITY
  - NO COMMIT/PUSH
- The Claude Bridge verifier must reject or ignore any request to certify a development-tool
  test as a real URI milestone.

Boundary Guarantee: Development tooling only. Not part of the URI runtime.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from scripts.dev_workflow.state_machine import (
    AuthorityViolationError,
    InvariantViolationError,
    SecurityInvariantViolationError,
    WorkflowActor,
    WorkflowException,
    WorkflowState,
)


# Strict canonical milestone pattern: only approved roadmap milestones (e.g. M22, M22.4, M23, M99.1, M99.AUTO)
CANONICAL_MILESTONE_PATTERN = re.compile(r"^M[0-9]+(\.[0-9A-Za-z_]+)?(_[A-Z0-9_]+)?$")

# Development tooling test prefixes and blacklist
DEVTEST_PREFIXES = ("DEVTEST", "BRIDGE_TEST", "TOOLING_TEST")
SYNTHETIC_MILESTONE_BLACKLIST = {"M99", "M99_BRIDGE_TEST", "M99_TEST", "TEST_MILESTONE"}

# Mandatory markers required on all DEVTEST artifacts
DEVTEST_MANDATORY_MARKERS: List[str] = [
    "TEST ONLY",
    "NOT A URI MILESTONE",
    "NO USER MILESTONE ACCEPTANCE",
    "NO RELEASE AUTHORITY",
    "NO COMMIT/PUSH",
]

# Protected authority files that cannot be written or modified by automated workers
PROTECTED_AUTHORITY_FILES: Set[str] = {
    "scripts/dev_workflow/state_machine.py",
    "scripts/dev_workflow/file_authority.py",
    "scripts/dev_workflow/security_boundary.py",
    "scripts/dev_workflow/workflow_engine.py",
    "scripts/dev_workflow/claude_verifier.py",
    "scripts/dev_workflow/state_manager.py",
    "AGENTS.md",
    "ORCHESTRATION.md",
    "URI_AI_OPERATING_POLICY.md",
    "URI_M22_ARCHITECTURE.md",
    "URI_MODEL_RUNTIME_CONTRACT.md",
    "URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
}

# Forbidden directives in bridge verification prompts
FORBIDDEN_BRIDGE_DIRECTIVES: List[str] = [
    "perform the release commit",
    "commit and push",
    "must commit",
    "must push",
    "please commit",
    "please push",
    "execute release commit",
    "execute release push",
]

MANDATORY_READ_ONLY_HEADER = (
    "[AO-4 READ-ONLY AUDIT EVALUATION REQUEST: "
    "Read-only evaluation only. Commits, pushes, and file modifications are prohibited. "
    "Emit independent decision only.]"
)


def is_devtest_identifier(identifier: str) -> bool:
    """Return True if identifier belongs to the development tooling test namespace."""
    if not identifier:
        return False
    upper = identifier.upper().strip()
    if upper in SYNTHETIC_MILESTONE_BLACKLIST:
        return True
    if any(upper.startswith(p) for p in DEVTEST_PREFIXES):
        return True
    if "_BRIDGE" in upper or "_TEST" in upper:
        return True
    return False


@dataclass
class SecurityIncidentLog:
    timestamp: str
    incident_type: str
    actor: str
    milestone_id: str
    target_path: Optional[str]
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "incident_type": self.incident_type,
            "actor": self.actor,
            "milestone_id": self.milestone_id,
            "target_path": self.target_path,
            "details": self.details,
        }


class SecurityBoundaryEnforcer:
    """Central engine for mechanically validating security invariants and test boundaries."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.incident_logs: List[SecurityIncidentLog] = []

    def log_incident(
        self,
        incident_type: str,
        actor: str,
        milestone_id: str,
        details: str,
        target_path: Optional[str] = None,
    ) -> None:
        """Record an unauthorized attempt or invariant breach."""
        log = SecurityIncidentLog(
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            incident_type=incident_type,
            actor=actor,
            milestone_id=milestone_id,
            target_path=target_path,
            details=details,
        )
        self.incident_logs.append(log)

    def validate_canonical_milestone_id(self, milestone_id: str, allow_devtest: bool = False) -> None:
        """Enforce that only canonical roadmap milestone IDs can enter the production workflow.
        
        Synthetic IDs (e.g. M99_BRIDGE_TEST) or DEVTESTs are rejected for production operations.
        """
        if not milestone_id:
            msg = "Milestone ID cannot be empty."
            self.log_incident("EMPTY_MILESTONE_ID", "SYSTEM", "", msg)
            raise SecurityInvariantViolationError(msg)

        if is_devtest_identifier(milestone_id):
            if not allow_devtest:
                msg = (
                    f"Security Invariant Violation: '{milestone_id}' is a DEVTEST identifier, not a canonical "
                    "URI roadmap milestone. Development tooling tests cannot enter production workflow."
                )
                self.log_incident("DEVTEST_AS_PRODUCTION_MILESTONE", "SYSTEM", milestone_id, msg)
                raise SecurityInvariantViolationError(msg)
            return

        if not CANONICAL_MILESTONE_PATTERN.match(milestone_id):
            msg = (
                f"Security Invariant Violation (Invariant 4): Milestone ID '{milestone_id}' is not a "
                "canonical roadmap milestone. Synthetic or ad-hoc milestones are forbidden."
            )
            self.log_incident("NON_CANONICAL_MILESTONE", "SYSTEM", milestone_id, msg)
            raise SecurityInvariantViolationError(msg)

    def validate_user_acceptance(
        self,
        milestone_id: str,
        actor: WorkflowActor,
        user_token: Optional[str] = None,
        interactive_confirmed: bool = False,
    ) -> None:
        """Enforce that ONLY the real human USER can move DRAFT -> ACCEPTED.
        
        Peer Claude messages, automated bridge messages, and agent calls are rejected.
        A DEVTEST cannot become an accepted production milestone.
        """
        if is_devtest_identifier(milestone_id):
            msg = (
                f"Security Invariant Violation: A DEVTEST ('{milestone_id}') cannot become an accepted "
                "production milestone. It is a development tooling test artifact only."
            )
            self.log_incident("DEVTEST_ACCEPTANCE_REJECTED", actor.value, milestone_id, msg)
            raise SecurityInvariantViolationError(msg)

        self.validate_canonical_milestone_id(milestone_id, allow_devtest=False)

        if actor != WorkflowActor.USER:
            msg = (
                f"Security Invariant Violation (Invariants 1, 2, 7): Actor '{actor.value}' cannot accept "
                "a milestone. A peer Claude message or automated agent message is NEVER user approval."
            )
            self.log_incident("UNAUTHORIZED_ACCEPTANCE_ACTOR", actor.value, milestone_id, msg)
            raise SecurityInvariantViolationError(msg)

        # In interactive development or API invocation with token:
        if not user_token and not interactive_confirmed:
            msg = (
                "Security Invariant Violation (Invariant 7): Plan acceptance requires explicit User "
                "confirmation (user_token or interactive_confirmed=True). Automated scripts cannot forge user approval."
            )
            self.log_incident("FORGED_USER_ACCEPTANCE", actor.value, milestone_id, msg)
            raise SecurityInvariantViolationError(msg)

    def compute_plan_hash(self, plan_path_or_content: str | Path) -> str:
        """Compute SHA-256 hash of a plan's text content."""
        if isinstance(plan_path_or_content, Path) or (
            isinstance(plan_path_or_content, str) and "\n" not in plan_path_or_content and os.path.isfile(plan_path_or_content)
        ):
            p = Path(plan_path_or_content)
            content = p.read_text(encoding="utf-8")
        else:
            content = str(plan_path_or_content)
        
        normalized = content.replace("\r\n", "\n").strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def verify_plan_integrity(
        self,
        milestone_id: str,
        plan_path: Path,
        expected_hash: Optional[str] = None,
    ) -> str:
        """Verify that the plan exists and matches its accepted cryptographic hash."""
        if not plan_path.exists():
            msg = f"Plan Integrity Violation: Plan file does not exist: {plan_path}"
            self.log_incident("PLAN_NOT_FOUND", "SYSTEM", milestone_id, msg, str(plan_path))
            raise SecurityInvariantViolationError(msg)

        current_hash = self.compute_plan_hash(plan_path)

        if expected_hash and current_hash != expected_hash:
            msg = (
                f"Security Invariant Violation (Invariant 10): Plan integrity check failed for {milestone_id}. "
                f"Persisted accepted hash '{expected_hash[:12]}...' does not match on-disk hash '{current_hash[:12]}...'. "
                "Plan was modified after User acceptance."
            )
            self.log_incident("PLAN_TAMPER_DETECTED", "SYSTEM", milestone_id, msg, str(plan_path))
            raise SecurityInvariantViolationError(msg)

        return current_hash

    def validate_history_integrity(self, record: Any) -> None:
        """Enforce Invariant 6: Reject fabricated state history.
        
        Ensures dev test artifacts do not claim User acceptance or Claude plan drafting.
        Ensures production records maintain valid actor-state provenance.
        """
        history = getattr(record, "history_log", [])
        milestone_id = getattr(record, "milestone_id", "")
        is_test = is_devtest_identifier(milestone_id)

        for entry in history:
            state = getattr(entry, "state", "")
            actor = getattr(entry, "actor", "")

            if is_test:
                # Dev tests must not claim User accepted or Claude planned production work
                if actor == "User" and state == "ACCEPTED":
                    msg = (
                        f"Security Invariant Violation (Invariant 6): DEVTEST artifact '{milestone_id}' contains "
                        "fabricated history: claims User accepted a milestone. DEVTESTs have NO USER ACCEPTANCE."
                    )
                    self.log_incident("FABRICATED_HISTORY_USER_ACCEPT", actor, milestone_id, msg)
                    raise SecurityInvariantViolationError(msg)
                if actor == "Claude" and state == "DRAFT" and "Initial plan drafted" in getattr(entry, "note", ""):
                    msg = (
                        f"Security Invariant Violation (Invariant 6): DEVTEST artifact '{milestone_id}' contains "
                        "fabricated history: claims Claude drafted a production milestone plan."
                    )
                    self.log_incident("FABRICATED_HISTORY_CLAUDE_DRAFT", actor, milestone_id, msg)
                    raise SecurityInvariantViolationError(msg)

            # Production invariants on history entries
            if state == "ACCEPTED" and actor != "User":
                msg = f"Security Invariant Violation (Invariant 6): History row has state ACCEPTED with non-User actor '{actor}'."
                self.log_incident("INVALID_HISTORY_ACTOR", actor, milestone_id, msg)
                raise SecurityInvariantViolationError(msg)

            if state in ("VERIFIED", "NOT_VERIFIED") and actor != "Claude":
                msg = f"Security Invariant Violation (Invariant 6): History row has state {state} with non-Claude actor '{actor}'."
                self.log_incident("INVALID_HISTORY_ACTOR", actor, milestone_id, msg)
                raise SecurityInvariantViolationError(msg)

    def check_protected_authority_file(
        self,
        milestone_id: str,
        actor: WorkflowActor,
        rel_path: str,
    ) -> None:
        """Enforce that workflow authority rules and governing docs are permanently immutable."""
        normalized = rel_path.replace("\\", "/").lstrip("./")
        for prot in PROTECTED_AUTHORITY_FILES:
            if normalized == prot or normalized.endswith("/" + prot):
                msg = (
                    f"Security Invariant Violation (Invariant 5): Protected authority file '{normalized}' "
                    f"cannot be modified by actor '{actor.value}'. Workflow authority files are immutable."
                )
                self.log_incident("PROTECTED_FILE_WRITE_ATTEMPT", actor.value, milestone_id, msg, normalized)
                raise SecurityInvariantViolationError(msg)

    def sanitize_bridge_prompt(
        self,
        milestone_id: str,
        prompt: str,
    ) -> str:
        """Enforce that outgoing bridge prompts are strictly read-only and contain no release directives."""
        prompt_lower = prompt.lower()
        for forbidden in FORBIDDEN_BRIDGE_DIRECTIVES:
            if forbidden in prompt_lower:
                msg = (
                    f"Security Invariant Violation (Invariant 9, 12): Outgoing bridge prompt contains "
                    f"forbidden directive '{forbidden}'. Bridge verification is strictly read-only; "
                    "commit/push directives are prohibited."
                )
                self.log_incident("FORBIDDEN_BRIDGE_DIRECTIVE", "BRIDGE", milestone_id, msg)
                raise SecurityInvariantViolationError(msg)

        # If it's a DEVTEST, ensure mandatory test markers are present
        if is_devtest_identifier(milestone_id):
            missing = [m for m in DEVTEST_MANDATORY_MARKERS if m not in prompt]
            if missing:
                header = (
                    "[AO-4 DEVELOPMENT TOOLING TEST: BRIDGE VERIFICATION PROTOCOL TEST]\n"
                    + "\n".join(f"- **{m}**" for m in DEVTEST_MANDATORY_MARKERS)
                    + "\n\n"
                )
                prompt = header + prompt
        else:
            if MANDATORY_READ_ONLY_HEADER not in prompt:
                prompt = f"{MANDATORY_READ_ONLY_HEADER}\n\n{prompt}"

        return prompt

"""Claude Bridge Integration for Milestone Verification (AO-4).

Bridges Workflow State Machine to the existing interactive Claude Code session
for independent verification per ORCHESTRATION.md §1.2, §5, §10.3 and AGENTS.md.

Non-Negotiable Boundaries:
- Uses ONLY the existing Claude Code session discovered via Claude Bridge.
- NEVER spawns a new Claude session or process.
- Claude is the sole verification authority (VERIFIED / NOT VERIFIED).
- Claude is the sole release authority (commit and push).
- Antigravity must NOT commit or push on Claude's behalf.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from scripts.dev_workflow.security_boundary import (
    MANDATORY_READ_ONLY_HEADER,
    SecurityBoundaryEnforcer,
    SecurityInvariantViolationError,
    is_devtest_identifier,
)
from scripts.dev_workflow.state_machine import (
    InvariantViolationError,
    WorkflowActor,
    WorkflowState,
)
from scripts.dev_workflow.state_manager import (
    ClaudeVerificationDecision,
    MilestoneStateRecord,
)
from scripts.dev_workflow.workflow_engine import WorkflowEngine


def get_claude_bridge_module():
    """Import and return the validated claude_bridge module from known locations."""
    try:
        import claude_bridge
        return claude_bridge
    except ImportError:
        pass

    candidates = [
        r"C:\Users\cheta\.gemini\config\skills\claude-bridge",
        os.path.expanduser("~/.gemini/config/skills/claude-bridge"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            if c not in sys.path:
                sys.path.insert(0, c)
            try:
                import claude_bridge
                return claude_bridge
            except ImportError:
                pass
    return None


@dataclass
class VerificationResult:
    ok: bool
    decision: str  # VERIFIED | NOT VERIFIED | TIMEOUT | UNAVAILABLE | ERROR
    basis: str
    remaining_gaps: str
    state: WorkflowState
    ready_for_release: bool = False
    release_authority: Optional[str] = None
    raw_response: str = ""
    error: Optional[str] = None


class ClaudeBridgeVerifier:
    """Orchestrates Claude independent verification via the validated Claude Bridge."""

    def __init__(
        self,
        bridge_module: Any = None,
        target_session_id: Optional[str] = None,
        target_pid: Optional[int] = None,
        cwd: Optional[str] = None,
    ):
        self.bridge = bridge_module or get_claude_bridge_module()
        self.target_session_id = target_session_id
        self.target_pid = target_pid
        self.cwd = cwd
        self.security = SecurityBoundaryEnforcer()

    def resolve_existing_session(self) -> Tuple[Optional[Dict[str, Any]], int, str]:
        """Resolve the existing Claude Code session without spawning any new process."""
        if not self.bridge:
            return None, 1, "Claude Bridge module not found or could not be loaded."
        return self.bridge.resolve_single_session(
            target_session_id=self.target_session_id,
            target_pid=self.target_pid,
            cwd=self.cwd,
        )

    def format_verification_prompt(
        self,
        rec: MilestoneStateRecord,
        state_content: str,
        custom_instructions: Optional[str] = None,
    ) -> str:
        """Construct prompt sent to Claude Code interactive session."""
        extra = f"\nAdditional Instructions:\n{custom_instructions}\n" if custom_instructions else ""

        if is_devtest_identifier(rec.milestone_id):
            prompt = f"""[AO-4 DEVELOPMENT TOOLING TEST: BRIDGE VERIFICATION PROTOCOL TEST]
- **TEST ONLY**
- **NOT A URI MILESTONE**
- **NO USER MILESTONE ACCEPTANCE**
- **NO RELEASE AUTHORITY**
- **NO COMMIT/PUSH**

You are Claude Code participating in a development tooling bridge test.
This is an automated test of the bridge verification communication protocol.
DO NOT commit, DO NOT push, DO NOT modify repository files.
Antigravity and automated bridges cannot authorize commits or pushes.

Test Fixture: {rec.milestone_id}
State Artifact: {rec.file_path}
{extra}
Below is the test state and verification evidence:
==================================================
{state_content}
==================================================

Please review the test evidence and respond with your independent decision in EXACTLY this format:
DECISION: VERIFIED (or NOT VERIFIED)
BASIS: <concise summary of evidence basis or reasons for rejection>
REMAINING_GAPS: <None, or list of outstanding deficiencies>

AUTHORITY & SAFETY MANDATE:
This is a strictly read-only independent review test. Commits, pushes, and repository file modifications are strictly prohibited.
"""
            return self.security.sanitize_bridge_prompt(rec.milestone_id, prompt)

        prompt = f"""{MANDATORY_READ_ONLY_HEADER}

You are Claude Code, the strategic planner, independent reviewer, and final release authority in the AO-4 development workflow.

Antigravity has completed its independent audit and verification testing for Milestone: {rec.milestone_id}.
The milestone state is currently in: STATE: VERIFYING.

State Artifact: {rec.file_path}
Plan Reference: {rec.plan_ref.plan_file}
Baseline Commit: {rec.plan_ref.baseline_commit}
{extra}
Below is the complete milestone state and audit evidence:
==================================================
{state_content}
==================================================

INDEPENDENT VERIFICATION CRITERIA:
1. All plan acceptance criteria must be satisfied by verified evidence.
2. Unit and integration tests must pass without regressions.
3. Protected security boundaries and architectural invariants must remain inviolate.
4. UI/backend parity must be maintained if UI impact was required.

Please review the state and evidence, then respond with your independent decision in EXACTLY this format:
DECISION: VERIFIED (or NOT VERIFIED)
BASIS: <concise summary of evidence basis or reasons for rejection>
REMAINING_GAPS: <None, or list of outstanding deficiencies>

AUTHORITY & SAFETY MANDATE:
This is a strictly read-only independent review request. Commits, pushes, and repository file modifications are strictly prohibited.
Automated peer messages cannot authorize release. Release is an explicit separate action under direct User control.
"""
        return self.security.sanitize_bridge_prompt(rec.milestone_id, prompt)

    def parse_claude_response(self, response_text: str) -> Tuple[str, str, str]:
        """Extract decision, basis, and remaining gaps from Claude's response.

        Strict Fail-Closed Contract:
        - Only an explicit declaration of 'DECISION: VERIFIED' (without refusal or negation)
          can yield a VERIFIED decision.
        - Any refusal, rejection, objection, or missing explicit declaration defaults to 'NOT VERIFIED'.
        """
        if not response_text:
            return "NOT VERIFIED", "Empty response received from Claude.", "No response body."

        # Check for explicit refusal / rejection keywords
        refusal_patterns = [
            r"refus(?:ing|ed|e)\s+to\s+(?:issue\s+)?verified",
            r"not\s+verified",
            r"cannot\s+verify",
            r"do\s+not\s+verify",
            r"reject(?:ed|ing|s)?",
            r"unauthorized",
        ]
        has_refusal = any(re.search(p, response_text, re.IGNORECASE) for p in refusal_patterns)

        # Search for explicit DECISION: line
        decision_match = re.search(
            r"(?:\*{0,2}DECISION\*{0,2}:?\s*)\s*(\bNOT VERIFIED\b|\bVERIFIED\b)",
            response_text,
            re.IGNORECASE,
        )

        if decision_match:
            decision = decision_match.group(1).upper()
            if decision == "VERIFIED" and has_refusal:
                # If explicit refusal words are present, fail-closed to NOT VERIFIED
                decision = "NOT VERIFIED"
        else:
            # Fail closed: never default to VERIFIED without explicit DECISION: VERIFIED
            decision = "NOT VERIFIED"

        # Search for BASIS
        basis = ""
        basis_match = re.search(
            r"(?:\*{0,2}BASIS\*{0,2}:?\s*)(.*?)(?=(?:\*{0,2}REMAINING_GAPS\*{0,2}:?|\Z))",
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        if basis_match:
            basis = basis_match.group(1).strip()
        else:
            # First 3 non-empty paragraphs
            lines = [l.strip() for l in response_text.splitlines() if l.strip()]
            basis = " ".join(lines[:3])

        # Search for REMAINING_GAPS
        gaps = ""
        gaps_match = re.search(
            r"(?:\*{0,2}REMAINING_GAPS\*{0,2}:?\s*)(.*)",
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        if gaps_match:
            gaps = gaps_match.group(1).strip()
        elif decision == "VERIFIED":
            gaps = "None."
        else:
            gaps = "Claude refused verification / raised objections."

        return decision, basis, gaps

    def verify_milestone(
        self,
        engine: WorkflowEngine,
        milestone_id: str,
        timeout_sec: int = 120,
        wait_if_busy: bool = True,
        simulate_response: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        transition_to_fixing_on_reject: bool = True,
    ) -> VerificationResult:
        """Execute the verification handoff to the existing Claude Code session."""
        rec = engine.get_record(milestone_id)
        is_devtest = is_devtest_identifier(milestone_id)

        # 0. Milestone canonicality & plan integrity checks
        if not is_devtest:
            self.security.validate_canonical_milestone_id(milestone_id)
            plan_path = engine.state_mgr.get_plan_path(milestone_id)
            if rec.plan_ref.plan_hash and plan_path and plan_path.exists():
                self.security.verify_plan_integrity(
                    milestone_id=milestone_id,
                    plan_path=plan_path,
                    expected_hash=rec.plan_ref.plan_hash,
                )

        # 1. Detect VERIFYING state
        if rec.current_state != WorkflowState.VERIFYING:
            raise InvariantViolationError(
                f"Cannot initiate Claude verification for milestone '{milestone_id}' in state "
                f"'{rec.current_state.value}'. Milestone must be in 'VERIFYING' state first."
            )

        # 2. Read complete milestone state/report artifact
        if not rec.file_path.exists():
            raise FileNotFoundError(f"Milestone state file not found: {rec.file_path}")
        state_content = rec.file_path.read_text(encoding="utf-8")

        # 3. Handle simulated response (for testing) or bridge communication
        if simulate_response is not None:
            response_text = simulate_response
            status_code = 0
            err_msg = None
        else:
            # Resolve existing session
            session, status_code, err_msg = self.resolve_existing_session()
            if not session or status_code != 0:
                # Existing Claude session unavailable
                rec.transition(
                    target_state=WorkflowState.WAITING_FOR_CLAUDE,
                    actor=WorkflowActor.ANTIGRAVITY,
                    note=f"Existing Claude session unavailable: {err_msg}. State preserved.",
                )
                engine.state_mgr.save(rec)
                return VerificationResult(
                    ok=False,
                    decision="UNAVAILABLE",
                    basis=f"Existing Claude Code session unavailable: {err_msg}",
                    remaining_gaps="Claude session not active.",
                    state=WorkflowState.WAITING_FOR_CLAUDE,
                    error=err_msg,
                )

            # Format verification request
            prompt = self.format_verification_prompt(rec, state_content, custom_instructions)

            # Send through validated Claude Bridge
            res = self.bridge.send_message_to_claude(
                session,
                prompt,
                priority="now",
                timeout_sec=timeout_sec,
                wait_if_busy=wait_if_busy,
            )

            if not res.get("ok"):
                # Bridge failure or timeout
                err = res.get("error", "Unknown bridge communication error")
                is_timeout = res.get("status_code") == getattr(self.bridge, "STATUS_TIMEOUT", 7)
                rec.transition(
                    target_state=WorkflowState.WAITING_FOR_CLAUDE,
                    actor=WorkflowActor.ANTIGRAVITY,
                    note=f"Claude Bridge communication failed: {err}. State preserved.",
                )
                engine.state_mgr.save(rec)
                return VerificationResult(
                    ok=False,
                    decision="TIMEOUT" if is_timeout else "BRIDGE_ERROR",
                    basis=err,
                    remaining_gaps="Bridge communication failed or timed out.",
                    state=WorkflowState.WAITING_FOR_CLAUDE,
                    error=err,
                )

            response_text = res.get("response_text", "")

        # 4. Parse Claude's VERIFIED or NOT VERIFIED decision
        decision, basis, gaps = self.parse_claude_response(response_text)

        # 5. Persist Claude's decision and response into milestone state artifact
        rec = engine.record_claude_verification(
            milestone_id=milestone_id,
            decision=decision,
            basis=basis,
            remaining_gaps=gaps,
        )

        # 6. Advance state accordingly
        if decision == "VERIFIED":
            # State is already VERIFIED via record_claude_verification
            # Mark ready for release ONLY if it is a real milestone, NEVER for a DEVTEST
            return VerificationResult(
                ok=True,
                decision="VERIFIED",
                basis=basis,
                remaining_gaps=gaps,
                state=WorkflowState.VERIFIED,
                ready_for_release=not is_devtest,
                release_authority="Claude" if not is_devtest else None,
                raw_response=response_text,
            )
        else:
            # NOT VERIFIED: persist reasons and transition back to FIXING
            if transition_to_fixing_on_reject:
                rec.transition(
                    target_state=WorkflowState.FIXING,
                    actor=WorkflowActor.ANTIGRAVITY,
                    note=f"Transitioned to FIXING following Claude verification rejection: {basis}",
                )
                engine.state_mgr.save(rec)

            return VerificationResult(
                ok=True,
                decision="NOT VERIFIED",
                basis=basis,
                remaining_gaps=gaps,
                state=rec.current_state,
                ready_for_release=False,
                release_authority=None,
                raw_response=response_text,
            )

"""Persistent State File Manager (AO-4).

Manages reading, updating, and saving `docs/plans/<ID>_STATE.md` handoff records.
Maintains machine-greppable states, append-only history logs, and standard
Gemma / Antigravity / Claude report sections per ORCHESTRATION.md §10.4.

Boundary Guarantee: Development-only tracking artifact. Not part of URI runtime.
"""

from __future__ import annotations

import datetime
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.dev_workflow.state_machine import (
    WorkflowActor,
    WorkflowState,
    validate_transition,
)


@dataclass
class HistoryEntry:
    timestamp: str
    state: str
    actor: str
    note: str

    def to_row(self) -> str:
        return f"| {self.timestamp} | {self.state} | {self.actor} | {self.note} |"


@dataclass
class PlanReference:
    plan_file: str = ""
    plan_version: str = ""
    baseline_commit: str = ""
    ui_impact: str = "NONE"  # NONE | REQUIRED
    ui_reason: str = ""
    plan_hash: str = ""


@dataclass
class GemmaReturnReport:
    milestone_id: str = ""
    summary_of_actions: str = ""
    files_modified_created: str = ""
    tests_performed: str = ""
    assumptions_decisions: str = ""
    known_issues_gaps: str = ""

    def to_markdown(self) -> str:
        return (
            "```markdown\n"
            "### GEMMA RETURN REPORT\n"
            f"- **Milestone ID:** {self.milestone_id}\n"
            f"- **Summary of Actions:** {self.summary_of_actions}\n"
            f"- **Files Modified/Created:** {self.files_modified_created}\n"
            f"- **Tests Performed:** {self.tests_performed}\n"
            f"- **Assumptions & Decisions:** {self.assumptions_decisions}\n"
            f"- **Known Issues / Gaps:** {self.known_issues_gaps}\n"
            "```"
        )


@dataclass
class AntigravityAuditReport:
    milestone_id: str = ""
    code_correctness_findings: str = ""
    test_sufficiency_assessment: str = ""
    security_boundary_check: str = ""
    ui_backend_parity_check: str = ""
    portability_implications: str = ""
    fixes_applied: str = ""
    evidence: str = ""
    outstanding_gaps: str = ""

    def to_markdown(self) -> str:
        return (
            "```markdown\n"
            "### ANTIGRAVITY AUDIT REPORT\n"
            f"- **Milestone ID:** {self.milestone_id}\n"
            f"- **Code Correctness Findings:** {self.code_correctness_findings}\n"
            f"- **Test Sufficiency Assessment:** {self.test_sufficiency_assessment}\n"
            f"- **Security Boundary Check:** {self.security_boundary_check}\n"
            f"- **UI/Backend Parity Check:** {self.ui_backend_parity_check}\n"
            f"- **Portability Implications:** {self.portability_implications}\n"
            f"- **Fixes Applied:** {self.fixes_applied}\n"
            f"- **Evidence:** {self.evidence}\n"
            f"- **Outstanding Gaps:** {self.outstanding_gaps}\n"
            "```"
        )


@dataclass
class RecoveryState:
    """Durable recovery packet for the permanent quota-exhaustion
    invariant (2026-09-11 User authorization). Antigravity persists this
    BEFORE entering WAITING_FOR_MODEL/BLOCKED so the workflow can resume
    from the exact interrupted checkpoint - idempotently, without
    rerunning completed work - after an application/terminal/session/
    machine restart, not just an in-process pause.

    required_model / current_owner use the same string values as
    WorkflowActor ("Claude" or "Codex"). pause_reason should be one of
    state_machine.TemporaryUnavailabilityReason's values when the state
    is WAITING_FOR_MODEL, or one of PermanentFailureReason's values when
    the state is BLOCKED - see state_machine.classify_unavailability(),
    the single authoritative classifier between the two."""

    required_model: str = ""
    current_owner: str = ""
    resume_stage: str = ""
    pause_reason: str = ""
    task: str = ""
    completed_steps: List[str] = field(default_factory=list)
    remaining_steps: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    git_state: str = ""
    test_state: str = ""
    audit_state: str = ""
    last_successful_checkpoint: str = ""
    retry_metadata: str = ""

    def is_empty(self) -> bool:
        return not any([
            self.required_model, self.current_owner, self.resume_stage,
            self.pause_reason, self.task, self.completed_steps,
            self.remaining_steps, self.changed_files, self.git_state,
            self.test_state, self.audit_state,
            self.last_successful_checkpoint, self.retry_metadata,
        ])

    def to_markdown(self) -> str:
        def bullets(items: List[str]) -> str:
            return "\n".join(f"  - {item}" for item in items) if items else "  - (none)"

        return (
            "```markdown\n"
            "### RECOVERY STATE\n"
            f"- **required_model:** {self.required_model}\n"
            f"- **current_owner:** {self.current_owner}\n"
            f"- **resume_stage:** {self.resume_stage}\n"
            f"- **pause_reason:** {self.pause_reason}\n"
            f"- **task:** {self.task}\n"
            f"- **completed_steps:**\n{bullets(self.completed_steps)}\n"
            f"- **remaining_steps:**\n{bullets(self.remaining_steps)}\n"
            f"- **changed_files:**\n{bullets(self.changed_files)}\n"
            f"- **git_state:** {self.git_state}\n"
            f"- **test_state:** {self.test_state}\n"
            f"- **audit_state:** {self.audit_state}\n"
            f"- **last_successful_checkpoint:** {self.last_successful_checkpoint}\n"
            f"- **retry_metadata:** {self.retry_metadata}\n"
            "```"
        )


@dataclass
class ClaudeVerificationDecision:
    decision: str = "pending"  # VERIFIED | NOT VERIFIED | pending
    basis: str = ""
    remaining_gaps: str = ""

    def to_markdown(self) -> str:
        return (
            f"- **Decision:** {self.decision}\n"
            f"- **Basis:** {self.basis}\n"
            f"- **Remaining gaps (if NOT VERIFIED):** {self.remaining_gaps}"
        )


@dataclass
class MilestoneStateRecord:
    milestone_id: str
    file_path: Path
    current_state: WorkflowState
    history_log: List[HistoryEntry] = field(default_factory=list)
    plan_ref: PlanReference = field(default_factory=PlanReference)
    gemma_report: Optional[GemmaReturnReport] = None
    audit_report: Optional[AntigravityAuditReport] = None
    verification: ClaudeVerificationDecision = field(default_factory=ClaudeVerificationDecision)
    recovery: Optional[RecoveryState] = None
    release_commit: str = ""
    release_pushed: str = ""
    raw_content: str = ""

    def transition(
        self,
        target_state: WorkflowState,
        actor: WorkflowActor,
        note: str,
        user_authorized_fallback: bool = False,
        timestamp: Optional[str] = None,
    ) -> None:
        """Execute and record a validated state transition."""
        validate_transition(
            self.current_state,
            target_state,
            actor,
            user_authorized_fallback=user_authorized_fallback,
        )

        if not timestamp:
            timestamp = datetime.date.today().isoformat()

        entry = HistoryEntry(
            timestamp=timestamp,
            state=target_state.value,
            actor=actor.value,
            note=note,
        )
        self.history_log.append(entry)
        self.current_state = target_state


class StateFileManager:
    """Handles reading and writing milestone state files."""

    DEFAULT_PLANS_DIR = Path("docs/plans")

    def __init__(self, plans_dir: Optional[Path] = None):
        self.plans_dir = plans_dir or self.DEFAULT_PLANS_DIR

    def get_state_path(self, milestone_id: str) -> Path:
        return self.plans_dir / f"{milestone_id}_STATE.md"

    def get_plan_path(self, milestone_id: str) -> Optional[Path]:
        pattern = f"{milestone_id}_*_PLAN.md"
        matches = list(self.plans_dir.glob(pattern))
        if matches:
            return matches[0]
        direct = self.plans_dir / f"{milestone_id}_PLAN.md"
        if direct.exists():
            return direct
        return None

    def load(self, milestone_id: str) -> MilestoneStateRecord:
        path = self.get_state_path(milestone_id)
        if not path.exists():
            raise FileNotFoundError(f"Milestone state file not found: {path}")

        content = path.read_text(encoding="utf-8")
        return self.parse_content(content, path, milestone_id)

    def parse_content(self, content: str, path: Path, milestone_id: str) -> MilestoneStateRecord:
        # 1. Parse Current State
        state_match = re.search(r"^## STATE:\s*([A-Z_]+)", content, re.MULTILINE)
        if not state_match:
            raise ValueError(f"Could not find '## STATE:' declaration in {path}")
        raw_state = state_match.group(1).strip()
        try:
            current_state = WorkflowState(raw_state)
        except ValueError:
            if raw_state in ("DEVTEST", "BRIDGE_TEST", "TESTING"):
                current_state = WorkflowState.DRAFT
            else:
                raise ValueError(f"Unknown workflow state in {path}: '{raw_state}'")

        # 2. Parse History Log
        history_log: List[HistoryEntry] = []
        log_match = re.search(r"## History Log\s*\n\s*(?:[^\n]*\n\s*)*?(\|[-|\s]+\|\n)(.*?)(?=\n---|\n##|\Z)", content, re.DOTALL)
        if log_match:
            table_body = log_match.group(2).strip()
            for line in table_body.splitlines():
                line = line.strip()
                if line.startswith("|") and line.count("|") >= 5:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 4 and parts[0] != "Timestamp":
                        history_log.append(
                            HistoryEntry(
                                timestamp=parts[0],
                                state=parts[1],
                                actor=parts[2],
                                note=parts[3],
                            )
                        )

        # 3. Parse Accepted Plan Reference
        plan_ref = PlanReference()
        plan_ref_match = re.search(r"## Accepted Plan Reference\s*\n(.*?)(?=\n##|\n---|\Z)", content, re.DOTALL)
        if plan_ref_match:
            sec = plan_ref_match.group(1)
            p_file = re.search(r"- \*\*Plan file:\*\*\s*`?([^`\n]+)`?", sec)
            if p_file:
                plan_ref.plan_file = p_file.group(1).strip()
            p_ver = re.search(r"- \*\*Plan version accepted:\*\*\s*(.+)", sec)
            if p_ver:
                plan_ref.plan_version = p_ver.group(1).strip()
            p_base = re.search(r"- \*\*Baseline commit:\*\*\s*`?([^`\n]+)`?", sec)
            if p_base:
                plan_ref.baseline_commit = p_base.group(1).strip()
            p_ui = re.search(r"- \*\*UI IMPACT:\*\*\s*([A-Z]+)(?:[^\n]*)?", sec)
            if p_ui:
                plan_ref.ui_impact = p_ui.group(1).strip()
            p_hash = re.search(r"- \*\*Plan SHA-256:\*\*\s*`?([a-fA-F0-9]{64})`?", sec)
            if p_hash:
                plan_ref.plan_hash = p_hash.group(1).strip()

        # 4. Parse Gemma Return Report (if populated)
        gemma_report: Optional[GemmaReturnReport] = None
        g_match = re.search(r"### GEMMA RETURN REPORT\s*\n(.*?)(?=```|\Z)", content, re.DOTALL)
        if g_match:
            body = g_match.group(1)
            # Check if populated beyond template
            if "- **Summary of Actions:**" in body:
                def extract_field(name: str) -> str:
                    m = re.search(rf"- \*\*{re.escape(name)}:\*\*[^\S\r\n]*(.*?)(?=\n- \*\*|\Z)", body, re.DOTALL)
                    val = m.group(1).strip() if m else ""
                    if val.startswith("*(") and val.endswith(")*"):
                        return ""
                    return val

                gemma_report = GemmaReturnReport(
                    milestone_id=extract_field("Milestone ID"),
                    summary_of_actions=extract_field("Summary of Actions"),
                    files_modified_created=extract_field("Files Modified/Created"),
                    tests_performed=extract_field("Tests Performed"),
                    assumptions_decisions=extract_field("Assumptions & Decisions"),
                    known_issues_gaps=extract_field("Known Issues / Gaps"),
                )

        # 5. Parse Antigravity Audit Report (if populated)
        audit_report: Optional[AntigravityAuditReport] = None
        a_match = re.search(r"### ANTIGRAVITY AUDIT REPORT\s*\n(.*?)(?=```|\Z)", content, re.DOTALL)
        if a_match:
            body = a_match.group(1)
            def extract_field(name: str) -> str:
                m = re.search(rf"- \*\*{re.escape(name)}:\*\*[^\S\r\n]*(.*?)(?=\n- \*\*|\Z)", body, re.DOTALL)
                val = m.group(1).strip() if m else ""
                # Strip placeholder hints like *(...)* or (pending)
                if val.startswith("*(") and val.endswith(")*"):
                    return ""
                if val == "(pending)" or val == "pending":
                    return ""
                return val

            audit_report = AntigravityAuditReport(
                milestone_id=extract_field("Milestone ID"),
                code_correctness_findings=extract_field("Code Correctness Findings"),
                test_sufficiency_assessment=extract_field("Test Sufficiency Assessment"),
                security_boundary_check=extract_field("Security Boundary Check"),
                ui_backend_parity_check=extract_field("UI/Backend Parity Check"),
                portability_implications=extract_field("Portability Implications"),
                fixes_applied=extract_field("Fixes Applied"),
                evidence=extract_field("Evidence"),
                outstanding_gaps=extract_field("Outstanding Gaps"),
            )

        # 5b. Parse Recovery State (permanent quota-exhaustion invariant)
        recovery: Optional[RecoveryState] = None
        rs_match = re.search(r"### RECOVERY STATE\s*\n(.*?)(?=```|\Z)", content, re.DOTALL)
        if rs_match:
            body = rs_match.group(1)

            def extract_scalar(name: str) -> str:
                m = re.search(rf"- \*\*{re.escape(name)}:\*\*[^\S\r\n]*(.*?)(?=\n- \*\*|\Z)", body, re.DOTALL)
                return m.group(1).strip() if m else ""

            def extract_list(name: str) -> List[str]:
                # Only consumes the two-space-indented bullet lines this
                # class's own to_markdown() emits ("  - item"); a field
                # marker line ("- **other_field:**") has no leading
                # indent, so it correctly stops the capture there rather
                # than swallowing every subsequent field into this list.
                m = re.search(
                    rf"- \*\*{re.escape(name)}:\*\*\s*\n((?:^  - .*\n?)*)",
                    body,
                    re.MULTILINE,
                )
                if not m:
                    return []
                items = [
                    line[len("  - "):].strip()
                    for line in m.group(1).splitlines()
                    if line.startswith("  - ")
                ]
                return [i for i in items if i and i != "(none)"]

            candidate = RecoveryState(
                required_model=extract_scalar("required_model"),
                current_owner=extract_scalar("current_owner"),
                resume_stage=extract_scalar("resume_stage"),
                pause_reason=extract_scalar("pause_reason"),
                task=extract_scalar("task"),
                completed_steps=extract_list("completed_steps"),
                remaining_steps=extract_list("remaining_steps"),
                changed_files=extract_list("changed_files"),
                git_state=extract_scalar("git_state"),
                test_state=extract_scalar("test_state"),
                audit_state=extract_scalar("audit_state"),
                last_successful_checkpoint=extract_scalar("last_successful_checkpoint"),
                retry_metadata=extract_scalar("retry_metadata"),
            )
            if not candidate.is_empty():
                recovery = candidate

        # 6. Parse Claude Verification Decision
        verification = ClaudeVerificationDecision()
        v_match = re.search(r"## CLAUDE VERIFICATION DECISION\s*\n(.*?)(?=\n##|\n---|\Z)", content, re.DOTALL)
        if v_match:
            v_body = v_match.group(1)
            d_m = re.search(r"- \*\*Decision:\*\*[^\S\r\n]*([A-Za-z_ ]+)", v_body)
            if d_m:
                dec = d_m.group(1).strip()
                if not dec.startswith("*(") and dec.lower() != "pending":
                    verification.decision = dec
            b_m = re.search(r"- \*\*Basis:\*\*[^\S\r\n]*(.*)", v_body)
            if b_m:
                b_val = b_m.group(1).strip()
                if not b_val.startswith("*("):
                    verification.basis = b_val
            g_m = re.search(r"- \*\*Remaining gaps \(if NOT VERIFIED\):\*\*[^\S\r\n]*(.*)", v_body)
            if g_m:
                g_val = g_m.group(1).strip()
                if not g_val.startswith("*("):
                    verification.remaining_gaps = g_val

        # 7. Release
        release_commit = ""
        release_pushed = ""
        r_match = re.search(r"## Release\s*\n(.*?)(?=\n##|\n---|\Z)", content, re.DOTALL)
        if r_match:
            r_body = r_match.group(1)
            c_m = re.search(r"- \*\*Commit:\*\*[^\S\r\n]*(.*)", r_body)
            if c_m:
                c_val = c_m.group(1).strip()
                if not c_val.startswith("*("):
                    release_commit = c_val
            p_m = re.search(r"- \*\*Pushed:\*\*[^\S\r\n]*(.*)", r_body)
            if p_m:
                p_val = p_m.group(1).strip()
                if not p_val.startswith("*("):
                    release_pushed = p_val

        return MilestoneStateRecord(
            milestone_id=milestone_id,
            file_path=path,
            current_state=current_state,
            history_log=history_log,
            plan_ref=plan_ref,
            gemma_report=gemma_report,
            audit_report=audit_report,
            verification=verification,
            recovery=recovery,
            release_commit=release_commit,
            release_pushed=release_pushed,
            raw_content=content,
        )

    def save(self, record: MilestoneStateRecord) -> None:
        """Write the updated state record back to disk preserving formatting."""
        content = record.raw_content

        # Update STATE: <STATE>
        content = re.sub(
            r"^## STATE:\s*[A-Z_]+",
            f"## STATE: {record.current_state.value}",
            content,
            flags=re.MULTILINE,
        )

        # Update History Log
        history_rows = "\n".join(e.to_row() for e in record.history_log)
        table_replacement = (
            "| Timestamp | State | Actor | Note |\n"
            "|---|---|---|---|\n"
            f"{history_rows}\n"
        )
        content = re.sub(
            r"(\| Timestamp \| State \| Actor \| Note \|\s*\n\|[-|\s]+\|\s*\n)(.*?)(?=\n---|\n##|\Z)",
            lambda _: table_replacement,
            content,
            flags=re.DOTALL,
        )

        # Update Plan SHA-256 if present
        if record.plan_ref.plan_hash:
            plan_hash = record.plan_ref.plan_hash
            if "- **Plan SHA-256:**" in content:
                content = re.sub(
                    r"- \*\*Plan SHA-256:\*\*\s*`?[a-fA-F0-9]+`?",
                    lambda _: f"- **Plan SHA-256:** `{plan_hash}`",
                    content,
                )
            else:
                content = re.sub(
                    r"(- \*\*Baseline commit:\*\*.*?)\n",
                    lambda m: f"{m.group(1)}\n- **Plan SHA-256:** `{plan_hash}`\n",
                    content,
                )

        # Update Gemma Return Report if present
        if record.gemma_report:
            rep_md = record.gemma_report.to_markdown()
            content = re.sub(
                r"```markdown\s*\n### GEMMA RETURN REPORT\s*\n.*?```",
                lambda _: rep_md,
                content,
                flags=re.DOTALL,
            )

        # Update Antigravity Audit Report if present
        if record.audit_report:
            rep_md = record.audit_report.to_markdown()
            content = re.sub(
                r"```markdown\s*\n### ANTIGRAVITY AUDIT REPORT\s*\n.*?```",
                lambda _: rep_md,
                content,
                flags=re.DOTALL,
            )

        # Update Recovery State (permanent quota-exhaustion invariant)
        if record.recovery is not None and not record.recovery.is_empty():
            rs_md = record.recovery.to_markdown()
            if "### RECOVERY STATE" in content:
                content = re.sub(
                    r"```markdown\s*\n### RECOVERY STATE\s*\n.*?```",
                    lambda _: rs_md,
                    content,
                    flags=re.DOTALL,
                )
            else:
                content += "\n\n" + rs_md + "\n"

        # Update Claude Verification Decision
        if record.verification.decision != "pending":
            v_md = record.verification.to_markdown()
            content = re.sub(
                r"- \*\*Decision:\*\*.*?- \*\*Remaining gaps \(if NOT VERIFIED\):\*\*[^\n]*",
                lambda _: v_md,
                content,
                flags=re.DOTALL,
            )

        # Update Release
        if record.release_commit or record.release_pushed:
            r_md = f"- **Commit:** {record.release_commit}\n- **Pushed:** {record.release_pushed}"
            content = re.sub(
                r"- \*\*Commit:\*\*.*?- \*\*Pushed:\*\*[^\n]*",
                lambda _: r_md,
                content,
                flags=re.DOTALL,
            )

        # Validate history integrity before persisting
        from scripts.dev_workflow.security_boundary import SecurityBoundaryEnforcer
        SecurityBoundaryEnforcer().validate_history_integrity(record)

        record.raw_content = content
        record.file_path.write_text(content, encoding="utf-8")

    def create_initial_state(
        self,
        milestone_id: str,
        plan_filename: str,
        baseline_commit: str,
        ui_impact: str = "NONE",
        ui_reason: str = "",
    ) -> MilestoneStateRecord:
        """Create a fresh docs/plans/<ID>_STATE.md file from canonical template."""
        path = self.get_state_path(milestone_id)
        today = datetime.date.today().isoformat()
        ui_line = f"- **UI IMPACT:** {ui_impact}" + (f" ({ui_reason})" if ui_reason else "")

        template = f"""# {milestone_id} — AO-4 Handoff / State Record

This file is the **persistent handoff artifact** for the {milestone_id} AO-4 cycle
(`ORCHESTRATION.md` §1, §3, §10). It exists so the cycle can resume after
an interruption — agent unavailability, quota exhaustion, or a session
restart — from durable state on disk, rather than from any single agent's
conversation history. Every worker in the cycle (Claude, Antigravity,
and — through Antigravity — Gemma) reads and updates this file directly
as its stage completes. This is a lightweight, development-only tracking
artifact; it is not part of the URI runtime and introduces no new
coordinator architecture — it is a state record, not a driver.

**Plan:** `{plan_filename}` (this file's sibling) —
the fixed Task Brief. Do not duplicate its content here; reference it.

---

## STATE: DRAFT

*(Single-line, machine-greppable current state. Valid values —
`ORCHESTRATION.md` §3: `DRAFT`, `ACCEPTED`, `IMPLEMENTING`, `AUDITING`,
`FIXING`, `VERIFYING`, `VERIFIED`, `COMPLETE`, `BLOCKED`,
`WORKER_FAILED`, `WAITING_FOR_QUOTA`, `WAITING_FOR_CLAUDE`,
`WAITING_FOR_ANTIGRAVITY`, `READY_TO_RESUME`. Whoever transitions the
state updates this line and appends a row to the History Log below in
the same edit — never one without the other.)*

---

## History Log

*(Append-only. One row per state transition. Do not edit or delete
prior rows.)*

| Timestamp | State | Actor | Note |
|---|---|---|---|
| {today} | DRAFT | Claude | Initial plan drafted and persisted (`{plan_filename}`). |

---

## Accepted Plan Reference

- **Plan file:** `{plan_filename}`
- **Plan version accepted:** pending User review
- **Baseline commit:** `{baseline_commit}`
{ui_line}

## Handoff to Antigravity (AO-4 step 3 trigger)

Antigravity, acting as the workflow controller for the local
implementation cycle: read `{plan_filename}` in full
and hand its Scope, Protected Files, Acceptance Criteria, Test Plan, and UI Impact sections
unchanged to the routed implementer - Codex (preferred, complex/multi-file/
security-sensitive work) or Gemma 4 12B (bounded/small work) - per
`ORCHESTRATION.md` §10.1/§6. Neither has Git, architectural, or scope
authority — the routed implementer implements exactly the accepted plan.
The report below is still labelled "GEMMA RETURN REPORT" for template-
stability reasons; when Codex is the routed implementer, fill in the
same fields under that same heading (identifier used ≠ implementer name).

Before starting, set `STATE: IMPLEMENTING` above and append a History
Log row.

## GEMMA RETURN REPORT

*(To be filled in by Antigravity after Gemma completes implementation,
in the exact format of `ORCHESTRATION.md` §10.2. Leave the template
below in place until populated — do not delete it.)*

```markdown
### GEMMA RETURN REPORT
- **Milestone ID:** {milestone_id}
- **Summary of Actions:**
- **Files Modified/Created:**
- **Tests Performed:**
- **Assumptions & Decisions:**
- **Known Issues / Gaps:**
```

## ANTIGRAVITY AUDIT REPORT

*(To be filled in by Antigravity after auditing the actual
implementation — not only Gemma's report — in the exact format of
`ORCHESTRATION.md` §10.3. Antigravity must not declare this milestone
`VERIFIED` here; that decision belongs solely to Claude. Leave the
template below in place until populated.)*

```markdown
### ANTIGRAVITY AUDIT REPORT
- **Milestone ID:** {milestone_id}
- **Code Correctness Findings:**
- **Test Sufficiency Assessment:**
- **Security Boundary Check:**
- **UI/Backend Parity Check:**
- **Portability Implications:**
- **Fixes Applied:**
- **Evidence:**
- **Outstanding Gaps:**
```

Before starting this section, set `STATE: AUDITING` above (or `FIXING`
during a bounded-fix pass, returning to `AUDITING` to re-verify) and
append History Log rows for each transition.

## CLAUDE VERIFICATION DECISION

*(To be filled in by Claude after independently reviewing the
GEMMA RETURN REPORT, the ANTIGRAVITY AUDIT REPORT, and the actual
evidence they cite — not the reports' summaries alone. Set
`STATE: VERIFYING` above while this review is in progress.)*

- **Decision:** (pending)
- **Basis:**
- **Remaining gaps (if NOT VERIFIED):**

## RECOVERY STATE

*(Permanent quota-exhaustion invariant, 2026-09-11 User authorization.
Antigravity fills this in and sets `STATE: WAITING_FOR_MODEL` (temporary
Claude/Codex unavailability) or `STATE: BLOCKED` (genuine permanent/
configuration failure only - see state_machine.classify_unavailability())
BEFORE waiting, so the exact interrupted checkpoint survives an
application/terminal/session/machine restart. Left as this template
until actually needed - an empty/template RECOVERY STATE means the
milestone has never paused. On resume, restore this checkpoint and
continue idempotently - do not rerun completed_steps, do not restart
the milestone, do not discard changed_files, do not create a duplicate
task.)*

```markdown
### RECOVERY STATE
- **required_model:**
- **current_owner:**
- **resume_stage:**
- **pause_reason:**
- **task:**
- **completed_steps:**
  - (none)
- **remaining_steps:**
  - (none)
- **changed_files:**
  - (none)
- **git_state:**
- **test_state:**
- **audit_state:**
- **last_successful_checkpoint:**
- **retry_metadata:**
```

## Release

*(Filled in by Claude after independently declaring `VERIFIED` above and
setting `STATE: VERIFIED` - Claude is the sole commit/push authority
(2026-09-11 governance revision); Antigravity never releases. Claude
commits and pushes, then sets `STATE: COMPLETE` and appends the final
History Log row with the commit hash.)*

- **Commit:**
- **Pushed:**

---

## Continuity Notes

- If Gemma is unavailable mid-cycle: leave `STATE` at whatever it
  currently is (do not advance it), append a `WORKER_FAILED` or
  `WAITING_FOR_QUOTA` row noting the reason, and resume
  `IMPLEMENTING` from this same file once Gemma is available again.
  Antigravity does not implement in Gemma's place without an explicit,
  separately User-authorized fallback for this one instance.
- If Antigravity is unavailable: its audit gate is not bypassed. Hold
  at `WAITING_FOR_ANTIGRAVITY`.
- If Claude is unavailable or quota-exhausted after the plan is
  `ACCEPTED`: `IMPLEMENTING`/`AUDITING`/`FIXING` may proceed without
  Claude, but nothing advances to `VERIFIED` and no fresh next-milestone
  plan is drafted by anyone else. Hold at `WAITING_FOR_CLAUDE` once
  audit work is otherwise complete; Claude resumes verification directly
  from the GEMMA RETURN REPORT and ANTIGRAVITY AUDIT REPORT recorded
  above, not from conversation recall.
"""
        path.write_text(template, encoding="utf-8")
        return self.parse_content(template, path, milestone_id)

    def create_devtest_state(
        self,
        test_id: str,
        description: str = "Development tooling test fixture.",
    ) -> MilestoneStateRecord:
        """Create a development tooling test state record.

        Explicitly records:
        - TEST ONLY
        - NOT A URI MILESTONE
        - NO USER MILESTONE ACCEPTANCE
        - NO RELEASE AUTHORITY
        - NO COMMIT/PUSH
        """
        path = self.get_state_path(test_id)
        today = datetime.date.today().isoformat()

        template = f"""# DEVTEST: {test_id} — DEVELOPMENT TOOLING TEST ARTIFACT

> [!CAUTION]
> **TEST ONLY — NOT A URI MILESTONE**
> **NO USER MILESTONE ACCEPTANCE — NO RELEASE AUTHORITY — NO COMMIT/PUSH**
> This artifact is an automated test fixture for validating development tooling and bridge protocols.
> It must never be presented as an accepted production milestone or used for release.

---

## STATE: DRAFT

---

## History Log

| Timestamp | State | Actor | Note |
|---|---|---|---|
| {today} | DRAFT | ToolingTestFixture | Initial development tooling test fixture created ({description}). |

---

## Accepted Plan Reference

- **Plan file:** `NONE` (Development tooling test artifact only)
- **Plan version accepted:** NONE (NO USER MILESTONE ACCEPTANCE)
- **Baseline commit:** none
- **UI IMPACT:** NONE
"""
        path.write_text(template, encoding="utf-8")
        return self.parse_content(template, path, test_id)

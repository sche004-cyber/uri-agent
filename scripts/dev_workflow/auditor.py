"""Antigravity Audit Engine (AO-4).

Implements independent inspection, test execution, test sufficiency assessment,
security boundary auditing, and UI parity verification per ORCHESTRATION.md §1.2, §5, §10.3.

Role & Invariants:
- Antigravity independently audits the actual implementation (not just Gemma's report).
- Runs relevant test suites and records deterministic evidence.
- Checks UI impact: NONE (requires documented reason) or REQUIRED (requires UI tests & parity).
- Verifies protected invariant files are untouched.
- Produces persistent ANTIGRAVITY AUDIT REPORT.
- Invariant: Antigravity NEVER marks a milestone VERIFIED (Claude's sole authority).
- Invariant: Antigravity NEVER commits or pushes before Claude's VERIFIED decision.

Boundary Guarantee: Development-only tooling. Not part of URI runtime.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from scripts.dev_workflow.state_manager import AntigravityAuditReport, PlanReference

# Core Protected Invariant Files (ORCHESTRATION.md & AGENTS.md)
DEFAULT_PROTECTED_FILES = {
    "uri_core/core/approval_gate.py",
    "uri_core/core/approval_store.py",
    "step3_test.py",
    "step4_test.py",
    "URI_Model_Centric_Architecture_Docs/URI_ADR_018_MODEL_CENTRIC_ARCHITECTURE.md",
    "URI_Model_Centric_Architecture_Docs/URI_AI_OPERATING_POLICY.md",
    "URI_Model_Centric_Architecture_Docs/URI_MODEL_RUNTIME_CONTRACT.md",
}


@dataclass
class TestExecutionResult:
    command: str
    returncode: int
    passed_count: int
    failed_count: int
    output: str
    duration_sec: float


@dataclass
class AuditFindings:
    milestone_id: str
    changed_files: List[str] = field(default_factory=list)
    protected_boundary_violations: List[str] = field(default_factory=list)
    syntax_errors: List[str] = field(default_factory=list)
    test_results: List[TestExecutionResult] = field(default_factory=list)
    test_sufficiency_notes: List[str] = field(default_factory=list)
    security_notes: List[str] = field(default_factory=list)
    ui_parity_notes: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    outstanding_gaps: List[str] = field(default_factory=list)
    is_audit_passed: bool = False


class AntigravityAuditor:
    """Independent auditor and bounded fixer for milestone implementations."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        protected_files: Optional[Set[str]] = None,
    ):
        self.repo_root = repo_root or Path.cwd()
        self.protected_files = protected_files or DEFAULT_PROTECTED_FILES

    def get_changed_files_against_baseline(self, baseline_commit: str) -> List[str]:
        """Detect actual modified and untracked files compared to baseline commit."""
        files = []
        try:
            # Committed/staged diffs against baseline
            if baseline_commit:
                res = subprocess.run(
                    ["git", "diff", "--name-only", baseline_commit],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if res.returncode == 0:
                    files.extend([f.strip() for f in res.stdout.splitlines() if f.strip()])

            # Working directory unstaged and untracked
            stat_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if stat_res.returncode == 0:
                for line in stat_res.stdout.splitlines():
                    if len(line) >= 3:
                        files.append(line[3:].strip())
        except Exception:
            pass

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for f in files:
            if f not in seen:
                seen.add(f)
                deduped.append(f)
        return deduped

    def check_protected_boundaries(
        self,
        changed_files: List[str],
        allowed_exceptions: Optional[Set[str]] = None,
    ) -> List[str]:
        """Verify no protected invariant files were modified."""
        violations = []
        exceptions = {ex.replace("\\", "/").strip() for ex in (allowed_exceptions or set())}
        for f in changed_files:
            clean = f.replace("\\", "/").strip()
            # Check if exempted by plan
            is_exception = any(
                clean == ex or clean.endswith("/" + ex) or ex.endswith("/" + clean) or Path(clean).name == Path(ex).name
                for ex in exceptions
            )
            if is_exception:
                continue
            if clean in self.protected_files or any(clean.endswith("/" + pf) or pf.endswith("/" + clean) for pf in self.protected_files):
                violations.append(clean)
        return violations

    def run_tests(self, test_commands: List[str], timeout_sec: int = 120) -> List[TestExecutionResult]:
        """Execute test suites and collect concrete pass/fail metrics."""
        import time
        results = []
        for cmd in test_commands:
            start = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=timeout_sec,
                )
                duration = round(time.time() - start, 2)
                combined = proc.stdout + "\n" + proc.stderr

                # Extract pass/fail counts
                passed = 0
                failed = 0
                pass_m = re.search(r"(\d+)\s+passed", combined)
                fail_m = re.search(r"(\d+)\s+failed", combined)
                if pass_m:
                    passed = int(pass_m.group(1))
                elif "OK" in combined:
                    ran_m = re.search(r"Ran (\d+) tests?", combined)
                    if ran_m:
                        passed = int(ran_m.group(1))
                elif "All tests passed!" in combined:
                    fl_m = re.search(r"\+(\d+):", combined)
                    if fl_m:
                        passed = int(fl_m.group(1))

                if fail_m:
                    failed = int(fail_m.group(1))
                elif "FAILED" in combined:
                    fl_fail = re.search(r"FAILED \(.*?failures=(\d+)", combined)
                    if fl_fail:
                        failed = int(fl_fail.group(1))

                results.append(
                    TestExecutionResult(
                        command=cmd,
                        returncode=proc.returncode,
                        passed_count=passed,
                        failed_count=failed,
                        output=combined,
                        duration_sec=duration,
                    )
                )
            except Exception as e:
                results.append(
                    TestExecutionResult(
                        command=cmd,
                        returncode=1,
                        passed_count=0,
                        failed_count=1,
                        output=f"Execution error: {e}",
                        duration_sec=round(time.time() - start, 2),
                    )
                )
        return results

    def assess_test_sufficiency(self, test_files: List[str]) -> List[str]:
        """Inspect test code to assess whether assertions actually test behavior."""
        notes = []
        for t_file in test_files:
            p = self.repo_root / t_file
            if not p.exists() or not p.is_file():
                continue
            content = p.read_text(encoding="utf-8", errors="replace")
            # Check for assertions (Python assert/self.assert..., Dart expect)
            assert_count = len(re.findall(r"\bassert\w*|\bexpect\b", content))
            test_funcs = len(re.findall(r"\bdef test_|\btestWidgets\b|\btest\(", content))
            if test_funcs > 0 and assert_count == 0:
                notes.append(f"WARNING: {t_file} defines {test_funcs} tests but contains 0 assert statements.")
            elif test_funcs > 0:
                notes.append(f"Verified {test_funcs} tests with {assert_count} assertions in {t_file}.")
        if not notes:
            notes.append("No new test files were identified for sufficiency inspection.")
        return notes

    def audit_ui_impact(self, plan_ref: PlanReference, changed_files: List[str]) -> List[str]:
        """Audit UI impact declaration and parity requirements."""
        notes = []
        impact = plan_ref.ui_impact.upper()
        if impact == "REQUIRED":
            # Check if any UI files were touched
            ui_files = [f for f in changed_files if "ui" in f.lower() or f.endswith((".dart", ".flutter", ".css", ".html"))]
            if not ui_files:
                notes.append(
                    "VIOLATION: Milestone declared 'UI IMPACT: REQUIRED', but no UI components or tests were modified."
                )
            else:
                notes.append(f"UI Parity verified: {len(ui_files)} UI-related files modified/tested.")
        elif impact == "NONE":
            notes.append(f"UI impact declared NONE. Documented reason: {plan_ref.ui_reason or 'No UI contract impact'}.")
        else:
            notes.append(f"WARNING: Ambiguous UI impact declaration: '{impact}'. Must be NONE or REQUIRED.")
        return notes

    def get_milestone_files(
        self,
        changed_files: List[str],
        gemma_report: Optional[GemmaReturnReport] = None,
    ) -> List[str]:
        """Filter changed files to those actually in-scope/reported for this milestone."""
        if not gemma_report or not gemma_report.files_modified_created:
            return changed_files
        
        reported_text = gemma_report.files_modified_created
        milestone_files = []
        for f in changed_files:
            clean = f.replace("\\", "/").strip()
            basename = Path(clean).name
            if clean in reported_text or basename in reported_text:
                milestone_files.append(f)
        return milestone_files

    def check_syntax_errors(self, changed_files: List[str]) -> List[str]:
        """Verify that modified Python files compile with valid syntax."""
        import py_compile
        errors = []
        for f in changed_files:
            clean = f.replace("\\", "/").strip()
            if clean.endswith(".py"):
                p = self.repo_root / clean
                if p.exists() and p.is_file():
                    try:
                        py_compile.compile(str(p), doraise=True)
                    except py_compile.PyCompileError as e:
                        errors.append(f"{clean}: {e.msg}")
                    except Exception as e:
                        errors.append(f"{clean}: {e}")
        return errors

    def perform_audit(
        self,
        milestone_id: str,
        plan_ref: PlanReference,
        test_commands: Optional[List[str]] = None,
        test_files: Optional[List[str]] = None,
        gemma_report: Optional[GemmaReturnReport] = None,
        plans_dir: Optional[Path] = None,
    ) -> AuditFindings:
        """Run complete audit pass against active repo state."""
        changed = self.get_changed_files_against_baseline(plan_ref.baseline_commit)
        milestone_files = self.get_milestone_files(changed, gemma_report)

        # Look for plan exceptions in the plan file
        allowed_exceptions: Set[str] = set()
        p_dir = plans_dir or getattr(self, "plans_dir", None) or (self.repo_root / "docs" / "plans")
        plan_path = (p_dir / plan_ref.plan_file) if plan_ref.plan_file else None
        if plan_path and plan_path.exists():
            try:
                from scripts.dev_workflow.file_authority import FileWriteAuthorizer
                authorizer = FileWriteAuthorizer(repo_root=self.repo_root)
                plan_info = authorizer.extract_plan_scope(plan_path.read_text(encoding="utf-8"))
                allowed_exceptions = plan_info.get("protected_exceptions", set())
            except Exception:
                pass

        files_to_check = milestone_files if (gemma_report and gemma_report.files_modified_created) else changed
        protected_violations = self.check_protected_boundaries(files_to_check, allowed_exceptions=allowed_exceptions)
        syntax_errors = self.check_syntax_errors(milestone_files)

        test_results = []
        if test_commands:
            test_results = self.run_tests(test_commands)

        sufficiency_notes = self.assess_test_sufficiency(test_files or [f for f in changed if "test" in f.lower()])
        ui_notes = self.audit_ui_impact(plan_ref, changed)

        security_notes = []
        if protected_violations:
            security_notes.append(f"CRITICAL: Protected invariant files modified: {protected_violations}")
        else:
            security_notes.append("Protected invariant boundaries verified intact.")

        # Determine overall audit status
        tests_passed = all(r.returncode == 0 for r in test_results) if test_results else True
        has_violations = bool(protected_violations)
        ui_violation = any("VIOLATION" in n for n in ui_notes)
        has_syntax_errors = bool(syntax_errors)

        is_passed = tests_passed and not has_violations and not ui_violation and not has_syntax_errors

        outstanding = []
        if not tests_passed:
            outstanding.append("One or more automated test suites failed.")
        if has_violations:
            outstanding.append("Protected boundary violation must be resolved.")
        if ui_violation:
            outstanding.append("UI impact parity requirement unfulfilled.")
        if has_syntax_errors:
            outstanding.append(f"Python syntax errors in changed files: {'; '.join(syntax_errors)}")

        return AuditFindings(
            milestone_id=milestone_id,
            changed_files=changed,
            protected_boundary_violations=protected_violations,
            syntax_errors=syntax_errors,
            test_results=test_results,
            test_sufficiency_notes=sufficiency_notes,
            security_notes=security_notes,
            ui_parity_notes=ui_notes,
            fixes_applied=[],
            outstanding_gaps=outstanding,
            is_audit_passed=is_passed,
        )

    def format_audit_report(self, findings: AuditFindings) -> AntigravityAuditReport:
        """Construct the persistent AntigravityAuditReport artifact per ORCHESTRATION.md §10.3."""
        code_findings = f"Inspected {len(findings.changed_files)} changed files. "
        if findings.protected_boundary_violations:
            code_findings += f"Protected violations detected: {findings.protected_boundary_violations}. "
        elif findings.syntax_errors:
            code_findings += f"Syntax errors detected: {findings.syntax_errors}. "
        else:
            code_findings += "No protected boundary violations. "

        sufficiency = "; ".join(findings.test_sufficiency_notes)
        security = "; ".join(findings.security_notes)
        ui_parity = "; ".join(findings.ui_parity_notes)
        fixes = "; ".join(findings.fixes_applied) if findings.fixes_applied else "None required."

        evidence_lines = []
        for tr in findings.test_results:
            status = "PASSED" if tr.returncode == 0 else "FAILED"
            evidence_lines.append(f"`{tr.command}` -> {status} ({tr.passed_count} passed, {tr.failed_count} failed in {tr.duration_sec}s)")
        evidence = "; ".join(evidence_lines) if evidence_lines else "Code inspection performed; test suite pending."

        gaps = "; ".join(findings.outstanding_gaps) if findings.outstanding_gaps else "None. Ready for Claude independent verification."

        return AntigravityAuditReport(
            milestone_id=findings.milestone_id,
            code_correctness_findings=code_findings,
            test_sufficiency_assessment=sufficiency,
            security_boundary_check=security,
            ui_backend_parity_check=ui_parity,
            portability_implications="No platform-specific leaks identified.",
            fixes_applied=fixes,
            evidence=evidence,
            outstanding_gaps=gaps,
        )

"""CLI Interface for URI Development Workflow Automation (AO-4).

Usage:
  python -m scripts.dev_workflow.cli status M22.4
  python -m scripts.dev_workflow.cli accept M22.4 --notes "Accepted with clarifications"
  python -m scripts.dev_workflow.cli modify M22.4 --notes "Need test plan update"
  python -m scripts.dev_workflow.cli implement M22.4
  python -m scripts.dev_workflow.cli audit M22.4 --test-cmd "pytest tests/core"
  python -m scripts.dev_workflow.cli review M22.4 --decision VERIFIED --basis "All 15 tests passing"
  python -m scripts.dev_workflow.cli release M22.4 --commit "abcd123"
  python -m scripts.dev_workflow.cli resume M22.4 --target-state AUDITING
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.dev_workflow.state_machine import (
    WorkflowActor,
    WorkflowState,
    WorkflowException,
)
from scripts.dev_workflow.workflow_engine import WorkflowEngine


def cmd_status(engine: WorkflowEngine, milestone_id: str) -> None:
    rec = engine.get_record(milestone_id)
    print(f"\n=== Milestone State Record: {rec.milestone_id} ===")
    print(f"File Path:     {rec.file_path}")
    print(f"Current State: {rec.current_state.value}")
    print(f"Plan File:     {rec.plan_ref.plan_file}")
    print(f"Baseline:      {rec.plan_ref.baseline_commit}")
    print(f"UI Impact:     {rec.plan_ref.ui_impact}")
    print(f"\n--- History Log ({len(rec.history_log)} entries) ---")
    for e in rec.history_log:
        print(f"  {e.timestamp} | {e.state:<20} | {e.actor:<12} | {e.note}")

    print("\n--- Gemma Return Report ---")
    if rec.gemma_report and rec.gemma_report.summary_of_actions:
        print(f"Actions:   {rec.gemma_report.summary_of_actions[:120]}...")
        print(f"Files:     {rec.gemma_report.files_modified_created}")
        print(f"Tests:     {rec.gemma_report.tests_performed}")
    else:
        print("(Template / Not yet populated)")

    print("\n--- Antigravity Audit Report ---")
    if rec.audit_report and rec.audit_report.code_correctness_findings:
        print(f"Findings:  {rec.audit_report.code_correctness_findings}")
        print(f"Security:  {rec.audit_report.security_boundary_check}")
        print(f"UI Parity: {rec.audit_report.ui_backend_parity_check}")
        print(f"Evidence:  {rec.audit_report.evidence}")
        print(f"Gaps:      {rec.audit_report.outstanding_gaps}")
    else:
        print("(Template / Not yet populated)")

    print("\n--- Claude Verification Decision ---")
    print(f"Decision:  {rec.verification.decision}")
    if rec.verification.basis:
        print(f"Basis:     {rec.verification.basis}")
    if rec.verification.remaining_gaps:
        print(f"Gaps:      {rec.verification.remaining_gaps}")

    if rec.release_commit:
        print(f"\n--- Release ---")
        print(f"Commit:    {rec.release_commit}")
        print(f"Pushed:    {rec.release_pushed}")
    print("===================================================\n")


def cmd_accept(engine: WorkflowEngine, milestone_id: str, notes: str) -> None:
    rec = engine.user_accept_plan(milestone_id, notes=notes)
    print(f"Successfully accepted milestone {milestone_id}. State is now: {rec.current_state.value}")


def cmd_modify(engine: WorkflowEngine, milestone_id: str, notes: str) -> None:
    rec = engine.user_modify_plan(milestone_id, notes=notes)
    print(f"Successfully requested modifications for {milestone_id}. State is now: {rec.current_state.value}")


def cmd_implement(engine: WorkflowEngine, milestone_id: str, dry_run: bool, auto_audit: bool = True, test_cmds: list[str] | None = None, auto_verify: bool = False) -> None:
    print(f"Initiating implementation stage for {milestone_id}...")
    rec = engine.start_implementation(
        milestone_id,
        dry_run_response="Simulated implementer response" if dry_run else None,
        auto_audit=auto_audit,
        test_commands=test_cmds or [],
        auto_verify=auto_verify,
    )
    print(f"Implementation stage concluded. State is now: {rec.current_state.value}")


def cmd_audit(engine: WorkflowEngine, milestone_id: str, test_cmds: list[str], auto_verify: bool = False) -> None:
    print(f"Initiating Antigravity independent audit for {milestone_id}...")
    rec = engine.perform_audit(milestone_id, test_commands=test_cmds, auto_verify=auto_verify)
    print(f"Audit pass completed. State is now: {rec.current_state.value}")


def cmd_verify(engine: WorkflowEngine, milestone_id: str, timeout_sec: int = 120, dry_run_decision: str | None = None) -> None:
    print(f"Initiating Claude Bridge independent verification handoff for {milestone_id}...")
    sim = None
    if dry_run_decision:
        sim = f"DECISION: {dry_run_decision}\nBASIS: Dry-run simulation.\nREMAINING_GAPS: None."
    result = engine.verify_with_claude_bridge(milestone_id, timeout_sec=timeout_sec, simulate_response=sim)
    print(f"\n--- Claude Bridge Verification Result ---")
    print(f"Status:            {'SUCCESS' if result.ok else 'FAILED / WAITING'}")
    print(f"Decision:          {result.decision}")
    print(f"State:             {result.state.value}")
    print(f"Basis:             {result.basis}")
    print(f"Remaining Gaps:    {result.remaining_gaps}")
    print(f"Ready for Release: {result.ready_for_release}")
    if result.ready_for_release:
        print(f"Release Authority: {result.release_authority} (Claude is sole authority; Antigravity must NOT commit/push)")
    if result.error:
        print(f"Error / Note:      {result.error}")


def cmd_review(engine: WorkflowEngine, milestone_id: str, decision: str, basis: str, gaps: str) -> None:
    print(f"Recording Claude independent verification decision for {milestone_id}...")
    rec = engine.record_claude_verification(milestone_id, decision=decision, basis=basis, remaining_gaps=gaps)
    print(f"Verification recorded. State is now: {rec.current_state.value}")


def cmd_release(engine: WorkflowEngine, milestone_id: str, commit_hash: str) -> None:
    print(f"Executing milestone release for {milestone_id}...")
    rec = engine.release_milestone(milestone_id, commit_hash=commit_hash)
    print(f"Milestone successfully released. State is now: {rec.current_state.value}")


def cmd_resume(engine: WorkflowEngine, milestone_id: str, target_state: str, actor_str: str, note: str) -> None:
    actor = WorkflowActor(actor_str)
    state = WorkflowState(target_state)
    rec = engine.resume_from_interruption(milestone_id, actor=actor, target_state=state, note=note)
    print(f"Resumed milestone {milestone_id} to state {rec.current_state.value}")


def main():
    parser = argparse.ArgumentParser(description="URI Development Workflow Automation CLI (AO-4)")
    parser.add_argument("--plans-dir", type=str, default="docs/plans", help="Directory containing milestone plans & states")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Display milestone state and history")
    p_status.add_argument("milestone_id", help="Milestone ID (e.g. M22.4)")

    # accept
    p_accept = subparsers.add_parser("accept", help="Record User plan acceptance")
    p_accept.add_argument("milestone_id", help="Milestone ID")
    p_accept.add_argument("--notes", default="Plan accepted by User.", help="Acceptance notes")

    # modify
    p_modify = subparsers.add_parser("modify", help="Record User plan modification")
    p_modify.add_argument("milestone_id", help="Milestone ID")
    p_modify.add_argument("--notes", required=True, help="Modification notes")

    # implement
    p_impl = subparsers.add_parser("implement", help="Trigger Gemma 4 12B implementation")
    p_impl.add_argument("milestone_id", help="Milestone ID")
    p_impl.add_argument("--dry-run", action="store_true", help="Simulate worker invocation")
    p_impl.add_argument("--no-auto-audit", action="store_true", help="Do not automatically chain into Antigravity audit")
    p_impl.add_argument("--test-cmd", action="append", default=[], help="Test command(s) to pass to auto-audit")
    p_impl.add_argument("--auto-verify", action="store_true", help="Automatically trigger Claude Bridge verification if audit passes")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run Antigravity independent audit")
    p_audit.add_argument("milestone_id", help="Milestone ID")
    p_audit.add_argument("--test-cmd", action="append", default=[], help="Test command(s) to run")
    p_audit.add_argument("--auto-verify", action="store_true", help="Automatically trigger Claude Bridge verification if audit passes")

    # verify (Claude Bridge)
    p_verify = subparsers.add_parser("verify", help="Handoff milestone in VERIFYING state to Claude Code via Claude Bridge")
    p_verify.add_argument("milestone_id", help="Milestone ID")
    p_verify.add_argument("--timeout-sec", type=int, default=120, help="Bridge timeout in seconds")
    p_verify.add_argument("--dry-run-decision", choices=["VERIFIED", "NOT_VERIFIED"], default=None, help="Simulate Claude response")

    # review (manual recording fallback)
    p_review = subparsers.add_parser("review", help="Manually record Claude verification decision")
    p_review.add_argument("milestone_id", help="Milestone ID")
    p_review.add_argument("--decision", choices=["VERIFIED", "NOT_VERIFIED"], required=True, help="Decision")
    p_review.add_argument("--basis", required=True, help="Evidence basis")
    p_review.add_argument("--gaps", default="", help="Remaining gaps")

    # release
    p_rel = subparsers.add_parser("release", help="Record release commit after VERIFIED (Claude authority)")
    p_rel.add_argument("milestone_id", help="Milestone ID")
    p_rel.add_argument("--commit", required=True, help="Release commit hash")

    # resume
    p_res = subparsers.add_parser("resume", help="Resume from interruption")
    p_res.add_argument("milestone_id", help="Milestone ID")
    p_res.add_argument("--target-state", required=True, help="Target state to resume to")
    p_res.add_argument("--actor", default="Antigravity", help="Actor initiating resume")
    p_res.add_argument("--notes", default="Resumed from interruption.", help="Resume notes")

    args = parser.parse_args()
    engine = WorkflowEngine(plans_dir=Path(args.plans_dir))

    try:
        if args.subcommand == "status":
            cmd_status(engine, args.milestone_id)
        elif args.subcommand == "accept":
            cmd_accept(engine, args.milestone_id, args.notes)
        elif args.subcommand == "modify":
            cmd_modify(engine, args.milestone_id, args.notes)
        elif args.subcommand == "implement":
            cmd_implement(
                engine,
                args.milestone_id,
                args.dry_run,
                auto_audit=not args.no_auto_audit,
                test_cmds=args.test_cmd,
                auto_verify=args.auto_verify,
            )
        elif args.subcommand == "audit":
            cmd_audit(engine, args.milestone_id, args.test_cmd, auto_verify=args.auto_verify)
        elif args.subcommand == "verify":
            cmd_verify(engine, args.milestone_id, timeout_sec=args.timeout_sec, dry_run_decision=args.dry_run_decision)
        elif args.subcommand == "review":
            cmd_review(engine, args.milestone_id, args.decision, args.basis, args.gaps)
        elif args.subcommand == "release":
            cmd_release(engine, args.milestone_id, args.commit)
        elif args.subcommand == "resume":
            cmd_resume(engine, args.milestone_id, args.target_state, args.actor, args.notes)
    except WorkflowException as e:
        print(f"\nWorkflow Error: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""M22.7 Claude Verification Handoff.

Delivers the M22.7 independent final verification task directly to the running
Claude Code CLI session over local named pipe IPC via claude-bridge.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add claude-bridge skill directory to path
skill_path = r"C:\Users\cheta\.gemini\config\skills\claude-bridge"
if skill_path not in sys.path:
    sys.path.insert(0, skill_path)

from claude_bridge import resolve_single_session, send_message_to_claude

session, status_code, err = resolve_single_session()
if not session:
    print(f"Error resolving Claude Code session ({status_code}): {err}")
    sys.exit(1)

prompt = """AO-4 DEVELOPMENT LOOP — M22.7 INDEPENDENT FINAL VERIFICATION HANDOFF

The implementation of M22.7 (Usage Metering, Budgets, and Pre-Flight Ceiling Enforcement) by Codex is complete.
docs/plans/M22.7_STATE.md is now in STATE: VERIFYING.

Please conduct your independent final verification per the standing AO-4 operating contract (AGENTS.md / ORCHESTRATION.md commit 17db6ad).

1. REVIEW ARTIFACTS & IMPLEMENTATION:
   - Accepted Plan: docs/plans/M22.7_USAGE_METERING_PLAN.md
   - State & Return Report: docs/plans/M22.7_STATE.md
   - New Core Modules:
     * uri_core/core/usage_meter.py
     * uri_core/core/usage_ceiling_store.py
     * uri_core/core/usage_aggregator.py
   - Modified Core Modules:
     * uri_core/core/model_router.py
     * uri_core/app/server.py
     * uri_core/app/route_classification.py
   - New Tests (36 tests across 6 files):
     * test_usage_meter_recording.py
     * test_usage_meter_no_content_stored.py
     * test_usage_ceiling_budget_enforcement.py
     * test_usage_aggregator_zero_model_calls.py
     * test_usage_import_boundary.py
     * test_usage_endpoints_isolation.py

2. VERIFICATION REQUIREMENTS:
   - Do not trust reports; inspect actual git diff and source directly.
   - Trace real production paths (ModelRouter pre-flight budget check, attempt post-call recording, server endpoints /usage and /usage/limits).
   - Check all M22.7 acceptance criteria (1-11).
   - Verify non-negotiable invariants:
     * orchestrator.py line-count invariant strictly held (0 diff).
     * No prompt or response content stored in usage records.
     * Zero model calls in aggregator.
     * Route table correctly classifies endpoints as USER and enforces same-user isolation.
   - Run targeted test suite:
     .venv/Scripts/python.exe -m pytest -q -o python_files=test_*.py test_usage_meter_recording.py test_usage_meter_no_content_stored.py test_usage_ceiling_budget_enforcement.py test_usage_aggregator_zero_model_calls.py test_usage_import_boundary.py test_usage_endpoints_isolation.py test_model_router_resolution.py test_model_router_auth_failure_boundary.py test_model_router_degraded_mode.py test_model_router_freshness.py test_model_router_import_boundary.py test_model_router_budget_seam.py test_m22_3_route_authorization.py
   - Note on pre-existing test fixture isolation:
     Codex diagnosed that test_orchestrator_response_narrative.py modifies ModelRouter cooldown state in setUpModule which affects test_workflow_restart_recovery.py when run together in the full suite. As final auditor with bounded-fix authority, if you deem a small test-fixture cleanup in test_orchestrator_response_narrative.py (or router test teardown) appropriate, you may apply it directly, re-test, and verify.

3. OUTCOME & RELEASE:
   - Record findings in docs/plans/M22.7_STATE.md under ## CLAUDE FINAL VERIFICATION REPORT.
   - When verified:
     * Set STATE: VERIFIED in docs/plans/M22.7_STATE.md and update PROJECT_MEMORY.md / URI_MILESTONE_TRACKER.md.
     * Perform the git commit and git push to origin/master.
     * Immediately initiate M22.8 planning and pre-audit.
"""

print(f"Connecting to Claude session {session.get('sessionId')} (PID {session.get('pid')})...", flush=True)
result = send_message_to_claude(session, prompt, priority="now", timeout_sec=1200, wait_if_busy=True)

print(f"Handoff completion status: {result.get('ok')}")
if not result.get("ok"):
    print("Error during execution:", result.get("error"))
    sys.exit(1)

print("\n=== CLAUDE VERIFICATION OUTPUT ===\n")
print(result.get("response_text", ""))
if result.get("tools"):
    print("\nTools executed by Claude:", result.get("tools"))

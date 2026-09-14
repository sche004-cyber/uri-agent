# M30.6A State - Gmail Connection Truth Unification

**Plan:** `docs/plans/M30_6A_GMAIL_CONNECTION_TRUTH_UNIFICATION_PLAN.md`

STATE: LIVE_VERIFIED + CLAUDE ACCEPT

## Governance

Single-milestone remediation blocking M30.7 (per
`M30_6_CONTROLLED_CANONICAL_EXECUTION_REPORT.md` §16-17). Scope is
Gmail connection/availability truth unification only - M30.7 remains
BLOCKED and must not start from this milestone.

## History Log

- 2026-09-13: Codex implementation started against the accepted M30.6A
  plan. Scope remains limited to Gmail connection/availability truth
  unification; M30.7 remains blocked and is not started.
- 2026-09-13: Codex completed the scoped implementation and focused
  verification. The Gmail connection probe and direct live read path are
  verified; the canonical trace still reaches the existing runtime permission
  boundary, documented in `M30_6A_GMAIL_CONNECTION_TRUTH_REPORT.md`. Ready
  for the required independent audit; M30.7 remains blocked.
- 2026-09-13: Claude (Architect/Pre-Auditor role) traced the exact
  root-cause divergence across `GmailSearchService`, `GmailService`/
  `GmailCapability`, and `connection_status.py` directly from source
  (not assumed - each file read in full), designed the unification
  (a single non-interactive `ensure_connected_from_token()` on
  `GmailService`, plus a shared `google_auth_common.
  load_usable_credentials()` helper consolidating three duplicated
  token-parsing blocks), and produced the plan above. Marked ACCEPTED
  under the standing auto-approval rule (`ORCHESTRATION.md` §1.5) -
  routine engineering remediation of an already-disclosed gap, not a
  constitutional-boundary change. Awaiting Antigravity to route
  implementation to Codex per the standing AO-4 role assignment
  (Codex is the preferred worker for security-adjacent,
  production-call-path work as of the 2026-09-11 revision).
- 2026-09-13: Final live acceptance verification passed through the real
  authenticated `/ask` HTTP route. The production principal resolved to a
  populated user_id, the existing CapabilityGrantsStore/CapabilityResolver
  permitted gmail_search, and canonical Gmail `list_labels` execution reached
  READY, executed successfully against the real token, returned evidence to
  reasoning, and produced a grounded unread-count response. See
  `M30_6A_FINAL_LIVE_VERIFICATION.md`. M30.7 remains not authorized.
- 2026-09-13: Claude completed the independent audit of
  `M30_6A_FINAL_LIVE_VERIFICATION.md` and verified the real artifacts
  (`canonical_execution_log.jsonl`, `capability_grants.json`, `user_accounts.json`,
  usage logs). Revised verdict: ACCEPT. M30.6A is officially complete and accepted.
  M30.7 remains NOT AUTHORIZED until explicit User approval is communicated.

## Release gate

Per the 2026-09-12 live-verification-gate revision: Codex implements
against this plan; the User personally live-tests the result; only
after the User explicitly directs Claude to proceed does Claude
perform its own independent final audit and, if `VERIFIED`, the
release commit/push. Claude does not implement this milestone itself
and does not simulate Antigravity or Codex.

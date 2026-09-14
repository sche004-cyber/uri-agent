# M30.7C - Canonical Readiness Evidence Closure (Final Pass, Plan)

STATE: ACCEPTED (plan only) - implementation NOT yet performed. Claude
(Architect/Planner) output per the standing AO-4 development cycle, at
the User's explicit direct approval. Sibling state file:
`docs/plans/M30_7C_STATE.md`.

Scope authority: exactly the User's own verbatim approval, itself
directly derived from `docs/plans/M30_8_BLOCKER_DISPOSITION_PLAN.md`'s
own CLOSE NOW / DEFER / ACCEPT-AS-LIMITATION findings. Named M30.7C to
preserve the M30.7A/M30.7B lineage - this is a continuation of
canonical readiness evidence closure, not M30.8 itself.

---

## Scope (binding, exactly as approved - no expansion)

**MANDATORY:**
- **Scenario 2** - obtain a genuine canonical `DISCONNECTED` result
  using an invalid-but-present Gmail credential/token condition (the
  capability must remain discoverable so the flow reaches Gate 1 -
  the exact gap `M30_8_BLOCKER_DISPOSITION_PLAN.md` diagnosed in the
  prior, wrong fixture shape).
- **Scenario 8** - capture the already-successful `APPROVAL_REQUIRED`
  path with the required content-envelope evidence (the real drafted
  content, not only canonical telemetry fields).
- **Scenario 12** - execute and capture the **visible** canonical
  fallback behavior under a controlled, real provider-unavailable
  condition (the actual `/ask` response body/narrative, not only
  `fallback_reason: invalid_contract:unavailable` telemetry).

**BEST EFFORT:**
- **Scenario 7** - complete the real Gmail search → read → attachment
  chain only if a suitable real attachment-bearing message exists in
  the connected account. If none exists, document that fact plainly
  and retain the existing independent mechanism proof (M30.6's
  fake-double + M30.7B's real search half) - never fabricate Gmail
  data to force a pass.

**DO NOT REOPEN:** Scenario 5 (accepted documented limitation),
Scenario 9 (deferred capability-admission work), Scenario 4 (accepted
residual, closed since M30.7).

## Fixture guidance for Scenario 2 (specified precisely, since the
prior attempt's fixture shape was the confirmed root cause of its own
failure - do not repeat it)

Per `M30_8_BLOCKER_DISPOSITION_PLAN.md`'s own root-cause finding: the
prior attempt used an **empty** `URI_GOOGLE_CREDENTIALS_DIR`, which
made Gmail vanish from the Directory entirely (no `credentials.json`
at all) - the model then had nothing to propose, so the flow never
reached Gate 1's `DISCONNECTED` branch.

**Corrected approach:** continue using the existing, already-safe
`URI_GOOGLE_CREDENTIALS_DIR` isolation mechanism (never touch the real
`token.json`/`credentials.json` in the actual repo root), but populate
the isolated temp directory with:
1. A real copy of `credentials.json` (the OAuth client secret - not
   per-user-sensitive, already handled this way by `connection_
   status.py`/`GmailService` in normal operation) - so the Directory
   still lists Gmail as a real capability.
2. A deliberately invalid `token.json` in that same isolated
   directory - either a syntactically valid-but-expired token with no
   usable refresh token, or a corrupted/malformed one - so `GmailCapability.
   _availability()`/`GmailService.ensure_connected_from_token()`
   genuinely fails the connection check rather than never being asked.

This should make the Directory list Gmail (capability discoverable),
let the model propose it, and let Gate 1 actually evaluate and return
`DISCONNECTED` with the real connection-guidance message. Verify this
fixture shape produces the intended availability-check failure *before*
relying on it for the live `/ask` proof - if it does not, root-cause
the fixture again before a third attempt, per the same discipline
already applied twice this session.

## Evidence-capture requirement for Scenarios 8 and 12 (the specific
gap identified, not new work)

Both scenarios' underlying safety mechanisms are already proven live
(`APPROVAL_REQUIRED` reached twice for real; canonical `invalid_
contract:unavailable` refusal reached twice for real). The only gap is
capture methodology: prior attempts recorded only `canonical_
execution_log.jsonl` fields, which do not include response body
content. This pass must capture and quote the **actual `/ask` HTTP
response body** for one fresh call each - the real drafted content for
scenario 8, the real narrative/message text for scenario 12 - sanitized
per this session's own standing privacy discipline (no tokens,
credentials, or raw email content beyond what's needed to confirm the
scenario's own intent).

## Defect-handling protocol (binding, exact per User instruction)

**No production source changes are authorized under this milestone
unless an unexpected real defect is discovered during execution.** If
one is, **stop immediately and return for scope approval** - do not
repair automatically, do not silently expand write scope, do not
apply even a "small" fix without a new, explicit approval. This
applies even to the conditional scenario-12 template fix the
disposition plan flagged as a remote possibility - it remains
conditional and unapproved until and unless the evidence actually
shows a real problem, at which point work stops for approval rather
than proceeding.

## Required post-execution steps (binding, exactly as specified)

1. Verify each fresh run against `canonical_execution_log.jsonl` and
   any other relevant runtime evidence (session state, response
   bodies) - Codex's own report must cite specific, checkable
   artifacts, not summarized claims.
2. Run the required regression verification to a **real terminal
   state** - per this session's own hard-won lesson (a background run
   killed before completion must never be reported as a result): let
   it finish, observe the actual exit output, and report only that.
3. Rebuild the full 12-scenario readiness matrix (all 12, not only the
   ones touched this round - confirm 1, 3, 4, 6, 9, 10, 11 have not
   regressed).
4. Independently self-review the evidence before returning a verdict -
   binding on both Codex's own report and Claude's subsequent audit,
   per this repository's standing Verification-First Audit and
   Planning Standard (`CLAUDE.md`).

## Required final output

`docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_REPORT.md`, containing
the per-scenario evidence for 2/8/12 (mandatory) and 7 (best-effort,
with an honest "no suitable message found" disposition if applicable),
the rebuilt 12-scenario matrix, the regression comparison against the
known 1,726/8/0-new baseline, and **exactly one** readiness conclusion
line: **"M30.8 READY FOR USER APPROVAL"** or **"M30.8 NOT READY -
`<exact remaining blockers>`"** - no other conclusion is acceptable,
per the User's own instruction.

## Write scope

`docs/plans/M30_7C*`, `docs/governance/URI_ACTIVE_MILESTONE.md`,
`docs/governance/URI_AGENT_RELAY.md`. **No source file may be modified
under this milestone** unless a real defect is discovered and a
separate, explicit approval is subsequently given for its repair - not
pre-authorized here.

## Stop conditions

Do NOT start or implement M30.8. Do NOT make canonical execution
global. Do NOT retire legacy mechanisms. Do NOT touch `uri_ui/`. Do
NOT commit or push. Do NOT reopen scenarios 4, 5, or 9. Do NOT
fabricate Gmail data for scenario 7. Do NOT modify any real credential
file (`token.json`/`credentials.json` in the repo root) - all Gmail
fixture work stays inside an isolated `URI_GOOGLE_CREDENTIALS_DIR`. Do
NOT apply any source repair without stopping for a new, explicit
approval first, even if the defect appears small.

## Process note

Marked ACCEPTED under the standing auto-approval rule
(`ORCHESTRATION.md` §1.5) - this milestone's own scope was already
fully specified by the User directly, derived from Claude's own prior,
already-accepted disposition plan; no new architectural judgment is
being exercised here beyond faithfully recording that scope. Claude
does not implement or perform live verification itself; hands off to
Antigravity for routing to Codex. Claude will independently re-audit
the resulting report against real telemetry/session-state/response-
body artifacts before either readiness conclusion is treated as final
- exactly as for every prior milestone this session.

---

Stopping here. M30.7C plan is ready for Antigravity to route to Codex.
M30.8 is not started and not authorized.

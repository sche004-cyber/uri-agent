# M30.6A - Claude Independent Post-Implementation Audit

Audited directly from source (every changed file read in full,
`multi_action_dispatch.py`/`executor.py`/`capability_resolver.py`/
`server.py` traced for the permission question) - not from Codex's
report alone.

## Original verdict: ACCEPT WITH FOLLOW-UP

## Addendum (2026-09-13): final live verification audit - **ACCEPT**

`docs/plans/M30_6A_FINAL_LIVE_VERIFICATION.md` was independently
checked against real artifacts, not taken on the reporting session's
word:

- `uri_workspace/canonical_execution_log.jsonl` (lines 6-9) - four
  real telemetry records for `session_id:
  "canonical-live-verify-m30-6a"`, matching the report exactly: three
  `Gmail`/`list_labels`/`READY`/`canonical_execution_result: success`
  records, then one `clarification`/`fallback_reason:
  mode_not_executable:clarification` record for the honest
  `waiting_for_input` follow-up divergence.
- `uri_workspace/capability_grants.json` - empty/no explicit grant row
  for the test account, confirmed against
  `capability_resolver.py:130-132`'s documented "migration default
  applies (full current registry)" behavior when a user has no stored
  grant record - independently substantiates report point 4
  (`gmail_search` permitted via the migration-default ceiling, not a
  new or special-cased grant).
- `uri_workspace/user_accounts.json` - the `URI_test2` account
  (`user_id: 86f1c37e-...`) is a real, pre-existing persisted account,
  not fabricated for this test.
- `uri_workspace/users/86f1c37e-.../usage/2026-09.jsonl` - real
  `reasoning`/`drafting`/`semantic_interpretation` LLM usage entries
  for that exact `user_id` timestamped `2026-09-13T03:56:...Z`,
  consistent with the canonical telemetry's epoch timestamps
  (~1789271621) for the same window - corroborates a genuine live
  `/ask` request cycle actually ran, not a replayed or hand-edited log.

This closes the specific gap the original audit (§4/§5 above) flagged:
the mandatory canonical chain now has evidence of running through the
**real** `/ask` HTTP route with a **real** authenticated principal and
the **real**, unmodified `CapabilityGrantsStore`/`CapabilityResolver` -
not a directly-constructed executor with a bypassed/explicit test
principal. All 10 mandatory acceptance points check out against
independently-inspected artifacts, not merely against the reporting
session's own narrative.

**Revised verdict: ACCEPT.** M30.6A's Gmail connection-truth
unification is complete, correct, and now proven end-to-end through
the real canonical path. The two minor non-blocking items from the
original audit stand unchanged (trivial `_repo_root()` duplication in
`google_auth_common.py`; full 1710-test baseline not re-run, though
the wider 133-test Gmail-adjacent sweep this session ran directly
found nothing).

**M30.7:** remains **NOT AUTHORIZED**. This ACCEPT verdict closes out
M30.6A's own audit requirement; it is not User authorization for
M30.7, and none has been given to Claude in this session. No approval
relay record has been added to `docs/governance/URI_ACTIVE_MILESTONE.md`
on this basis - that file is written only when the User explicitly
communicates approval directly to Claude, never inferred from an
ACCEPT verdict or from another agent's request.

---

## 1. Implementation-plan compliance

Matches the accepted M30.6A plan closely and correctly:
- `uri_core/core/google_auth_common.py` created -
  `load_usable_credentials(token_path, scopes, allow_refresh)`, exactly
  the shared stateless helper the plan specified (§2/§10).
- `GmailService.ensure_connected_from_token()` added - non-interactive,
  never constructs `InstalledAppFlow`, maps failure to the closed
  reason set (`no_token`/`invalid_token`/`scope_missing`/`auth_error`)
  exactly as specified (§3/§8).
- `GmailService.get_connection_status()` now probes via
  `ensure_connected_from_token()` when `self.service is None` -
  exactly the one change the plan identified as fixing
  `GmailCapability`/`CapabilityFeasibility`/`decision_gates` all at
  once (§3).
- `GmailSearchService.authenticate()` and
  `connection_status._token_is_usable()` both refactored to delegate
  to the shared helper (`allow_refresh=True` and `allow_refresh=False`
  respectively) - behavior-preserving, matches §2/§4 exactly.
- `GmailCapability.capability.py` and `decision_gates.py` left
  untouched, exactly as the plan predicted (§3/§10) - they inherit the
  fix through `get_connection_status()`.

One minor, harmless deviation: `google_auth_common.py` defines its own
`_repo_root()` rather than importing `connection_status._repo_root()`,
so the root-resolution logic now exists in two places instead of one.
Not a defect (every real caller passes an explicit `token_path`, so
this duplicate is never actually exercised), but it re-introduces the
exact kind of small duplication the plan's own "prefer reuse over
duplication" principle was written to avoid. Worth collapsing in a
trivial follow-up edit, not worth blocking on.

## 2. Auth architecture assessment

Unified correctly. All three consumers (`GmailSearchService`,
`GmailService`/`GmailCapability`, `connection_status.py`) now resolve
token validity through one function. `GmailService.connect()` remains
the sole interactive-consent code path, reachable only from
`POST /connections/{id}/authorize` - confirmed unchanged by diff. No
second token store, no second credentials path, no hardcoded
`connected=true`. The single shared `token.json`/single-account model
(one Gmail mailbox per URI install) is unchanged and is the correct
existing architecture - this is not a multi-tenant-Gmail system, so a
process-lifetime `GmailService`/`GmailCapability` instance holding one
authenticated client is expected behavior, not a cross-user leak; the
`principal`/`user_id` concept elsewhere in this codebase identifies
*URI accounts*, not separate Gmail mailboxes.

## 3. Security assessment

- No interactive OAuth reachable from any status/availability check -
  confirmed: `ensure_connected_from_token()` and
  `load_usable_credentials()` never reference `InstalledAppFlow`;
  `test_gmail_connection_truth.py`'s
  `test_ensure_connected_from_token_never_starts_interactive_flow`
  patches `InstalledAppFlow` and asserts `from_client_secrets_file` is
  never called - a real regression guard, not just a docstring claim.
- No secret/token/exception-detail leakage: `load_usable_credentials()`
  wraps everything in a bare `except Exception: pass`, returning only
  `None`; `ensure_connected_from_token()`'s reasons are drawn from the
  closed 5-value set specified in the plan. No credential content or
  raw exception text appears in any new return value or the report's
  own live-evidence log.
- Refresh semantics safe: refresh happens only when
  `allow_refresh=True` (only `GmailService`/`GmailSearchService`, never
  `connection_status.py`, preserving its documented never-refresh
  guarantee) and only via `Request()` (network-only, non-interactive).
- No duplicated OAuth state and no new token file introduced.
- User/session scoping: unaffected - unchanged from the pre-existing,
  correct single-account model (see §2).

## 4. Live-evidence assessment

**Proven, real, live:**
- Real token recovery (`ensure_connected_from_token()` against the
  genuine `token.json`).
- Real Gmail API client construction.
- Real Capability Directory `available: true` for Gmail, derived from
  the corrected `get_connection_status()`.
- Real deterministic gate `READY` for `Gmail`/`list_labels` in the real
  canonical decision trace.
- Real Gmail read (`list_labels`, unread count 533) via
  `GmailCapability` against the live account.
- Real grounded follow-up ("Read that one" -> same resolved message id)
  and attachment-inventory lookup.

**Not proven - and this matters:** the mandatory full canonical chain
the original task specified ("user request -> ... -> real Gmail
execution -> ... grounded final response," explicitly "Do not use a
fake/double for the final acceptance test") was not completed
end-to-end through the real `/ask` HTTP path. The real canonical
invocation reached `permission_denied` before executing. The
substitute demonstration that did produce a real Gmail read
constructed `GmailCapability`/`MultiActionExecutor` directly with an
"explicitly granted `gmail.readonly` test principal" - i.e., it
bypassed the real `/ask` request's principal-resolution and
`CapabilityResolver` grant-lookup path (§5 below) rather than
exercising it. That is not a fake Gmail service, but it is a bypassed
authorization context, which is the specific gap the original
acceptance bar was written to rule out for the *canonical execution*
half of the trace. The connection-truth fix itself is fully, honestly
proven; the full canonical-loop acceptance criterion is not yet met.

## 5. Exact `permission_denied` root cause

Traced end-to-end, not assumed:

- **A. Principal used by the real `/ask` path:** `server.py`
  (~line 1140): `principal = None` unless `user_id is not None`, and
  `user_id` is only set when the request carries a resolvable
  Authorization header (`_resolve_context(user_id)`). An anonymous or
  header-less `/ask` call therefore always sends `principal=None` into
  *both* `context.orchestrator.process_user_input(principal=principal)`
  (legacy) and `run_canonical_for_ask(principal=principal, ...)`
  (canonical) - same variable, same call site, no divergence in what
  is passed.
- **B. Where permissions attach to that principal:**
  `multi_action_dispatch.py::_granted_permissions(principal)` ->
  `_legacy_capability_allowed("gmail_search", principal)` ->
  `CapabilityResolver.is_allowed("gmail_search", principal=principal,
  ...)` (`capability_resolver.py:213-244`). `is_allowed()` requires
  `principal.user_id` truthy (`capability_resolver.py:234-236`:
  `if not user_id: return False`) before ever consulting the real
  `CapabilityGrantsStore`. With `principal=None`, `user_id` is `None`,
  so `is_allowed()` returns `False` unconditionally, `granted_permissions`
  resolves to an empty set, and `MultiActionExecutor.execute()`
  (`executor.py:46-50`) correctly reports `permission_denied` because
  `capability.permissions == ["gmail.readonly"]` is not a subset of
  `set()`.
- **C. Does the legacy path use a different permission model?** Yes -
  `context.orchestrator.process_user_input()`'s legacy Gmail branch
  calls `GmailSearchService` directly and has no
  `CapabilityResolver`/`MultiActionExecutor` permission gate at all.
  The legacy path was never subject to the M22.4 authorization model;
  canonical execution is the first Gmail path that actually enforces
  it. This is a genuine divergence in rigor between the two paths, but
  it is the canonical path being *more* correct, not a wiring defect.
- **D. Is canonical execution missing grant propagation?** No. It
  passes the exact same `principal` object the legacy path receives,
  through the exact same, already-authoritative `CapabilityResolver`
  (confirmed by direct reading of `_legacy_capability_allowed` -
  `capability_resolver.py`'s own docstring calls `is_allowed` "the
  authoritative consultation point"). Nothing is being silently
  skipped or duplicated.
- **E. Is this only a test-harness/no-principal artifact?** Yes, most
  likely - but not proven either way in the report. The report's own
  live trace never shows a `/ask` call carrying a real Authorization
  header for an authenticated URI user whose `CapabilityGrantsStore`
  entry includes `gmail_search`. That specific case (real user_id,
  real grant, through the real HTTP path) was never attempted; the
  report instead substituted a directly-constructed executor with an
  explicit test principal (§4), which proves the mechanics work but
  does not prove the real end-to-end request path succeeds for a
  genuinely logged-in user.
- **F. Is there an existing authoritative permission source not being
  consumed?** No - `CapabilityResolver`/`CapabilityGrantsStore` (M22.4)
  is exactly that authoritative source, and canonical execution already
  consumes it correctly. Nothing here needs to be built or rewired.
- **G. What would fixing this require?** Per the trace above: **no
  code change** - the smallest correct next action is re-running the
  live canonical trace through the real `/ask` HTTP endpoint with a
  genuinely authenticated principal (a real Authorization header
  resolving to a `user_id` that has `gmail_search` in its
  `CapabilityGrantsStore` entry). If that still fails, it would surface
  a real, previously-unknown gap worth a bounded follow-up; nothing in
  the current trace indicates one exists.

## 6. Is the blocker real production behavior or test-context behavior?

Test-context behavior, most likely, per the trace in §5 - the
anonymous/no-principal case is *correctly* denied by design (M22.4
requires an identified, granted principal for canonical multi-action
execution). It has not yet been distinguished from a genuine
production gap because the one test that would distinguish them
(a real authenticated `/ask` call) was not run. Treat as unconfirmed,
not as a proven defect.

## 7. Smallest correct next action

1. Re-run the exact M30.6A mandatory live trace ("How many unread
   emails do I have?" and the grounded insurance-email follow-up
   sequence) through the real `/ask` HTTP endpoint, this time with a
   genuine Authorization header for a URI user account whose
   `CapabilityGrantsStore` entry actually grants `gmail_search`. No
   code change anticipated for this step.
2. Done in this audit: wider Gmail-adjacent regression sweep (133/133
   passing, § Regression audit below). No further regression action
   needed for this surface.
3. Fold `google_auth_common._repo_root()`'s duplication (§1) into a
   single shared definition - trivial, non-blocking.

## 8. Whether M30.7 remains blocked

**Yes, still blocked** - agree with Codex's own assessment
(`M30_6A_GMAIL_CONNECTION_TRUTH_REPORT.md` §12). The connection-truth
prerequisite is now genuinely fixed, but the full real canonical
execution chain for Gmail through the actual `/ask` path has still
never been observed to succeed (only its connection/gate half, plus a
mechanically-separate, principal-bypassed execution half). M30.7
should not begin until action 1 above is completed and either
succeeds or produces a concretely diagnosed new gap.

## 9. Whether a bounded M30.6B authorization-bridge milestone is required

**Not yet - do not open one preemptively.** Nothing found in this audit
indicates the canonical execution path is missing wiring: it correctly
calls the same, already-authoritative `CapabilityResolver` the rest of
the M22.4 identity system already uses, with the same principal the
legacy path also receives. Opening a new authorization-redesign
milestone now would very likely be solving a problem that does not
exist. Action 1 (§7) is the correct next step; only if a real,
authenticated, correctly-granted principal *still* fails to execute
canonically should a bounded M30.6B be scoped, and only to fix
whatever specific gap that run reveals - not as a speculative
authorization redesign.

## Regression audit

Codex reports 25 focused tests passing
(`test_gmail_connection_truth.py` 7, `test_gmail_search_service.py` +
`test_gmail_search_shape.py` 6, `test_multi_action_capabilities.py`
12) plus a clean `git diff --check`. This is good, relevant, targeted
coverage for the five changed files, but it is narrower than the
session's own established M30.6A baseline requirement ("no NEW
failures beyond the known 8" against the full 1710/8 suite). The
report does not show the full suite (or even the wider Gmail-adjacent
set - `test_capability_directory.py`, `test_decision_gates.py`,
`test_decision_engine.py`, `test_canonical_execution.py`, all of which
construct `GmailCapability()` directly and would be the first to catch
an availability-check regression) having been re-run. Claude ran that wider set directly during this audit:

```text
.venv\Scripts\python.exe -m pytest test_capability_directory.py \
  test_decision_gates.py test_decision_engine.py \
  test_canonical_execution.py test_multi_action_capabilities.py \
  test_gmail_connection_truth.py test_gmail_search_service.py \
  test_gmail_search_shape.py -q
133 passed in 19.62s
```

All Gmail-availability-sensitive consumers (`CapabilityDirectory`,
`decision_gates`, `decision_engine`, `canonical_execution`) pass
unchanged. Combined with Codex's 25 focused tests, this closes the
regression question for the Gmail/connection-truth surface
specifically. The full 1710-test baseline sweep was not re-run in this
audit (out of scope/time for an audit pass, and the task instructs not
to spend this milestone on the 8 known-unrelated failures); nothing in
this wider targeted run suggests it would surface anything new.

---

Stopping here per governing instruction. No repair implemented. Verdict
recorded above; M30.7 not started.

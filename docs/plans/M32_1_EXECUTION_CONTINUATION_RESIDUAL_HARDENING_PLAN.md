# M32.1 — Execution Continuation Residual Hardening

Frozen Implementation Blueprint. Status: ACCEPTED (standing AO-4
default-auto-approval for routine engineering decisions cited
explicitly per `uri-ao4-development-cycle` governance — routine,
reversible, bounded scope, no architectural/security-boundary change).

From clean HEAD `1b7d8d8`. Scope: strictly the carried-forward
residual named in the M32 closure register — durable resumed approval
across turns. Nothing else.

## Goal

When URI returns an approval-required action, a later user message
such as "yes", "approve", or "go ahead" must resume the correct
pending action safely and deterministically across turns.

## Root-cause investigation (pre-implementation inspection)

Inspected, before any edit: `ApprovalStore`/`ApprovalGate`, pending-
action state, `/ask` flow, `M30.7` workflow_continuation logic,
`canonical_execution.py`, the audit trail, and the real
`capabilities_registry.json`.

Found **two separate, independent "approval required" signal paths**,
neither of them durable through canonical execution:

1. `decision_gates.evaluate_gates()`'s advisory `GateResult(outcome=
   "APPROVAL_REQUIRED")`. This module's own docstring states "Nothing
   in this module executes anything" — it is a judgment, not state.
2. `MultiActionExecutor.execute()`'s stateless, per-call boolean gate
   (`user_approved`/`admin_approved`, both default `False`). Nothing
   about a rejected/approval-required call is persisted anywhere; the
   very next call starts from a clean slate.

Cross-checked against the real capability registry: the **only**
production capabilities that ever require approval are `gmail_
create_draft` and `drive_upload`, both multi-action (Gmail-shaped). No
legacy single-capability tool requires approval. This means a fix that
only handles the legacy `remember_fact`-style path would have **zero**
real-world effect — the Gmail bridge is the actual core of this
milestone, not an optional extra.

`ApprovalStore` itself (`uri_core/core/approval_store.py`) already
existed as a durable, file-backed, session-bound, single-use-consume,
TTL-expiring (15 min), fail-closed proposal store for `ProposedAction`
records — built for the legacy `remember_fact` approval path via
`ApprovalGate`. It was never wired to the Gmail path at all.

Also found: `dispatch_explicit()`/`dispatch_chain_explicit()` in
`multi_action_dispatch.py` already accept and thread `user_approved`/
`admin_approved` kwargs — an existing, deliberately-unwired "explicit
approval-resume integration" seam per its own docstring. Reused rather
than reinvented. Confirmed `_bind_context()`'s idempotency is safe for
re-dispatch: explicit stored inputs from `ProposedAction.arguments`
always win over freshly-grounded context from a later turn's text, so
replaying turn 1's exact bound inputs on turn 2/3 cannot be
contaminated by the confirmation text itself ("yes").

## Design

1. **Extend `ProposedAction`** with an optional `action_name` field —
   `None` for a legacy single-tool proposal (where `capability_id`
   already names the tool, unchanged meaning, zero behavior change for
   every existing record/caller), set to the real action (e.g.
   `"create_draft"`) for a multi-action proposal, where `capability_id`
   ("Gmail") and the action are genuinely different names.

2. **Bridge the Gmail single-action approval-required outcome to a
   real, durable `ApprovalStore.propose()` call**, inside
   `canonical_execution.py`'s `_execute_gmail()`, via a new
   `_propose_durable_gmail_approval()` helper. Uses the SAME
   `ApprovalStore` instance `ApprovalGate` already owns — never a
   second, parallel store. Never raises; returns `None` on any
   failure, in which case behavior is unchanged from today (approval-
   required but with no resumable `action_id`, matching current
   behavior exactly as a safe fallback).

3. **New module `approval_resumption.py`**: classifies a later
   message as a clear confirmation/rejection/neither (conservative,
   whole-message match only — never a substring inside a longer
   sentence); finds this session's pending actions; resumes the
   single unambiguous one via the SAME already-tested entry points
   (`ApprovalGate.decide()` for the legacy shape, `ApprovalStore.
   consume()` + `MultiActionDispatch.dispatch_explicit(...,
   user_approved=True)` for the Gmail shape, consume-before-dispatch
   to match `ApprovalGate.decide()`'s own existing ordering exactly).
   Returns `None` whenever resumption does not clearly apply — the
   same "None means fall back" convention every other M32-era seam in
   this codebase already follows.

4. **Wire into `/ask`** as an isolated, default-off, exception-safe
   early check, before the existing M30.7 workflow_continuation block.

5. **Security correctness**: `canonical_execution.py`'s dispatch
   condition and `decide_fallback_reason()` must both be widened
   together to admit `APPROVAL_REQUIRED` alongside `READY` — widening
   only the dispatch condition without also widening the fallback-
   reason check would silently skip the allowlist/killswitch check for
   every approval-required capability.

## Non-goals (explicitly out of scope)

- Multi-step chain approval resumption (`dispatch_chain_explicit`) —
  only the single-action Gmail branch is bridged. A pending chain
  approval is unaffected by this milestone (unchanged: still not
  durably resumable).
- Any change to `decision_gates.py`'s gate logic itself, or to
  `ApprovalStore`'s expiry/consumption semantics.
- Any new authorization boundary — resumption must reuse existing,
  already-audited decide/dispatch calls only, never invent its own.

## Acceptance criteria (mirrors the User's 10-point kickoff list)

1. Inspection completed before editing (see Root-cause investigation
   above).
2. Minimum durable continuation state defined and persisted:
   `ProposedAction.action_name` plus reuse of all pre-existing
   `ProposedAction` fields (`action_id`, `capability_id`, `session_id`,
   `arguments`, expiry).
3. Never infer/resume when 2+ pending approvals exist for a session —
   deterministic `clarification_required` envelope naming each one.
4. Per-session isolation preserved — resumption filters by exact
   `session_id` match only, never a prefix or "no session recorded".
5. Grants/permissions/evidence/audit/dispatch/idempotency/canonical-
   execution boundaries preserved — no new parallel state, no new
   dispatch mechanism, `_bind_context()` idempotency reused as-is.
6. Resumption never bypasses original authorization checks — routes
   through the exact same `decide()`/`consume()`+`dispatch_explicit()`
   calls a fresh approval would use, live-verified with a real
   `action_id` in `approval_store.list_pending()`.
7. Expiry, cancellation, duplicate approval, stale action IDs,
   restart/recovery, and ambiguous natural-language confirmation all
   handled safely — each proven by a dedicated test scenario.
8. Focused tests plus live multi-turn evidence for all 6 named
   scenarios — see M32.1 completion report.
9. Regression coverage run — see M32.1 completion report.
10. Completion report produced with exact files changed, test
    evidence, live evidence, residual risks, and READY/NOT READY
    verdict.

## History log

- Drafted and marked ACCEPTED under the standing AO-4 default-auto-
  approval rule (routine, reversible, bounded-scope engineering
  decision; no change to URI's core project structure, product
  identity, or security/authority model) — proceeded DRAFT → ACCEPTED
  without waiting for explicit User ACCEPT, per
  `uri-ao4-development-cycle` §1.5.
- 2026-09-18: this file was accidentally overwritten with a
  placeholder mid-session by a stray `Write` call while drafting the
  separate completion report, then reconstructed in place from the
  design already recorded in the session's own working context.
  Recorded here per this repository's auditable-correction-history
  convention rather than silently treated as if it never happened. No
  design content changed as a result — the reconstruction reflects the
  same root-cause investigation, design, non-goals, and acceptance
  criteria the implementation was actually built against.

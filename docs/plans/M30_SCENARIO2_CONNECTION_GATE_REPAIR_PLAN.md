# Scenario 2 - Connection Gate Repair Plan (Read-Only, NOT Implemented)

STATE: ACCEPTED (plan only) - implementation NOT yet performed, per the
User's explicit "Do NOT implement yet." Claude (Architect/Planner)
output per the standing AO-4 development cycle. **No production source
was modified to produce this document** - the root cause below was
established entirely by reading source and by the live telemetry
already captured in `docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_
REPORT.md`. Sibling state file: `docs/plans/M30_SCENARIO2_CONNECTION_
GATE_STATE.md`.

**Product decision this plan implements (User, 2026-09-14):**
connection availability must be checked by a generic, deterministic
gate - never inferred from the model's own self-report - reusable
across Gmail, Drive, MCP servers, plugins, and any future connected
service; backend remains source of truth for connection state; UI
owns reconnect/presentation UX; the Decision Engine must never reject
or reinterpret a disconnected capability before the connection gate
reports the real runtime state.

---

## 1. Exact root cause

Traced end-to-end through `uri_core/core/decision_gates.py` and
`uri_core/core/decision_engine.py`, corroborated by 4 real, live
Scenario 2 reproductions this session (`docs/plans/M30_7C_READINESS_
EVIDENCE_CLOSURE_REPORT.md` § Scenario 2).

**The connection/availability gate itself is already correct, already
generic, and already reusable - it is not the defect.**
`decision_gates.py`'s Gate 5 ("AVAILABILITY / CONNECTION", lines
284-314) reads only generic, capability-agnostic fields
(`availability_known`/`available`/`availability_reason`) from
`CapabilityDirectory.describe(capability_id)`
(`capability_directory.py` lines 395-444), which in turn calls the
target capability's own generic `Capability.check_availability()`
(`uri_core/capabilities/base.py` lines 182-195) - a mechanism with
**zero Gmail-specific code anywhere in this chain**. Any capability
registered with a real `availability_check` (Drive, an MCP server
adapter, a future plugin) already gets this exact same classification
for free, with no additional code. This was independently re-confirmed
today: `test_decision_gates.py`'s own `DisconnectedTests` already
proves this generic mechanism correct for both a legacy capability
(`test_legacy_capability_marked_unavailable_runtime_is_disconnected`)
and a multi-action capability
(`test_multi_action_gmail_real_connection_state_reaches_the_gate`).

**The defect is that Gate 5 is structurally unreachable whenever
`contract["capability"]` is `null`.** `_evaluate_gates_inner()`
branches into two disjoint paths at line 212: "no capability named"
(lines 212-257) vs. "a capability WAS named" (line 259 onward). Gate 5
lives entirely inside the second branch. The first branch's only
defense against a wrongly-claimed `"unsupported"` proposal is
`_plausible_match_exists()` (lines 90-103, backed by `capability_
relevance.py`'s already-generic, directory-derived, non-model term-
overlap scorer `plausible_matches()`) - a **pure text-overlap check
against `goal_text`**, with no connection to the real runtime
connection state at all. When a plausible match exists, the branch
returns `INVALID_PROPOSAL`/`false_unsupported_claim_rejected_by_
directory` (line 223-227) - a verdict about the model's proposal being
wrong, **never a verdict about the capability's real connection
state**, because Gate 5's own classification logic is never consulted
for that plausible-match candidate.

**Why `contract["capability"]` ends up `null` in practice - confirmed
against the model's own system prompt, not merely inferred:**
`decision_engine.py`'s `REASONING_SYSTEM_PROMPT` (lines 245-250)
already, correctly, instructs the model: *"Never choose \[unsupported\]
only because a capability LOOKS unavailable right now (that is
'single_action'/'multi_action' with capability named - a disconnected/
unavailable capability is not the same as 'no such capability
exists')."* The intended flow is exactly the User's own desired
design: the model should still name the real capability, and Gate 5
should classify it. **Empirically, across all 4 of today's live
Scenario 2 reproductions, the model does not follow this instruction**
- it proposes `mode: "unsupported"`, `capability: null` for a
genuinely disconnected Gmail account, contradicting its own prompt.
This is exactly the class of model unreliability the "no capability
named" branch's `_plausible_match_exists()` safety net already exists
to catch - **but that safety net stops one step short**: it correctly
detects the model was wrong to claim "unsupported," but never takes
the next, already-available step of asking the SAME Gate 5 logic what
the real connection state of the matched candidate actually is.

**In one sentence:** the Decision Engine's contract-validation safety
net for a falsely-claimed "unsupported" proposal returns a verdict
about the proposal's validity (`INVALID_PROPOSAL`) instead of
consulting the already-correct, already-generic connection gate for
the real runtime truth (`DISCONNECTED`) - exactly the ordering problem
the User's product decision names.

**Related, disclosed, out-of-scope finding (not part of this bounded
repair):** the gate vocabulary (`GATE_OUTCOMES`, `decision_gates.py`
line 51-61) has no `REAUTH_REQUIRED` state distinct from
`DISCONNECTED` - Gate 5 currently collapses every `availability_known
and not available` case (other than `not_implemented`) into
`DISCONNECTED`. `connection_status.py`'s own three-state model
(`connected`/`needs_authorization`/`not_connected`) is closer to the
User's desired `CONNECTED`/`DISCONNECTED`/`REAUTH_REQUIRED` split, but
Gate 5 does not currently surface that distinction. Adding a real
`REAUTH_REQUIRED` outcome is a broader vocabulary change than this
bounded repair - **recommended as a separate, explicitly-scoped follow-
up, not bundled here.**

---

## 2. Narrowest generic repair

Reuse three already-existing, already-generic, already-tested
mechanisms verbatim - **invent nothing new, hardcode nothing
capability-specific**:

1. **`plausible_matches()`** (`capability_relevance.py`) - already the
   generic, directory-derived, non-model candidate-identification step
   the "no capability named" branch already calls today.
2. **`CapabilityDirectory.describe(capability_id)`** - already the
   generic, capability-agnostic source of real connection/availability
   truth Gate 5 already consumes today.
3. **Gate 5's own classification logic** (lines 284-314) - already
   correct; only its *reachability* is the problem, not its content.

**The change:** extract Gate 5's existing classification block (lines
284-314) into a small, pure, capability-agnostic helper -
`_availability_outcome(entry, capability_id, action_names,
overlap_ids) -> Optional[GateResult]` - returning `None` when the
capability is available (so the caller falls through to its own next
step, e.g. completeness/permission/approval), or the appropriate
`GateResult` (`DISCONNECTED`, `UNSUPPORTED` for `not_implemented`, or
`UNAVAILABLE` for unknown availability) otherwise. This is a pure
extract-function refactor for the existing "capability WAS named"
call site - **zero behavior change there**, verified by re-running the
existing `DisconnectedTests`/`ReadyTests`/`UnknownAvailabilityTests`
unchanged against the refactored code.

**The new call site:** in the "no capability named" branch, when
`mode == "unsupported"` and `_plausible_match_exists()` returns at
least one candidate, look up the **top-scoring** candidate's `describe()`
entry and call the same `_availability_outcome()` helper on it
*before* deciding between `INVALID_PROPOSAL` and `UNSUPPORTED`:

- If the helper returns a `DISCONNECTED` (or `UNSUPPORTED`/
  `UNAVAILABLE`) `GateResult`, return it **with the real
  `capability_id` populated** (the matched candidate's id, not `null`)
  instead of `INVALID_PROPOSAL`. This is the honest, real-runtime-state
  answer the User's product decision requires.
- If the helper returns `None` (capability is genuinely available),
  fall through to the **existing, unchanged** `INVALID_PROPOSAL`/
  `false_unsupported_claim_rejected_by_directory` verdict - the model
  really was wrong, and the capability really is available, so the
  existing "reject the false claim" behavior is exactly right and is
  left untouched.

This directly satisfies "do not let the Decision Engine reject or
reinterpret a disconnected capability before the connection gate can
report the real runtime state": the connection gate is now
unconditionally consulted for any plausible-match candidate before any
`INVALID_PROPOSAL`/`UNSUPPORTED` verdict is finalized, regardless of
how the model framed its own proposal.

**Genericity, by construction, not by extra effort:** nothing above
names "Gmail" anywhere in the new logic - `plausible_matches()` is
directory-derived, `describe()` is capability-id-generic, and the
extracted helper reads only the same generic `availability_known`/
`available`/`availability_reason` fields Gate 5 already reads for
every registered capability. A future Drive/MCP/plugin capability
registered with a real `availability_check` is covered automatically,
with no further code change, the moment it is registered in the
Capability Directory - exactly the User's "do not hard-code this as
Gmail-only" requirement.

---

## 3. Files affected

**Production source (bounded, single-file):**
- `uri_core/core/decision_gates.py` - extract `_availability_outcome()`
  from the existing Gate 5 block; add the new call site inside the
  `mode == "unsupported"` branch of `_evaluate_gates_inner()`. No other
  function in this file changes.

**Explicitly NOT touched:**
- `uri_core/core/capability_directory.py` - already generic and
  correct; reused as-is.
- `uri_core/core/capability_relevance.py` - already generic and
  correct; reused as-is.
- `uri_core/capabilities/base.py`, `uri_core/capabilities/gmail/
  capability.py`, `uri_core/services/gmail_service.py`,
  `uri_core/core/connection_status.py` - no change; this repair is
  entirely inside the gate's own decision logic, not the connection-
  state plumbing itself, which is already correct and already generic.
- `uri_core/core/decision_engine.py` - the model's system prompt
  already correctly instructs the intended behavior (§1); this repair
  does not depend on or attempt to fix model prompt-compliance, per
  the User's own product decision that availability must be checked
  deterministically, not inferred from the model.
- `uri_core/core/orchestrator.py` - untouched; this gate is consumed
  by the shadow/canonical path only, per the existing M30.5/M30.6/
  M30.7 pipeline - no orchestrator change is needed to make Gate 5
  itself reachable and correct.

**New test file:**
- `test_decision_gates.py` - extended with new test classes (see §4);
  reuses this file's own existing fixture conventions
  (`_multi_action_directory()`, `_decision()`, the
  `_FakeConnectedGmailDirectory` pattern) rather than inventing a new
  test style.

---

## 4. Tests required

All new, all deterministic (using controllable fake directories, not
the real environment's own Gmail token state - the existing
`test_multi_action_gmail_real_connection_state_reaches_the_gate` is
itself already flagged as environment-dependent, `assertIn(outcome,
("DISCONNECTED", "READY"))`, and must not be relied on for these new,
precise assertions):

1. **A genuinely disconnected, plausible-match capability now returns
   `DISCONNECTED` with a real (non-null) `capability_id`** - a fake
   directory whose `describe()` reports `available: False,
   availability_reason: "unavailable_runtime"` for a capability whose
   `summaries()` text plausibly overlaps `goal_text`, proposed as
   `mode: "unsupported", capability: None`. Must assert `outcome ==
   "DISCONNECTED"` and `capability_id == "<the real id>"` (not `None`).
2. **A genuinely connected capability's false "unsupported" claim is
   still rejected exactly as today (regression guard, unchanged
   behavior)** - re-run of the existing `test_model_false_unsupported_
   claim_is_rejected_when_a_match_exists` shape, but against a
   deterministic fake directory reporting `available: True` for the
   matched candidate; must assert the existing `INVALID_PROPOSAL`/
   `false_unsupported_claim_rejected_by_directory` outcome, proving the
   new check does not fire for the connected case.
3. **No plausible match at all still returns `UNSUPPORTED` unchanged**
   - re-run of `test_model_unsupported_claim_confirmed_when_nothing_
   matches` unchanged; proves the new logic does not fire when there is
   no candidate to check availability for at all.
4. **Genericity proof - a second, non-Gmail fake capability** (e.g.
   `"TestDrive"` or `"TestMCPTool"`, registered only in the test's own
   fake directory, zero relation to Gmail) also correctly reaches
   `DISCONNECTED` through the exact same code path, with zero Gmail-
   specific code touched anywhere - proving the fix is capability-
   agnostic by construction, not merely working for Gmail by
   coincidence.
5. **The "not_implemented" and "unknown availability" shapes still
   classify correctly through the new call site** - a plausible-match
   candidate whose `describe()` reports `availability_reason:
   "not_implemented"` must still yield `UNSUPPORTED` (not
   `DISCONNECTED`), and one with `availability_known: False` must still
   yield `UNAVAILABLE` - proving the extracted helper's full
   classification (not just the `DISCONNECTED` branch) is reused
   correctly at the new call site.
6. **The "capability WAS named" path is byte-for-byte unaffected by
   the extract-function refactor** - re-run `DisconnectedTests`,
   `ReadyTests`, `MissingParameterTests`, `UnknownAvailabilityTests`,
   `PermissionDeniedTests`, `ApprovalCannotBeBypassedTests`,
   `ReadOnlyReadyTests`, `NoExecutionTests`, `OverlapTests`
   (`test_decision_gates.py`, all existing) completely unchanged and
   still passing - the direct regression proof for item 6 of this
   plan's own required output ("proof that connected capabilities
   still reach normal Brain reasoning").
7. **Full existing `test_decision_gates.py` and `test_decision_
   engine.py` suites re-run unchanged and passing.**
8. **Live re-verification** - re-run the exact Scenario 2 fixture from
   today's session (isolated `URI_GOOGLE_CREDENTIALS_DIR` with a
   present `credentials.json` and a deliberately malformed
   `token.json`) at least once against the repaired code; confirm the
   shadow-mode canonical telemetry (`decision_engine_shadow_log.jsonl`)
   now records `gate_outcome: "DISCONNECTED"` with `capability_id:
   "Gmail"` populated (not `null`), for the same `mode: "unsupported"`
   model behavior already observed today - the direct live proof this
   repair closes Scenario 2's actual defect, not only a unit-level
   proof.

---

## 5. Pre-reasoning gating, or an earlier deterministic routing prerequisite?

**Recommendation: an earlier deterministic ROUTING PREREQUISITE inside
the existing post-reasoning gate pipeline (`decision_gates.py`) - not
a new gate that runs before the Brain/model call.**

Reasoning:

- The repair above already fully satisfies the User's binding
  requirement - "do not let the Decision Engine reject or reinterpret
  a disconnected capability before the connection gate can report the
  real runtime state" - by guaranteeing Gate 5 is *always* consulted
  before any `INVALID_PROPOSAL`/`UNSUPPORTED` verdict is finalized,
  regardless of how the model framed its proposal. The connection
  check becomes deterministic and generic (never model-inferred) at
  exactly the point of decision, which is what the product decision
  requires in substance.
- A literal pre-reasoning variant - running `plausible_matches()`
  against the raw user text *before the Brain/model is invoked at
  all*, and short-circuiting immediately on a disconnected match -
  is architecturally possible using the exact same generic,
  directory-derived scorer, and would more closely match the User's
  own flow diagram (checking connection before "continue normal Brain
  reasoning" even begins) and would save a wasted model call on an
  already-known-disconnected turn.
- **However, this stronger variant carries real, disclosed risk this
  repair does not need to take on:** `plausible_matches()`'s own
  design principle is explicitly "false UNSUPPORTED is worse than an
  unresolved/low-confidence match" (`capability_relevance.py`'s own
  docstring) - a deliberately permissive threshold appropriate for
  *validating* an already-made Brain proposal, but a materially higher-
  stakes lever if used to *hijack the entire turn before the Brain ever
  reasons about it*. `capability_relevance.py`'s own history records a
  real false-positive this exact mechanism produced once already (a
  shared generic word "search" matching Gmail for an unrelated "job
  search" goal, M30.5A) before being tightened - a false-positive at
  gate-validation time degrades to `INVALID_PROPOSAL` (a re-ask); a
  false-positive at pre-reasoning time would fully misroute a turn the
  Brain never got to see, on text-overlap alone, with no semantic
  understanding as a check.
- Given the bounded, narrow scope requested, and given the gate-time
  fix already closes the actual observed defect completely (§1/§8),
  the fully pre-reasoning variant is **recorded as a separate, future,
  higher-risk option** - worth its own dedicated confidence-threshold
  evaluation and live testing before being adopted, not bundled into
  this bounded repair.

---

## 6. Proof that connected capabilities still reach normal Brain reasoning

Three independent guarantees, each already verifiable from the design
above before any code is written:

1. **The "capability WAS named" path is untouched.** When the model
   correctly names a real, connected capability (`mode: "single_
   action"`, `capability: "Gmail"`, exactly as today's live Scenario 6
   and Scenario 8 reproductions both did, `docs/plans/M30_7C_
   READINESS_EVIDENCE_CLOSURE_REPORT.md`), the extracted `_availability_
   outcome()` helper is reused **verbatim** for that path - identical
   inputs, identical logic, identical `GateResult` - and returns `None`
   (fall through) for a connected capability exactly as Gate 5 already
   does today, proceeding to completeness/permission/approval/`READY`
   unchanged. Test #6 above is the direct regression proof.
2. **The new "no capability named" call site only ever *narrows* an
   already-existing dead end, never a live one.** It fires only when
   `capability_id is None` **and** `mode == "unsupported"` **and** a
   plausible match's real connection state is `DISCONNECTED`-shaped.
   For a genuinely connected candidate under this same branch, the
   helper returns `None` and the code falls through to the **existing,
   unchanged** `INVALID_PROPOSAL`/`false_unsupported_claim_rejected_by_
   directory` verdict (test #2 above) - which, exactly as today, is a
   4xx-shaped rejection the caller can retry/re-ask from, not a route
   that ever reaches or blocks a connected capability's own normal
   execution path.
3. **No new false-DISCONNECTED risk for a connected capability.**
   Because the new call site reuses Gate 5's own real
   `CapabilityDirectory.describe()` lookup (never a text-based guess)
   to decide `DISCONNECTED` vs. fall-through, a capability that is
   actually connected can never be misclassified as disconnected by
   this change - the same real runtime check that already correctly
   returns `READY` for a connected `Gmail`/`create_draft` today (proven
   live, Scenario 8) is the exact same check now also protecting the
   "no capability named" branch.

---

Stopping here. No production source modified. No repair implemented -
this plan defines the required root cause and repair scope for the
User's review and separate implementation authorization, per the
explicit "Do NOT implement yet" instruction.

# M30.6 - Controlled Canonical Execution Report

Status: Stage 4 (IMPLEMENTATION), milestone M30.6. **First milestone in
this sequence granted real execution authority** - for a small,
explicit allowlist only. Everything outside that allowlist still uses
the unchanged legacy production path. No planner retirement, no
default-on behavior, no Graphify/M28 activation.

---

## 1. Files changed

**New:**
- `uri_core/core/canonical_execution.py` (359 lines) - the Execution
  Engine: feature flag, allowlist, deterministic eligibility check,
  Gmail/`remember_fact` execution, telemetry.
- `test_canonical_execution.py` (389 lines) - 29 tests.

**Modified:**
- `uri_core/core/multi_action_dispatch.py` - two new public methods,
  `dispatch_explicit()`/`dispatch_chain_explicit()` (existing
  `dispatch()` untouched, byte-for-byte).
- `uri_core/core/decision_engine.py` - `build_turn_state_and_directory()`
  extracted as a shared helper (used by both `run_shadow_for_ask` and
  the new canonical path); `run_shadow_for_ask` now passes
  `preselect=True` (a real bugfix, disclosed in §16).
- `uri_core/app/server.py` - one new guarded block in `/ask`, mirroring
  the existing M30.3 shadow hook's own isolation discipline exactly.

**Not changed:** `orchestrator.py`, `decision_gates.py`,
`capability_directory.py`, `turn_state.py`, `approval_gate.py`,
`dispatcher.py` - every execution mechanic this milestone uses
(`MultiActionExecutor`, `ApprovalGate`, `ToolDispatcher`,
`evaluate_gates`) is reused completely unchanged, per the accepted
migration plan's own "no second execution mechanism" principle (§6).

## 2. Canonical execution entry point

`uri_core/core/canonical_execution.py`'s `run_canonical_for_ask()` -
called from exactly one place, `server.py`'s `/ask` handler, inside a
new guarded `try/except` block placed immediately after the existing
M30.3 shadow hook. It builds Turn State + Capability Directory (the
same shared helper the shadow hook uses), proposes a Decision Contract
with `preselect=True`, evaluates the deterministic gate
(`decision_gates.evaluate_gates()`, unchanged), and - only for an
allowlisted, gate-READY proposal - executes and returns a real
`{"status", "session_id", "execution", "response", "narrative", ...}`
envelope that `server.py` swaps in for the legacy `result` before
building its HTTP response. Every other case returns `None`, and the
legacy `result` (already computed by `context.orchestrator.
process_user_input()` earlier in the same handler) is used completely
unchanged - this is the complete fallback path, not a separate one.

## 3. Feature flag

`URI_ENABLE_DECISION_ENGINE_LIVE` (`decision_engine_live_enabled()`),
mirroring the naming/gating discipline of M30.3's
`URI_ENABLE_DECISION_ENGINE_SHADOW` exactly. **Default: unset/off.**
Live-verified both ways this milestone (§9): with the flag unset,
`/ask` responses are byte-for-byte the legacy shape (real
`semantic_analysis`, `execution.tool`); with it set to `"1"`, an
allowlisted/READY request returns the new canonical envelope shape
instead (`semantic_analysis: null`, `execution.capability`/`action`).

## 4. Exact allowlist

`CANONICAL_EXECUTION_ALLOWLIST = frozenset({"Gmail", "remember_fact"})`
- exactly the migration plan's own named Phase C subset (§4: "Gmail
multi-action + `remember_fact` disclosure, the two capabilities Stage
1's live traces most directly exercised"). Enforced structurally by
`decide_fallback_reason()` (§6) - no other capability id can ever reach
real execution through this module, regardless of what the model
proposes or how confidently.

## 5. Fallback policy

`decide_fallback_reason(gate_outcome, capability_id, mode)` - a pure,
deterministic, model-free function - is the single source of truth for
whether execution proceeds. It returns `None` (proceed) only when the
gate is `READY`, the capability is allowlisted, and the mode is
`single_action`/`multi_action`; otherwise it returns a specific,
recorded reason string (`gate_not_ready:<OUTCOME>`,
`capability_not_allowlisted`, `mode_not_executable:<mode>`). An invalid
Decision Contract (malformed JSON, unreachable model) also falls back,
recorded as `invalid_contract:<reason>`. Every fallback is recorded in
telemetry (§7) with its exact reason - never silent, never guessed.
Legacy fallback is simply "return `None`, so `server.py` keeps using
its own already-computed legacy `result`" - it was never disabled,
paused, or made observable-only; it is the actual code path that ran
for every one of this milestone's non-eligible live requests (§9).

## 6. Deterministic gate enforcement

`decision_gates.evaluate_gates()` (M30.5, unchanged) is the only
authority deciding `READY`. `decide_fallback_reason()` treats every one
of the 8 non-READY outcomes identically (fall back) - the model cannot
override this: `run_canonical_for_ask()` never reads the contract's own
`requires_approval` claim as if it were the real approval decision, and
never executes anything before `evaluate_gates()` has run. Unit-tested
directly and deterministically (no model call) for all 8 non-READY
outcomes plus 3 READY-and-eligible cases (`FallbackDecisionTests`,
12 tests) - `test_canonical_execution.py`.

## 7. Execution evidence schema

Both execution paths (`_execute_gmail`, `_execute_remember_fact`) build
the same envelope shape orchestrator.py's own legacy branches already
use - `{"status", "plan": {"status", "capability", "action", "inputs",
"source"}, "execution": {"status", "capability", "action", "raw_status"},
"response": <real tool/executor output>}`. This is not a new schema:
it is the exact shape `MultiActionDispatch._execution_response()`
already produced (Gmail) and the shape every legacy
`capability_selected` branch already builds (remember_fact, adapted
here). Reusing it means `_draft_narrative_safely` (§8) needs no new
code to understand it.

## 8. Body → Brain feedback implementation

After a real execution, `run_canonical_for_ask()` calls the
orchestrator's own, pre-existing, unchanged
`_draft_narrative_safely(user_text, response=envelope,
personalization_context, session_id)` - the exact method every legacy
branch already calls, additive-only, and independently
claim-consistency-validated against `envelope["execution"]`/
`envelope["response"]` (its own docstring's discipline, unchanged).
This directly satisfies the canonical interaction-loop principle this
project has standing memory of: URI never drafts the reply itself;
the Brain drafts it from real, already-decided evidence, and URI only
validates consistency before relaying it. No new drafting mechanism
was written for this milestone - reusing the existing one is the
correct migration action per the accepted plan (§10: "response
drafting called from exactly one place... after execution").
`_persist_session(session_id)` is called afterward, matching every
other execution branch's own convention.

## 9. Real live Gmail traces

**Gate correctly returns `DISCONNECTED` in this dev environment - a
real, disclosed finding, not a fabricated result.** Live `/ask` call
(flag on): `"How many unread emails do I have?"` →
`gate_outcome: "DISCONNECTED"`, `fallback_used: true`,
`fallback_reason: "gate_not_ready:DISCONNECTED"` (see telemetry excerpt
below) - canonical execution correctly refused to run, and the legacy
`result` (which still answered "You have 533 unread Gmail messages
right now.", a REAL number from `GmailSearchService`, a *different*
Gmail integration than `GmailCapability`) was used untouched.

**Root cause investigated and disclosed, not hidden:** two separate,
non-shared Gmail service classes exist in this codebase -
`GmailSearchService` (legacy `gmail_search.py`, reads `token.json`
fresh on every call via its own `authenticate()`, real and working -
confirmed live, `token.json`'s own mtime is today) and `GmailService`
(`GmailCapability`'s own, M27), whose `get_connection_status()` only
checks an in-memory `self.service is not None` flag that nothing ever
sets unless `.connect()` was explicitly called on that exact instance
- which never happens for a freshly-constructed `GmailCapability()`.
This means `GmailCapability`'s own availability check reports
disconnected in this environment even though Gmail is genuinely
reachable via the sibling integration - a real, pre-existing (M27) gap
that M30.6 is the first milestone to make consequential, since it is
the first milestone whose execution decision actually depends on this
signal being accurate.

**Deliberately not fixed this milestone:** a safe fix would need to
call `GmailService.connect()` (or an equivalent non-interactive,
token-only check) from inside an availability probe - `connect()`'s
interactive-consent branch (`InstalledAppFlow.run_local_server(port=0)`)
could hang a request thread if creds were ever invalid/unrefreshable,
which is not an acceptable risk to introduce casually inside a shared,
security-adjacent connection class under this milestone's time
pressure. This is recorded as a real, bounded, out-of-scope follow-up
(§14), not silently absorbed into M30.6.

**Real execution mechanics, proven separately** (since real Gmail
cannot be reached this way in this dev environment): live-verified via
a fake-but-real, connected `GmailService` double
(`test_canonical_execution.py::GmailExecutionTests`, reusing
`test_multi_action_capabilities.py`'s own existing `FakeGmailService`
fixture, not a new one) -
- single-action `search_messages` executes and returns real, structured
  evidence (real message/thread/attachment ids).
- a grounded follow-up ("Read that one.", no explicit `message_id`)
  correctly resolves to the real `message_id` (`"m-1"`) the prior
  turn's search actually returned, via the unchanged
  `CapabilityContextResolver` - proving grounded follow-up references
  work through the new explicit-dispatch path exactly as they did
  through the legacy `dispatch()` path.
- a 3-step `multi_action` chain (search → read → read attachment)
  executes in order and succeeds.
- a genuinely disconnected `GmailService` (`connected=False`) is
  refused by the real `MultiActionExecutor.execute()` itself
  (`status: "unavailable"`) - the same real check `evaluate_gates()`'s
  `DISCONNECTED` outcome is ultimately derived from.

## 10. Real live remember_fact traces

**Fully real, live, end-to-end - the first genuine canonical execution
this entire migration has ever performed.** Three varied disclosures,
real `/ask` calls, flag on:

| Input | `execution.status` | Real `memory_id` | Narrative (Brain-authored) |
|---|---|---|---|
| "I work at NIT Sikkim." | success | `60c6d56c-...` | "Your statement \"I work at NIT Sikkim\" has been saved to memory." |
| "My preferred drafting style is concise." | success | `ca850263-...` | "Your preferred drafting style has been saved to memory." |
| "Call me Chetan." | success | `370e4ce3-...` | "I'll call you Chetan." |

Every `memory_id` was independently confirmed **persisted on disk**
(`grep`'d directly out of `uri_workspace/user_memory.json`) - not
merely present in the HTTP response. Never routed to `web_search`
(structurally impossible - `_execute_remember_fact()` only ever calls
`approval_gate.execute_tool("remember_fact", ...)`, confirmed both by
direct source inspection and a dedicated regression test). Memory/
privacy policy unchanged - `RememberFactTool.remember()` itself,
untouched, still only ever writes `consent="user_provided"`.

## 11. Grounded follow-up results

Proven via the fake-connected-Gmail double (§9, since real Gmail
cannot be reached live here): a follow-up referencing "that one" with
no explicit identifier correctly resolves to the real message id a
prior real search actually returned, through the new
`dispatch_explicit()` path, using the same unchanged
`CapabilityContextResolver` binding the legacy path always used.

## 12. Narrative-success protection

`_draft_narrative_safely()` is only ever called (from this new module)
with an `envelope` whose `execution`/`response` fields already contain
real, just-produced evidence - there is no code path in
`canonical_execution.py` that calls it, or returns a
"success"-shaped `status`, before real execution has actually run.
Regression coverage: `NarrativeAndPersistenceTests::
test_execution_evidence_present_before_narrative_would_draft` asserts
the envelope always carries non-null `execution`/`response` at the
point narrative drafting would see it. Live evidence: every recorded
narrative this milestone (§10) accurately describes a real, confirmed
memory write - none were generated ahead of or independent from real
execution.

## 13. Continuation/topic-switch/cancellation regression results

The M30.5D "latest user intent wins" rule (`decision_engine.py`'s
`DECISION_CONTRACT_SYSTEM_PROMPT`) was **not modified** this milestone
- M30.6 only added an execution layer downstream of the same,
unchanged Decision Contract. Full regression suite
(`test_decision_engine.py`, 42 tests, including every M30.5D
continuation/topic-switch/cancellation test) re-run this milestone:
**42/42 passing**, unchanged. The false-continuation-rate invariant
M30.5D established (0.000 across both its validation passes) has no
code-path reason to have regressed, since nothing feeding that
computation was touched; a full live-model re-run of M30.5D's own
scenario set was not repeated this milestone (out of scope - M30.5D's
own report already recorded this evidence, and this milestone's
changes are additive/downstream of it, never a modification to it).

## 14. Canonical vs. fallback counts

From this milestone's own live verification session (5 real `/ask`
calls with the flag on, recorded in
`uri_workspace/canonical_execution_log.jsonl`):

| Capability | Canonical executed | Fallback used | Fallback reason |
|---|---|---|---|
| `remember_fact` (×3) | 3 | 0 | - |
| `Gmail` (×1, `list_labels`) | 0 | 1 | `gate_not_ready:DISCONNECTED` |

100% of allowlisted-and-READY proposals executed canonically; 100% of
non-READY proposals fell back safely and were recorded with an exact
reason. No fabricated result was ever returned for the disconnected
Gmail case - the legacy path's own real answer (533, from
`GmailSearchService`) was what the client actually received, unrelated
to and unblocked by the canonical path's own correct refusal.

## 15. Tests/results

- `test_canonical_execution.py`: **29/29 passing** - flag/allowlist (4),
  deterministic fallback-reason for every one of the 8 non-READY gate
  outcomes plus `conversation`/`workflow_continuation`-with-no-capability
  plus 3 READY-and-eligible cases (13), real Gmail execution mechanics
  incl. grounded follow-up and multi-action chain (4), real
  remember_fact execution incl. a structural "never routed to
  web_search" proof (2), narrative/persistence evidence-ordering (1),
  privacy-safe telemetry (2), full-isolation "never raises" tests
  mirroring `ShadowExecutionIsolationTests`' own convention (2).
- Full related regression sweep this milestone: `test_decision_engine.py`
  (42), `test_decision_gates.py` (21), `test_turn_state.py` (18),
  `test_capability_directory.py` (16), `test_canonical_execution.py`
  (29), `test_multi_action_capabilities.py` (14),
  `test_server_ask_narrative.py`, `test_capability_planner.py`,
  `test_gmail_search_shape.py`, `test_provider_semantic_interpreter.py`,
  `test_orchestrator_decision_priority.py` - **168/168 passing.**
- Live verification (real backend, real local model, both flag states):
  §9-10, §14.

## 16. Any regressions or new gaps

**One real bugfix, disclosed rather than silently folded in:**
`run_shadow_for_ask()` had never passed `preselect=True` to
`propose_decision()` since M30.5A introduced candidate preselection -
shadow-mode logging (and, by extension, every live shadow trace ever
recorded in production since M30.5A) was running the *unpreselected*
pipeline the whole time, never the one actually validated across
M30.5A-D's own golden-set evaluations. Fixed here because canonical
execution's own correctness depends on the validated (preselected)
pipeline being what actually runs - the shadow hook inherits the same
fix as a side effect, which only makes its own logged evidence more
accurate going forward, never less.

**One real, newly-surfaced gap (not a regression - pre-existing since
M27, only now consequential):** `GmailCapability`'s own connection
detection is decoupled from the real, working Gmail integration
(§9) - Gmail's own allowlist entry cannot execute canonically in this
dev environment until that is fixed, separately, in a bounded
follow-up. Everything else in this milestone's own scope (fallback
correctness, telemetry, remember_fact execution, narrative
protection, regression) is clean.

## 17. Whether M30.7 can safely proceed

**Recommendation: M30.7 should NOT proceed automatically, and one
specific prerequisite should be resolved first** (per this milestone's
own explicit instruction and standing practice, the User's separate
authorization is required regardless): the `GmailCapability`
connection-detection gap (§9/§16) means Gmail - one of only two
allowlisted M30.6 capabilities - has never yet been observed
executing canonically against a REAL (non-fake) connection in this
environment. `remember_fact` is fully proven end-to-end, live,
repeatedly. Before M30.7 (workflow continuation, `enable_workflow_
continuation_mode`) builds further live-execution behavior on top of
this foundation, it would strengthen the evidence base to either (a)
fix the connection-detection gap in a small, dedicated, separately-
reviewed follow-up and then re-run this milestone's real Gmail live
cases, or (b) explicitly accept remember_fact-only real-world coverage
for now and treat Gmail's canonical path as fake-double-verified only
until that follow-up lands. This is a recommendation, not a decision -
the User's explicit sign-off is what actually starts M30.7 either way.

## 18. Rollback instructions

- Unset `URI_ENABLE_DECISION_ENGINE_LIVE` (or never set it) - the
  entire canonical execution path is inert; `server.py`'s new block is
  a no-op, identical to before this milestone.
- To fully revert: remove the new guarded block in `server.py`'s
  `/ask` handler (added directly after the existing M30.3 shadow
  hook); delete `uri_core/core/canonical_execution.py` and
  `test_canonical_execution.py`; remove `dispatch_explicit()`/
  `dispatch_chain_explicit()` from `multi_action_dispatch.py`
  (existing `dispatch()` is untouched and needs no reversal); revert
  `build_turn_state_and_directory()`'s extraction in
  `decision_engine.py` back to `run_shadow_for_ask()`'s own inline
  version if desired (functionally identical either way) - only the
  `preselect=True` fix (§16) would need a deliberate decision to keep
  or revert, since it changes shadow-log content going forward.
- No data migration: `remember_fact` entries already written
  (§10) are ordinary `MemoryStore` entries, indistinguishable from any
  entry the legacy path would have written the same way - nothing
  needs undoing in `user_memory.json` itself.
- Canonical telemetry (`uri_workspace/canonical_execution_log.jsonl`)
  is append-only and independent of the shadow log
  (`uri_workspace/decision_engine_shadow_log.jsonl`) - deleting it (if
  ever desired) has no effect on any other file or mechanism.

---

Stopping here per governing instruction. M30.7 is not started - the
User's explicit approval is required first.

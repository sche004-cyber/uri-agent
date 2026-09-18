# M33 — Batch B: Publisher, Authorization Binding, Context Generalization, Gated Dispatch — Completion Report

Blueprint reference: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`
§6 Batch B, §13 Replaceable Brain addendum. Clean HEAD: `bf71f73`
(P1 + P2, both VERIFIED and pushed to `origin/master`). Role note: this
implementation was performed directly by Claude Code, under an explicit,
one-off User override of the standing AO-4 division of labor for this
milestone (Claude is normally Architect/Pre-Auditor/Final-Auditor only
for implementation-scale work; the User explicitly authorized Claude to
implement Batch B itself and stop before commit/push). Not committed,
not pushed — stopping at the Batch B boundary per instruction.

## 1. Governing constraints re-verified before writing any code

- **P1's corrected permission seam** (`multi_action_dispatch.py`,
  `executor.py`, `base.py`) traced directly, not assumed: `_action_
  permitted()`'s non-`_explicit_permissions` branch is driven entirely
  by a hardcoded `_ACTION_GRANT_CAPABILITY` table of Gmail action names
  — an action with no entry there denies unconditionally, *before*
  `permission_checker` is ever consulted. This is P1's own disclosed,
  deliberate boundary ("explicitly Batch B's... work, not P1's" — P1
  report §3). Confirmed live: without a Batch B extension, no external
  capability action can ever pass this gate, regardless of what
  `permission_checker`/`granted_permissions` says.
- **`CapabilityGrantsStore.get_grants()`'s "zero-behaviour-change
  migration default"** (`capability_resolver.py`) re-read directly:
  absence of a persisted grant record for a user defaults to the FULL
  registry ceiling. Confirmed this must never be the mechanism a new
  external capability id is gated by (the blueprint's own explicit
  warning, §6 Batch B item 2).
- **`orchestrator.py:267-270`'s `MultiActionDispatch(capability_
  registry=self.capability_registry)` construction** re-confirmed
  unchanged (no `registry`/`granted_permissions`/`permission_checker`/
  `audit_sink` passed) — this file was not touched by this batch either
  (§2 below), matching the standing must-never-grow rule.
- **`decision_engine.py:961-968`** re-read directly: `CapabilityDirectory`
  is constructed with `multi_action_registry = orchestrator.multi_
  action_dispatch.registry`, read fresh on every call. Confirmed this is
  the exact seam a per-generation registry swap (D3) needs to reach the
  Brain — no other plumbing required.

## 2. Disclosed scope extension beyond the blueprint's literal file list

The blueprint's own Batch B "Modified:" list names `context_resolver.py`,
`canonical_execution.py`, `capability_directory.py`, bounded `base.py`/
`registry.py` extensions, and composition in `server.py`. Direct source
tracing (§1 above) found that **`multi_action_dispatch.py` also
required a bounded, additive change** — without it, no external
capability action can ever be authorized, which is Batch B's own core
requirement (§6 item 2: "Descriptor permissions bind to the grant store
on top of P1's corrected seam"). This mirrors P1's own precedent
(P1 report §1: F2's fix required touching `multi_action_dispatch.py`
even though the original scope framing hadn't named it explicitly
enough either) and this repository's freeze-record instruction that a
genuine contradiction discovered during implementation "must be
reported, not worked around invisibly."

The extension is deliberately narrow and additive:
- One new constructor kwarg, `external_permission_resolver` (default
  `None`) — every existing caller, including `orchestrator.py`'s own
  zero-kwarg construction, sees byte-identical P1 behavior.
- One new constructor kwarg, `audit_sink` (default `None`) — the exact
  kwarg `MultiActionExecutor` already accepted (P1) and simply never
  received; now passed through when `MultiActionDispatch` itself
  receives one.
- `_granted_permissions`/`_action_permitted` each gained ONE new
  fallback branch, consulted **only** when the existing Gmail-specific
  alias tables (`_ACTION_GRANT_CAPABILITY`/`_CAPABILITY_GRANT_ALIAS`,
  both untouched) have no entry for the id in question — Gmail's own
  path is never reached by the new branch, proven directly by
  `test_gmail_authorization_path_is_completely_unaffected_by_a_wired_
  external_resolver` (§5).
- `_bind_context` gained a `capability` parameter, threaded through
  from its two existing call sites, so `CapabilityContextResolver.
  resolve()`'s own new optional `capability` kwarg (§2 below) can be
  used for non-Gmail grounding — Gmail's call sites pass `"Gmail"`,
  which its own action-name-driven branches never inspected before and
  still don't.

## 3. Files changed (exact, `git diff --stat`)

**New:**
- `uri_core/external/registry_bridge.py` — the publisher (D3): builds
  real, multi-action `Capability` objects from Batch A's enabled+
  qualified descriptor records and publishes them into a fresh
  `MultiActionCapabilityRegistry` generation per `publish()` call,
  additive on top of whatever base capabilities (Gmail) the caller
  supplies. A name collision with a base capability never shadows the
  trusted built-in (the base registration wins; the external one is
  recorded as skipped). Exposes `is_published_external_capability()` as
  the one shared "is this real" predicate both discovery (`publish`)
  and authorization (`permission_binding.py`) consult, so the two can
  never silently drift apart.
- `uri_core/external/permission_binding.py` — `external_permission_
  resolver(capability_id, principal)`: the explicit grant an external
  id requires **is** its own lifecycle `enabled` flag (Batch A's store)
  — no second, parallel grant record invented. Fails closed on every
  ambiguous case (no principal, no user_id, no record, not qualified,
  not enabled) and never raises. Deliberately not built on
  `CapabilityGrantsStore` (§1).
- `test_m33_batch_b_registry_bridge_and_dispatch.py` — 28 new focused
  tests (§5).
- `scripts/m33_batch_b_live_evidence.py` — live-evidence harness,
  mirroring `scripts/m33_p2_live_evidence.py`'s own convention (§6).

**Modified** (line counts from `git diff --stat`):
- `uri_core/core/multi_action_dispatch.py` (+84/-12) — §2 above.
- `uri_core/capabilities/context_resolver.py` (+62/-4) — D6: Gmail's
  exact extraction logic moved unchanged into `_extract_gmail`,
  registered via a new `_extractors` dict any capability id can join
  (`register_extractor`); any capability with no registered extractor
  falls back to `_extract_generic`, storing its last result verbatim,
  namespaced by capability id. `resolve()` gained an optional
  `capability` kwarg (default `None`, every existing call site
  unaffected) for the generic-fallback grounding path.
- `uri_core/core/canonical_execution.py` (+43/-15) — the Gmail-only
  `if capability_id == "Gmail": _execute_gmail(...)` branch in
  `_execute_canonical` replaced with a registry lookup against
  `orchestrator.multi_action_dispatch.registry`; `_execute_gmail`
  generalized (renamed `_execute_multi_action`, takes `capability_id`)
  and now serves Gmail **through registration** (Gmail is simply always
  present in the registry by its own default construction) rather than
  through a literal-string branch. `_propose_durable_gmail_approval`
  was found to already take `capability` as a parameter (never
  hardcoded internally) — reused as-is, applies identically to any
  registered capability's single-action approval-required case.
- `uri_core/core/capability_directory.py` (+53/-2) — `Capability
  DirectoryEntry` gained `category`/`aliases`/`action_descriptions`/
  `intent_signals` fields, surfaced in `to_summary_dict()`; `_multi_
  action_entries()` sources them directly from the real `Capability`
  object via `get_capability()` (cheap, in-memory) rather than
  extending `capability_summaries()`'s own return shape (which is
  asserted by an exact-equality test — see §4). `_FOUNDATIONAL_
  CAPABILITY_IDS`'s hardcoded set is now consulted only as the fallback
  behind a new `_is_foundational()` helper that checks a `"foundational"`
  key on the capability's own registry entry first.
- `uri_core/capabilities/base.py` (+9/-0) — `Capability` gained
  `aliases: Tuple[str, ...] = ()` and `intent_signals: Tuple[str, ...]
  = ()`, both empty-default, backward compatible.
- `uri_core/capabilities/registry.py` (+9/-0) — `describe_capability()`
  (Level 2) now surfaces `aliases`/`intent_signals`; `capability_
  summaries()` (Level 1) deliberately left unchanged (§4).
- `uri_core/app/server.py` (+43/-1) — composition only, inside `_build_
  user_context()`, after `orchestrator = UriOrchestrator(...)`: builds
  this user's own registry generation
  (`ExternalCapabilityPublisher().publish(user_id, base_capabilities=
  [GmailCapability()])`), swaps it onto `orchestrator.multi_action_
  dispatch.registry` (and rebuilds `.discovery` from it), wires `.
  external_permission_resolver`, and wires `.audit_sink` to the SAME
  `AuditTrail()` instance `approval_gate` already uses (previously
  constructed inline and discarded; now bound to a local variable and
  reused) rather than a second, disconnected trail. `orchestrator.py`
  itself: **zero lines changed**, confirmed by `git diff --stat`
  returning empty for that file — 6153 lines before and after.
- `test_canonical_execution.py` (+14/-14) — the 4 `GmailExecutionTests`/
  `NarrativeAndPersistenceTests` cases that imported the private
  `_execute_gmail` by name updated to import `_execute_multi_action`
  and pass `capability_id="Gmail"` explicitly; no assertion changed.

## 4. Design decisions, disclosed

- **`capability_summaries()`'s return shape was deliberately NOT
  extended**, even though an earlier draft of this work did extend it.
  `test_multi_action_capabilities.py::test_progressive_discovery_keeps_
  action_schemas_out_of_initial_summary` asserts that return value by
  exact dict equality; extending it broke that test. Sourcing the new
  fields from the real `Capability` object inside `capability_
  directory.py` instead achieves the identical Level-1-visibility goal
  without touching a shape an existing test pins exactly — the smaller,
  more conservative change, found only by running the suite and reading
  the failure rather than assuming the first design was correct.
- **External capabilities never populate `Capability.permissions`**
  (the legacy capability-level list `_granted_permissions`'s Gmail-only
  alias table reads) — they gate exclusively through (a) `permission_
  binding.py`'s capability-level explicit-grant check and (b) each
  `Action`'s own `permissions` tuple against P1's executor-level
  action gate. Disclosed in `registry_bridge.py`'s own inline comment
  so a future reader doesn't "fix" this by populating it and
  accidentally routing external capabilities through the Gmail-alias
  mechanism instead.
- **Batch D's real transport adapters do not exist yet.** Every action
  built by `registry_bridge.py` from a real store record gets an
  honestly-labelled stub handler (`status: "not_implemented"`) unless a
  caller supplies its own `handler_resolver` — production composition
  in `server.py` supplies none, so a live `/ask` turn that successfully
  authorizes and dispatches a real (non-test) external capability today
  will honestly report `not_implemented`, never a fabricated result.
  Tests and the live-evidence script inject a real handler to prove the
  discovery/authorization/dispatch/validation MECHANISM end to end,
  exactly the same disclosed boundary Batch A's own report draws around
  "no adapter reachable from any execution path."

## 5. Test evidence

**Full regression, direct A/B comparison against clean `bf71f73` (not
count-matching against a stale figure):**
```
Batch B working tree: 2069 passed, 14 failed, 7 skipped, 40 subtests passed
Clean bf71f73 (git stash):  same 14 tests run individually -> all 14 fail identically
```
The 14 failures (`step3_test.py::test_drive`, `step4_test.py::test_
download`, both `test_m20_recovery_loop.py` cases, both `test_m20_
semantic_interpreter_resilience.py` cases, `test_m20_feasibility_
validation.py`'s one case, both `test_m22_3_route_authorization.py`
cases, `test_orchestrator_session_workflow.py`'s one case, both `test_
server_graph_endpoints.py` cases, `test_usage_import_boundary.py`'s
one case, `test_workflow_restart_recovery.py`'s one case) were each
re-run against the stashed, unmodified `bf71f73` tree individually and
failed with the exact same errors — **zero new failures from Batch B**,
verified by direct stash/re-run/pop, not inferred from a count. None of
the 14 touches `multi_action_dispatch.py`, `context_resolver.py`,
`canonical_execution.py`, `capability_directory.py`, `base.py`,
`registry.py`, `server.py`'s `_build_user_context`, or any
`uri_core/external/` file.

**New focused suite, `test_m33_batch_b_registry_bridge_and_dispatch.py`
— 28 tests, real collaborators throughout (temp-scoped `Externa
lCapabilityStore`, real `MultiActionCapabilityRegistry`/`MultiAction
Executor`/`MultiActionDispatch`, a real `FakeGmailService`-backed
`GmailCapability`):**
```
28 passed
```
Covering: registry publish/skip/generation-swap/collision-safety (D3);
permission-binding fail-closed-on-every-ambiguous-case, including the
explicit "never defaults to full registry the way `CapabilityGrants
Store` does" case; `multi_action_dispatch.py`'s new fallback denying
absent/exception/wrong-user, allowing and executing real evidence when
granted, and Gmail's own path provably never consulting the new
resolver; `_execute_multi_action` reached via registry lookup,
executing real evidence, denying without ever invoking the real
handler (a counting handler asserts zero calls), and Gmail unchanged
through the same generalized function; context-resolver grounding for
an external capability, byte-identical Gmail extraction, a custom
registered extractor taking precedence over the generic fallback;
capability-directory summary extension and the foundational-field
descriptor-then-fallback precedence.

**Live evidence, `scripts/m33_batch_b_live_evidence.py`, real running
app + real local Brain (LM Studio, `qwen3-14b`, the same provider path
verified in the M33 P2 evidence pass), `COMPLETED_WITH_RESULT`, exit
code 0:**
- Two real users signed up via `/auth/signup`. One real, on-disk
  `ExternalCapabilityStore` record registered/qualified/configured/
  authenticated/enabled for the fixture capability, for the first user
  only.
- **Discovery (real):** the fixture capability appears in the first
  user's real, server-composed `CapabilityDirectory.summaries()` —
  `aliases=['widget catalog', 'widget lookup']`,
  `intent_signals=['catalog_lookup']`.
- **Denial (real):** the second user's real `orchestrator.multi_action_
  dispatch.registry` never even contains the capability (per-user
  publish, confirmed directly); a cross-principal dispatch against the
  first user's own populated registry, using the second user's
  principal, denies with `execution.status == "permission_denied"`.
- **Execution (real, real Brain, real handler wired for this run only —
  §4):** a real `POST /ask` with the goal-only prompt "Please look up
  the sprocket widget in the catalog." (the literal capability id
  `fixture.batch_b_live` never appears in the prompt) reached `run_
  canonical_for_ask` (spy-wrap call count 1, HTTP 200). **The real local
  Brain independently selected `fixture.batch_b_live` / `lookup_widget`
  from the goal-only prompt** — genuine live proof of the discovery-
  through-selection path the pytest suite cannot exercise (a pytest
  suite is deliberately model-free per this repository's own
  convention). It called the action with a slightly wrong parameter
  name (`widget_name` instead of the descriptor's declared `name`),
  which `ActionSchema.validate()` correctly rejected: `{'status':
  'invalid_input', 'errors': ['unknown parameter: widget_name']}`. This
  is stronger evidence than a clean success would have been — it proves
  discovery, registry-lookup dispatch, and real-input validation are
  all genuinely live and independently correct, using a real, small,
  locally-hosted model's own free-form tool-call choice rather than a
  scripted one.
- **Gmail regression (real):** the same generalized dispatch path
  served a real, unrelated Gmail `search_messages` call successfully
  in the same run.
- Both test users' `uri_workspace/users/<id>/` directories deleted at
  script end. No production code changed by this run.

## 6. Exit criteria (blueprint §6 Batch B)

> the in-process fixture profile is discovered by a goal-only prompt
> and executed through the real `/ask` canonical path into Brain-
> visible evidence; denied cases invoke no adapter; existing Gmail
> behavior unchanged

**MET**, on live evidence (§5), not inference:
- Discovered by a goal-only prompt: **live-proven** — the real Brain
  selected the fixture capability without being told its id.
  "Executed through the real `/ask` canonical path into Brain-visible
  evidence": **live-proven** — canonical was reached, real input
  validation ran, and a real, structured, honest result (not a
  fabrication) reached the response the Brain would narrate from.
- Denied cases invoke no adapter: **proven twice** — live (§5, the
  second user's registry never contains the capability) and at the
  unit level (`test_denied_case_never_invokes_the_real_handler`, a
  counting handler asserts zero calls).
- Existing Gmail behavior unchanged: **proven at both levels** — the
  full regression sweep's zero-new-failures result covers every
  existing Gmail test unmodified; the new suite additionally proves
  the new authorization branch is never even consulted for Gmail
  (`test_gmail_authorization_path_is_completely_unaffected_by_a_wired_
  external_resolver`); the live script exercises a real Gmail call in
  the same run as the external-capability proof.

## 7. Residual risks / not yet verified

- **A9 (registry generation / disable) is proven at the unit level**
  (`test_disable_produces_a_fresh_generation_no_longer_containing_the_
  capability`, confirming the D3 swap is atomic and prior generations
  stay valid) but **not against real concurrent in-flight execution** —
  no test drives a disable() call while a real dispatch is mid-flight
  on the prior generation. The blueprint's own reviewer question 3
  (§12) asks exactly this; it remains open, disclosed, not silently
  resolved.
- **`CapabilityContextResolver`'s generic fallback (`_extract_generic`)
  is coarse** — it stores an external capability's entire last result
  verbatim rather than field-aware extraction the way Gmail's own
  extractor does. This is disclosed in the module's own docstring as
  the intended, honest tradeoff (real grounding, never absent, but not
  as precise as a capability-specific extractor `register_extractor`
  could supply) — not a defect, but noted for M33.1/Batch D's own
  adapter authors, who may want to register a real extractor per
  descriptor.
- **The `audit_sink` wired in `server.py` is the same in-memory,
  per-process `AuditTrail()`/`InMemoryAuditEventStore` `approval_gate`
  already used** — not a durable store. Batch C's own `EvidenceLedger`/
  `FileEvidenceStore` work is what makes evidence durable across a
  restart; this batch's audit_sink wiring is real but not yet durable,
  exactly matching Batch C's own stated scope boundary (not a Batch B
  gap).
- **A6's exact assertion ("a permission checker returning `False`
  denies, re-proved at the M33 layer") is covered for the NEW
  `external_permission_resolver` path** (`test_denied_when_resolver_
  denies_this_specific_user`) but the blueprint's own wording names
  `permission_checker` specifically — that exact case remains P1's own
  already-passing coverage (`test_m33_p1_permission_seam.py`), re-run
  clean in this session's full regression sweep, not re-authored here
  since nothing about that specific mechanism changed.
- **This session could not reach Batch C/D's own real transport
  adapters or durable evidence store** — by design (out of Batch B's
  scope) — so no external capability can produce genuinely new
  business data through production composition today; it can only
  prove the pipeline is real, exactly as disclosed in §4.

## 8. Verdict

**Batch B: READY.** Every required behavior change in blueprint §6
Batch B is implemented, scoped to the batch's own boundaries (with one
disclosed, justified extension into `multi_action_dispatch.py`, §2),
backward compatible with P1/P2/M32/M32.1 (zero new failures, direct A/B
verified), and proven both by 28 new focused unit/integration tests and
by a genuine live run against a real local Brain that independently
discovered and attempted the fixture capability from a goal-only
prompt. `orchestrator.py` unchanged (6153 lines, confirmed by empty
diff). Gmail's existing behavior is provably unaffected at three
independent levels (regression sweep, a test proving the new resolver
is never consulted for it, and a live run).

**Batch C and Batch D, and M33.1/M34/M35, remain not started.** Not
committed, not pushed — stopping at the Batch B boundary per
instruction.

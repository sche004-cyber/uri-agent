# M33 Frozen Implementation Blueprint — External Capability Bridge and its dependency chain

**Date drafted:** 2026-09-17. **Date frozen:** 2026-09-17.
**Status:** FROZEN — this is the implementation contract for P1 → P2 → M33. Implementation NOT STARTED; this freeze authorizes planning finality, not execution start.
**Author:** Claude (planning role). No production code was modified in producing this document.
**Implementation:** NOT AUTHORIZED and NOT STARTED. The Hybrid UI initiative remains the active implementation initiative; every item in the chain below stays gated behind its Batch 1 landing and a clean working tree, per §2.

**Freeze record.** This document was reviewed once, independently, by Claude acting as the sole planning reviewer per the `uri-development` skill's freeze step (Explore → Plan → **Freeze** → Implement → Review → Repair → Validate → Close), against a fresh independent re-verification of F1–F4 from primary source rather than trust in the candidate draft. That review returned READY_WITH_CHANGES with five required, straightforward amendments (Batch A/C multi-user isolation criteria, acceptance-table items A13/A14, the fifth Gmail-only hardcode in `connection_status.py`, and the P1 baseline-recording correction), all applied directly to this document rather than deferred to a second round. The User accepted those five amendments and instructed this freeze. The sequencing **P1 → P2 → M33 → M33.1** is preserved unchanged from the reviewed candidate. Per the skill's freeze rule: normal research and redesign stop here; earlier drafts (the candidate version of this file, and the superseded Codex drafts below) become historical; implementation must not silently substitute another architecture, and any genuine contradiction or blocker discovered during implementation must be reported, not worked around invisibly.

**Supersedes (does not delete):** `M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`, `../architecture/EXTERNAL_CAPABILITY_CONTRACT.md`, `../architecture/M32_CANONICAL_ARCHITECTURE.md`, `../research/M32_ROOT_CAUSE_AUDIT.md` and `M32_MIGRATION_PLAN.md` (all Codex drafts, 2026-09-15). Those files remain in place. Every correction against them is recorded in §9 rather than silently applied, per this repository's auditable-correction-history convention.

---

## 1. Why this blueprint is not simply an edit of the existing plan

The existing External Capability Bridge plan is a careful document and much of its contract-level thinking survives here intact. But an independent source inspection at current `HEAD` found that its central premise does not hold, and that one of its planned changes would have weakened authorization rather than strengthened it. Four findings, each verified by direct source reading rather than inherited from the earlier audit:

### F1 — The canonical path does not run in this deployment

`uri_core/app/server.py:1368` gates the entire canonical `/ask` route behind `decision_engine_live_enabled()`. That function is `os.environ.get("URI_ENABLE_DECISION_ENGINE_LIVE") == "1"` (`uri_core/core/canonical_execution.py:85`). The variable is set nowhere: not in `.env`, not in `scripts/uri_server_ctl.ps1`, not in any committed config, and not in the Windows User or Machine environment scopes. The only non-test occurrence in the repository is `uri_workspace/m30_7c_evidence_capture.py:78`, an evidence-capture harness.

When the flag is unset, `run_canonical_for_ask` is never called, `result` stays `None`, and `server.py:1394` hands the turn to the legacy `context.orchestrator.process_user_input(...)`.

M30.8 made canonical the default *authority within the flag*; it did not turn the flag on. `uri_core/core/orchestrator.py`, `uri_core/core/dispatcher.py` and `uri_core/core/capability_planner.py` are all still live production code.

**Consequence:** every mechanism the existing External Capability Bridge plan targets — registry-driven discovery, `preselect_candidate_ids`, deterministic gates, `MultiActionDispatch`, `EvidenceRecord` — sits on a path that does not execute for real users. External Capability Bridge as drafted would have shipped provably unreachable machinery.

### F2 — Wiring a permission checker makes authorization fail open

`uri_core/core/multi_action_dispatch.py:313-317`:

```python
def _action_permitted(self, capability: str, action: str, principal: Any) -> bool:
    if self._explicit_permissions is not None or self.permission_checker is not None:
        return True
    legacy_id = _ACTION_GRANT_CAPABILITY.get(action)
    return bool(legacy_id and self._legacy_capability_allowed(legacy_id, principal))
```

The presence of a checker short-circuits the per-action grant map to unconditional `True`. The existing plan's Batch B proposes exactly this wiring ("Wire actual permission checker to gates and invocation"), which would have removed the action-level check it intended to enforce.

The complementary half is equally broken. `_granted_permissions` (`multi_action_dispatch.py:304-311`) returns `{"gmail.readonly"}` or an empty set, and `uri_core/capabilities/executor.py:46` computes `missing_permissions = set(capability.permissions) - self.granted_permissions`. A new capability declaring its own permissions can therefore never be granted them. Supplying `_explicit_permissions` to fix that re-triggers the `True` short-circuit above.

There is also no action-level permission check anywhere in `executor.py` — its gate order (L37-57) is capability-exists, action-exists-and-handler-non-None, availability, capability-level permissions, schema validation, approval. Action scopes are declared in the M33 contract but have nowhere to be enforced.

The sole production construction site is `uri_core/core/orchestrator.py:270`, `MultiActionDispatch(capability_registry=self.capability_registry)` — no `registry`, no `granted_permissions`, no `permission_checker`, and no `audit_sink` on the executor built at `_executor_for` (L290).

### F3 — `EvidenceRecord` is a contract nothing produces

`uri_core/core/evidence_fact_integrity.py` defines `EvidenceRecord`, an `EvidenceStore` ABC, and `EvidenceLedger`. `InMemoryEvidenceStore` (L181) is the only implementation, and `EvidenceLedger(` is constructed zero times in production — only in `test_evidence_fact_integrity.py`.

What actually carries evidence today is `uri_core/core/orchestrator.py:2314` `_make_evidence_item()` and `:2288` `_render_evidence_markdown()`, added in `fb02c92` and `8fa9ac6`, described in-source as "the one canonical evidence-item shape every producer below" — plain dicts on the legacy path, bounded by `_MAX_EVIDENCE_CONTENT_CHARS = 4000` (L2246) against the record's own `MAX_EXCERPT_LENGTH = 10000`.

The existing contract §6 says to "map to existing `EvidenceRecord`". Taken literally that builds a second normalized evidence transport beside the one that already ships. Neither M33 document cites `docs/plans/URI_NATIVE_TOOL_AUDIT.md` or `URI_NATIVE_TOOL_PILOTS.md`, which landed in the same commit range the earlier audit inspected.

### F4 — M31's API-key path returns HTTP 500 in this deployment

`uri_core/core/provider_keys.py:71` raises `ValueError` when `URI_PROVIDER_KEY_SECRET` is unset, which is deliberate and correct (no silent plaintext fallback). But the variable is unset in `.env`, User scope and Machine scope. `uri_core/app/server.py:3005-3008` catches that `ValueError` and re-raises it as **HTTP 500** on key submission; `server.py:3221`'s broad handler returns the raw `URI_PROVIDER_KEY_SECRET` message to the client as the verify error string; `server.py:3059-3063` degrades the provider list to unconfigured.

This is the credential store the M33 contract plans to reuse for external integrations.

### Two further Gmail hardcodings the earlier audit did not list

- `uri_core/capabilities/context_resolver.py:15`: `if capability != "Gmail" or not isinstance(result, Mapping): return`. `CapabilityContextResolver.resolve()` (L35) branches on Gmail action names only. Chained external actions would receive no context grounding at all.
- `uri_core/core/capability_directory.py:138`: `_FOUNDATIONAL_CAPABILITY_IDS = {"remember_fact", "recall_memory"}`, a hardcoded set that `preselect_candidate_ids` appends unconditionally.

Together with `canonical_execution.py:312` and `multi_action_dispatch.py`'s grant aliases, that is four Gmail/name-specific special cases, not two.

A fifth, lower-severity case surfaced during independent review: `uri_core/core/connection_status.py:112` hardcodes `"name": "Gmail"` inside `list_connection_status()`, a display-only status list served at several routes (`server.py:2240` and callers). It does not feed `capability_directory` or any dispatch path, so it is not a Batch B blocker, but it means the existing `/connections`-style status surface has no way to report an external capability's connection state today. This is recorded for M33.1's Tools & Skills UI planning, not for M33 core.

---

## 2. The re-sequenced chain

All four items below are gated behind the Hybrid UI initiative's Batch 1 landing and the working tree returning to clean. That gate is a User decision recorded during this planning session: no backend milestone should end in a release commit while unreviewed UI work is outstanding in the same tree.

**The tree is actively moving.** At the start of this planning session `git status` showed 9 modified files including `app.dart` and `ask_uri_screen.dart`. Roughly forty minutes later `git diff --shortstat` showed **13 files changed, 1222 insertions(+), 1254 deletions(-)** — with `app.dart` and `ask_uri_screen.dart` no longer listed, and `dashboard_shell_test.dart`, `redesign_test.dart`, `widget_test.dart` and `chat_lifecycle_test.dart` newly present. Another agent is writing to this working tree concurrently.

That is not incidental to the gate, it is the argument for it. Any figure quoted here is a snapshot, and the implementer must re-derive tree state immediately before acting rather than trusting this document or any earlier turn's reading.

| # | Milestone | Depth in this document | Rationale |
|---|---|---|---|
| P1 | Permission-seam generalization | Objective + exit criteria (§3) | Fix F2 while canonical is still off, so the repair is audited in isolation with no live blast radius |
| P2 | Canonical enablement | Objective + exit criteria (§4) | Fix F1. Flip the flag with a correct authorization path already underneath it. Closes M30.8's real unfinished business |
| M33 | External capability bridge — core | **Full implementation depth (§5-§8)** | The buildable milestone this blueprint specifies |
| M33.1 | Real integrations + Tools & Skills UI | Scope boundaries only (§10) | Deferred; needs external accounts, runtime dependencies, and Hybrid UI's settings surface to be stable |

A fifth, independent item: the F4 provider-key break should be confirmed live and then repaired under its own bounded audit. It is not a dependency of P1 or P2, but it *is* a dependency of M33.1's credential handling. It should not be folded into P1 — mixing two unrelated security repairs into one audit is what this chain is trying to avoid.

**Roles for every milestone in this chain are deliberately unassigned.** That is a User decision recorded during this planning session: role assignment waits until the Hybrid UI initiative closes and it is clear which implementers are free and whether the tree is contended.

---

## 3. P1 — Permission-seam generalization (objective and exit criteria)

**Objective.** Make capability and action authorization correct and vendor-neutral, so that supplying a permission checker enforces authorization instead of bypassing it, and so a non-Gmail capability can declare and be granted its own permissions.

**Scope.** `uri_core/core/multi_action_dispatch.py`, `uri_core/capabilities/executor.py`, `uri_core/capabilities/base.py` (adding action-level declared scopes), and their tests. Backend only. No UI. No new capability.

**Required behavior changes.**

1. `_action_permitted` must consult the checker rather than treat its presence as permission. The `_explicit_permissions` escape must likewise narrow rather than universally allow.
2. `_granted_permissions` must derive granted scopes from the resolver and principal for any capability ID, with the current Gmail behavior preserved as the outcome for Gmail rather than as the implementation.
3. `Action` gains declared required scopes, and `MultiActionExecutor.execute` gains an action-level permission gate between its existing capability-level check (L46) and schema validation.
4. Absence of a checker must deny for capability IDs that are not in the legacy alias map — an additive denial for new IDs, never a relaxation for existing ones.

**Exit criteria.**

- Every existing Gmail, approval-gate and multi-action test passes unchanged: `test_multi_action_capabilities.py` (12), `test_approval_gate.py` (18), `test_decision_gates.py` (27), `test_canonical_execution.py` (36).
- New tests prove: checker present and returning `False` denies (the F2 regression, stated as a named test); unknown capability ID with no grant denies; action-level scope missing denies even when capability-level scope is granted; `_explicit_permissions` narrows rather than universalizes.
- `pytest -q` from the repo root shows zero new failures against the baseline recorded immediately before P1 begins (the M31 figure of 1798/10/7/40 in this document is historical context, not the baseline to diff against — re-record fresh, since P2 and M33 [corrected 2026-09-18, approved cross-reference fix — originally read "M32," the same stale pre-collision-resolution self-reference as line 114; this is the blueprint's own next sequencing step (§2), not the unrelated, already-closed Brain Latency milestone] will each need to do the same and a stale comparison would misattribute failures).
- Independent audit traces the production construction site at `orchestrator.py:270` and confirms what is actually passed, not what is passable.

**Explicitly out of scope for P1:** wiring an `audit_sink`, generalizing `CapabilityContextResolver`, and any registry change. Those belong to M33 [corrected 2026-09-18, approved cross-reference fix — originally read "M32", a stale self-reference from before the M32/M33 identifier collision was resolved (`M32_EXECUTION_ARCHITECTURE_PLAN.md` §0, 2026-09-17); `CapabilityContextResolver` generalization is this blueprint's own §5.2/D6 in-scope work] and must not be smuggled into a security repair.

---

## 4. P2 — Canonical enablement (objective and exit criteria)

**Objective.** Make the canonical path the path that actually serves `/ask`, and discover empirically what breaks when it does.

**Scope.** Turning on `URI_ENABLE_DECISION_ENGINE_LIVE` as a committed, documented default rather than an unset env var; stabilizing whatever the live battery exposes; and recording honestly which legacy modules remain reachable and why.

**Required work.**

1. Decide and document how the flag is supplied — committed default in the server, a checked-in config, or a documented launcher change. An env var that nothing sets is not a cutover.
2. Run the full live battery against the canonical path, not against tests alone. `test_canonical_execution.py`'s 36 tests pass today against a path production does not use; passing tests are not evidence of live correctness.
3. Fix what breaks, within bounded scope. If something requires substantial remediation, define it and stop rather than expanding P2.
4. Re-examine the M30.8 completion record. M30.8 is recorded as COMPLETE with canonical cutover; the live deployment runs legacy. That discrepancy must be recorded as a correction, not quietly resolved.

**Exit criteria.**

- A real `/ask` turn is observed being handled by `run_canonical_for_ask`, evidenced by telemetry or log, not by reading code.
- The legacy fallback still works as a deliberate rollback lever (`CANONICAL_KILLSWITCH`, `CANONICAL_EXECUTION_ALLOWLIST`), and that is demonstrated rather than assumed.
- `orchestrator.py` does not grow. It is currently 6153 lines and grew +361 (`fb02c92`) then +224 (`8fa9ac6`) against the standing must-never-grow rule; P2 must not continue that.
- Full regression with zero new failures, and a recorded live-observation battery.

**Known unknown, disclosed:** nobody currently knows what flipping this flag does to live behavior. That is precisely why P2 is a milestone rather than a line item, and why M33 must not be planned as if the answer were known.

---

## 5. M33 — objective, scope and architecture

### 5.1 Objective

Build one descriptor-driven capability contract, with real authorization, real durable evidence, and real lifecycle, proven end to end through the canonical `/ask` path — entirely offline, with no external vendor, no network dependency, and no paid account.

The proof that the contract is genuinely generic is **subtractive**: migrating `remember_fact` onto it must *delete* a hardcoded branch at `canonical_execution.py:312`, not add a parallel one.

### 5.2 In scope

- A versioned external capability descriptor and its static validator.
- A bounded JSON-schema-subset validator for action inputs **and outputs**.
- A qualification record and lifecycle store (detect → qualify → install/connect → configure → health → enable), with no execution of unreviewed code at any point.
- A registry publisher owning immutable generations, with atomic swap and disable semantics.
- Permission binding from descriptors to the grant store, on top of P1's corrected seam.
- Generalization of `CapabilityContextResolver` beyond Gmail, preserving Gmail behavior exactly.
- A durable, user-scoped `EvidenceStore` implementation plus an operation ledger for asynchronous work.
- `EvidenceRecord` promoted to the authoritative evidence contract, with `orchestrator._make_evidence_item` demoted to a thin adapter over it.
- Three fixture profiles: one in-process, one CLI (a local script), one HTTP (a localhost test server). All offline.
- The `remember_fact` migration pilot.

### 5.3 Explicitly out of scope

Real third-party integrations of any kind; the Tools & Skills settings screen and every Flutter file; any marketplace, scanner, sandbox, signing or reputation system; MCP execution; OpenAPI import; arbitrary dynamic Python import; migration of the other sixteen `uri_core/tools/` modules; any change to `capability_planner.py`'s legacy scoring behavior; any growth of `orchestrator.py`.

### 5.4 Architectural decisions and their justification

**D1 — Reuse the existing descriptor vocabulary rather than invent one.**
`LegacyCapabilityAdapter.from_descriptor` (`uri_core/capabilities/registry.py:82`) already consumes `id`/`name`, `description`, `permissions`, `approval_requirement`, `risk`, and `interface{parameters, returns}` — which is exactly the JSON shape in `uri_workspace/capabilities_registry.json`. The external descriptor wraps that shape as its per-action interface layer and adds only what is genuinely missing: contract version, namespaced identity, source provenance, transport, dependencies, configuration, credential references, intent signals, aliases and lifecycle support. One vocabulary, extended — not two.

Note for the implementer: `registry.py:110` sets `read_only = (approval_requirement == "none")`, conflating approval with read-only. External descriptors must declare an explicit effect class instead of inheriting that conflation.

**D2 — Build the bounded schema validator; do not claim `ActionSchema` already does it.**
`ActionSchema.validate` (`uri_core/capabilities/base.py:88-108`) enforces required-present, unknown-key rejection, and top-level type matching against `_TYPE_NAMES` — and nothing else. It silently ignores `enum`, `minLength`/`maxLength`, `minimum`/`maximum`, `minItems`/`maxItems`, `pattern`, `format`, `items`, nested object properties (**there is no recursion**), `default`, `$ref` and the union keywords. `returns` is stored and surfaced but validated against actual output nowhere in the codebase.

The existing contract's §2 claim that these constructs are "compiled into existing ActionSchema" is false. M33 must build a separate `ExternalActionValidator` that layers on top — enforcing the bounded subset with an explicit maximum nesting depth, on input before execution and on output after — while leaving `ActionSchema` semantics untouched so no existing capability's validation behavior shifts.

**D3 — Registry generations via replacement, not mutation.**
`MultiActionCapabilityRegistry` has `register`, `get_capability`, `capability_summaries`, `describe_capability` — no `unregister`, no generation counter, no atomic swap. Rather than adding removal semantics to a registry whose immutability is currently load-bearing, the publisher builds a **fresh registry instance per generation** and swaps the reference atomically. Disable increments the generation; in-flight work holds an immutable handle to the generation it started under, and any evidence it returns is labeled with that generation.

**D4 — `EvidenceRecord` becomes authoritative; the orchestrator dict becomes a projection.**
`FileEvidenceStore` implements the existing `EvidenceStore` ABC (`add`, `get`, `query`, `resolve`), user-scoped through `portable_paths.user_scoped_path`. `EvidenceLedger` gets constructed in production for the first time and wired into canonical execution. `_make_evidence_item` is rewritten as an adapter that builds an `EvidenceRecord` and renders from it.

The two character bounds are reconciled explicitly rather than unified: `MAX_EXCERPT_LENGTH = 10000` is the **stored** excerpt bound; `_MAX_EVIDENCE_CONTENT_CHARS = 4000` becomes the **model-context projection** bound. They serve different purposes and both must be documented as such, with a test asserting a record stored at 10000 projects at 4000 and discloses truncation.

**D5 — Atomic writes, explicitly not copying the existing pattern.**
`ConversationHistoryStore` (`uri_core/core/conversation_history.py:218-221, 250-252`) writes with a plain `open(path, "w")` + `json.dump` inside `try/except OSError`. There is no temp-file-plus-`os.replace`. A durable evidence and operation store must not inherit that: it writes to a temp file in the same directory and `os.replace`s, so an interrupted write cannot corrupt the ledger. This is called out because copying the nearest existing persistence pattern is the obvious thing an implementer would do, and it would be wrong here.

**D6 — Generalize `CapabilityContextResolver`, preserving Gmail exactly.**
Chained external actions need grounded references between steps. Today `record_action_result` hard-returns for any capability other than Gmail (`context_resolver.py:15`) and `resolve` branches on four Gmail action names. The generalization registers per-capability context extractors declared by the descriptor's provenance support, with Gmail's current behavior registered as the Gmail extractor and asserted byte-identical by the existing tests.

---

## 6. M33 batches

Each batch has its own exit gate and its own rollback point. A scoped pre-batch diff and hash baseline is recorded before any edit, and the established test invocation (`pytest -q` from the repo root) is recorded rather than invented.

### Batch A — descriptor contract, validator, qualification and lifecycle

New: `uri_core/external/contract.py`, `validator.py`, `qualification.py`, `lifecycle.py`, `store.py`.

- Descriptor dataclasses and static validation. Unknown major contract versions and unsupported schema constructs fail closed.
- `ExternalActionValidator` per D2, with bounded nesting depth, input and output validation, and `invalid_output` as a distinct outcome from `no_result`.
- Qualification record bound to exact source revision, dependency lock and profile digest. Detection is static — no importing, no package discovery hooks, no dependency fetching.
- Orthogonal lifecycle state (presence, qualification, configuration, authentication, health, enabled, update_available) rather than one misleading enum, with the UI label derivation order defined as data.
- Reuse `SkillValidator`'s digest and static-validation patterns from `uri_core/skills/skill_installer.py`. Leave `SkillInstaller`'s API and ledger behavior untouched; existing enabled skills stay metadata-only and are never silently promoted to executable.

**Exit:** contract and lifecycle pass their tests, including explicit user-A/user-B isolation for the qualification record, lifecycle store and every path constructed through `user_scoped_path` — two distinct user IDs must never observe or affect each other's qualification, install, or configuration state; no adapter is reachable from any execution path; no registry change yet.

### Batch B — publisher, authorization binding, context generalization, gated dispatch

New: `uri_core/external/registry_bridge.py`, `permission_binding.py`.
Modified: `uri_core/capabilities/context_resolver.py`, `uri_core/core/canonical_execution.py`, `uri_core/core/capability_directory.py`, and bounded metadata extensions in `uri_core/capabilities/base.py` / `registry.py`. Composition in `uri_core/app/server.py`'s existing user-context construction.

- Publisher owns immutable generations per D3.
- Descriptor permissions bind to the grant store on top of P1's corrected seam. New external IDs require explicit grant records and never inherit `CapabilityResolver`'s legacy missing-grant full-registry default.
- `audit_sink` — already a constructor kwarg on `MultiActionExecutor` (L14) and simply never passed — is wired to a real sink on the production path.
- Replace the Gmail-only selection at `canonical_execution.py:312` with a registry lookup. Gmail keeps its behavior through registration, not through a branch.
- Extend `capability_directory.to_summary_dict` (L95) with the `category`, aliases and per-action descriptions it currently drops, and with normalized intent signals. Preserve existing entries with empty optional fields.
- `CapabilityContextResolver` generalization per D6.
- Explicit alias selection binds a turn-scoped `requested_capability_id` from the actual user request, never from model output, with exact normalized alias boundaries.
- Move `remember_fact`/`recall_memory`'s foundational status from the hardcoded `_FOUNDATIONAL_CAPABILITY_IDS` set (`capability_directory.py:138`) to a descriptor field, keeping the hardcoded set as the fallback for anything not yet migrated.

**Exit:** the in-process fixture profile is discovered by a goal-only prompt and executed through the real `/ask` canonical path into Brain-visible evidence; denied cases invoke no adapter; existing Gmail behavior unchanged.

### Batch C — durable evidence and operation ledger

New: `uri_core/external/result_normalizer.py`, `operation_store.py`; `FileEvidenceStore` in or beside `uri_core/core/evidence_fact_integrity.py`.
Modified: `uri_core/core/orchestrator.py` — **adapter rewrite only, and it must not grow the file**; if the adapter cannot be expressed without growth, the evidence helpers move out of `orchestrator.py` entirely, which is the better outcome anyway.

- `FileEvidenceStore` per D4 and D5, user-scoped and atomic.
- `EvidenceLedger` constructed in production and rehydrated on startup.
- Operation ledger persisting job identity, scope, version, budget and session, with a durable completion marker so a completion feeds the canonical Brain exactly once.
- Normalization into `EvidenceRecord` with secret redaction before construction, size validation, and truncation disclosure.

**Exit:** evidence survives restart; a follow-up question resolves the same `evidence_id`; a pending operation survives restart as pending/unknown and is never automatically resubmitted; user A cannot read, list, or rehydrate user B's evidence records or operations through any store path; `wc -l uri_core/core/orchestrator.py` is recorded before and after this batch and shows zero net growth — if the adapter rewrite cannot achieve that, the evidence helpers move out of the file per D4/D5 rather than the batch closing with growth accepted as a tradeoff.

### Batch D — `remember_fact` pilot, CLI and HTTP fixture transports, extensibility proof

New: `uri_core/external/adapters/{cli,http,in_process}.py` and the three fixture profiles.
Modified: `uri_core/core/canonical_execution.py` (branch deletion), `uri_workspace/capabilities_registry.json` (typed interface for `remember_fact`).

**The pilot's principal risk, stated plainly.** `_execute_remember_fact` currently calls `orchestrator.approval_gate.execute_tool("remember_fact", ...)` — the legacy `ToolDispatcher` boundary — and labels its plan `"source": "legacy"`. Migrating to a registry handler routes around `approval_gate`. The migration must prove that `Action.approval_requirement` plus the executor's approval check produce equivalent authorization behavior, and that the returned envelope

```
{"status": ..., "plan": {"status": "capability_selected", "capability": "remember_fact",
                         "action": "remember_fact", "source": ...},
 "execution": {"status": ..., "capability": ..., "action": ..., "raw_status": ...},
 "response": ...}
```

is preserved for every consumer. `remember_fact` also currently has `"interface": null` and a `remember(**kwargs)` signature that extracts content from `request_text`; giving it a typed interface is part of the pilot and must not change its consent semantics (`MemoryStore.add` with `user_provided`).

**Exit:** the hardcoded `capability_id == "remember_fact"` branch is deleted; the third fixture profile is added with descriptor and normalizer only, with a diff proving zero changes to `decision_engine.py`, `canonical_execution.py`, `multi_action_dispatch.py` and `executor.py`.

---

## 7. M33 acceptance criteria

Every criterion below is runnable offline. Each records PASS / FAIL / NOT RUN with exact request, session and operation IDs, redacted logs, evidence IDs and an independent audit reference. All are NOT RUN at the time of writing.

| # | Required proof |
|---|---|
| A1 | Descriptor contract validates in-process, CLI and HTTP fixture profiles; unknown major version and unsupported schema constructs are rejected closed |
| A2 | Bounded validator enforces enum, length, range, item and nesting-depth constraints on input **and** output; malformed output is `invalid_output`, never `no_result`; oversized output is bounded, not truncated silently |
| A3 | `remember_fact` executes through the descriptor path; the hardcoded branch at `canonical_execution.py:312` is gone; the envelope and approval semantics are preserved, asserted field by field |
| A4 | A goal-only prompt discovers a fixture action through `preselect_candidate_ids` → `plausible_matches` and executes it, with no product keyword and no Core branch |
| A5 | Explicit alias selection constrains to exactly that capability; unknown, disabled, unhealthy and missing-action cases report their exact state; no silent fallback, and `task_unsupported` rather than substituting a different action |
| A6 | Authorization: unknown external ID with no grant is denied; a grant revoked between selection and dispatch denies; **a permission checker returning `False` denies** (the F2 regression, re-proved at the M33 layer, not only at P1) |
| A7 | Evidence: `FileEvidenceStore` round-trips; restart rehydrates; a follow-up question resolves the same `evidence_id`; credentials are redacted before record construction; the 10000-character stored bound and 4000-character projection bound both hold and truncation is disclosed |
| A8 | Operation ledger: a pending job survives restart as pending or unknown; a lost submission is `outcome_unknown` and is never resubmitted automatically; duplicate completion is idempotent |
| A9 | Registry generation: disable increments the generation and blocks new invocations immediately; in-flight work from the prior generation is labeled; nothing executes after disable |
| A10 | A third fixture profile is added with descriptor and normalizer only — proven by diff, not by assertion — with zero Core changes |
| A11 | Chaining: a non-Gmail capability grounds a reference from a prior step through the generalized context resolver, and Gmail's existing grounding behavior is unchanged |
| A12 | Full regression: `pytest -q` from the repo root shows zero new failures against the then-current recorded baseline (the M31 baseline was 1798 passed, 10 failed, 7 skipped, 40 subtests passed; P1 and P2 will move it, so the baseline is re-recorded at M33 start rather than copied from here) |
| A13 | Multi-user isolation: two distinct user IDs' qualification records, lifecycle state, evidence records and operations are constructed through `user_scoped_path` and are mutually unreadable and unaffected by each other's install, enable, disable or dispatch actions |
| A14 | `uri_core/core/orchestrator.py` line count at M33 close is less than or equal to its count at M33 start, recorded by `wc -l` before Batch A and after Batch D; any exception is a disclosed, User-approved deviation, not a silent regression of the standing must-never-grow rule |

**Negative and failure-path cases**, each asserted to produce its normalized error code and never a false Ready, false success or empty list: missing executable; broken runtime; missing configuration; missing credential; rejected credential; quota exhausted distinguished from 429 rate-limited; service unavailable; no result; invalid input; invalid output; oversized output; disabled capability; removed capability; stale health; permission revoked after selection; expired qualification; another user's operation or evidence ID; denied approval; explicit tool unavailable; fallback destination outside declared scope; duplicate submission; restart during a pending operation; update failure retaining the previous version; an unknown new action appearing after update.

**Fallback bounds**, unchanged from the existing contract and retained here because they are sound: at most one compatible alternate per failed action, two attempts total, same semantic input/output contract, equal-or-narrower scope; never fall back to installation, enablement, authentication changes or a new data recipient; no fallback for denied, cancelled, approval-required or side-effect `outcome_unknown`; maximum six chained research actions with every step reauthorized.

---

## 8. M33 rollback and compatibility

- Scoped pre-batch patch and metadata backup captured before the first edit of each batch. Never reset the whole dirty tree; never auto-remove shared packages.
- Rollback disables external publication and restores only batch-owned files, retaining all evidence and history. Removing a capability never removes prior answer citations.
- Existing skills metadata, Gmail, local memory, model provider and approval history keep their semantics. No second grants store. Legacy skill entries stay labeled metadata-only.
- The legacy path must continue to fail honestly: under canonical rollback or terminal model failure, an external request must report unavailable rather than falling through to a vaguely matching legacy tool.
- Re-read shared governance and state files immediately before editing them, and prefer a single atomic write over sequential edits — this working tree has a documented history of concurrent writes by other agents.

---

## 9. Corrections register against the Codex drafts

Recorded rather than silently applied. The superseded files remain in place.

| Ref | Codex claim | Correction |
|---|---|---|
| E12 | "legacy `process_user_input` is reached on configured rollback/engine fallback" | Legacy is reached **by default, unconditionally**. The canonical route never runs without `URI_ENABLE_DECISION_ENGINE_LIVE=1`, which nothing sets. This inverts the plan's premise (F1) |
| E5 | "permission stage defaults allowed without checker … external path must wire a real checker" | Understated and, as a remedy, actively harmful. Wiring a checker makes `_action_permitted` return `True` unconditionally (F2). Both halves of the seam must be fixed together, before M33 |
| E7 | "`EvidenceLedger` defaults in-memory" | Understated. `EvidenceLedger` is constructed **zero times in production**; the only shipping evidence transport is `orchestrator.py`'s dict shape (F3) |
| Contract §2 | "Compile representable types into existing `ActionSchema`" for enum, bounds and nested validation | `ActionSchema` validates top-level types only, with no recursion and no constraint keywords, and never validates output. The validator must be built (D2) |
| Contract §4 | "atomically swap the registry generation" | `MultiActionCapabilityRegistry` has no unregister and no generation primitive. Generations require per-generation registry instances (D3) |
| Audit scope | E1–E16 omit `URI_NATIVE_TOOL_AUDIT.md` and `URI_NATIVE_TOOL_PILOTS.md` | Both landed in the inspected commit range and already establish an evidence shape and a `depends_on`/`evidence_provenance` inter-step pattern that the contract re-proposes independently |
| Gmail hardcodings | E4 and E5 list `canonical_execution.py` and `multi_action_dispatch.py` | Two more exist: `context_resolver.py:15` and `capability_directory.py:138`. Four total |
| Plan §4 Batch D | Tools & Skills UI in the same milestone | Deferred to M33.1. Batch D's named Flutter files collide 100% with Hybrid UI Batch 1 and Batch 3 ownership, and `capabilities_settings_screen.dart` already exists with a "System → Capabilities" slot assigned by the Hybrid UI blueprint |
| Plan §3 | Agent Reach and Firecrawl as the fixed reference pair | Deferred to M33.1 planning. M32 proves both transports against offline fixtures; vendor identity is not a contract dependency |
| Scope | Milestone runs from contract through two live vendors and UI | Split. M33 is offline-verifiable core; M33.1 carries vendors and UI |
| E1–E16 line citations | — | **No stale citation found.** Every cited file and line appears to still resolve to what the audit describes — though see §11.1: only a subset of these was re-read directly by this blueprint's author. The corrections above are about interpretation and completeness, not about stale references |

---

## 10. M33.1 — scope boundaries only

Not specified here. Its boundaries: two real integrations exercising the CLI and HTTP transports; the Tools & Skills settings surface; per-user credential configuration; live acceptance tasks against real external sources.

Three prerequisites must be resolved at M33.1 planning, not assumed:

1. **Vendor pair.** The drafted pair carries avoidable cost — Agent Reach is an unreviewed third-party wrapper around `yt-dlp` (not installed here, and needing a JavaScript runtime on Windows), and Firecrawl needs a paid account for which no key exists in `.env`. Running pinned `yt-dlp` directly would deliver the same CLI proof without a supply-chain review. This was left open deliberately.
2. **Credential store.** F4 must be repaired first, or M33.1 builds on a store that raises on construction.
3. **Settings surface.** `capabilities_settings_screen.dart` already exists and the Hybrid UI frozen blueprint §4.7 already assigns it a "System → Capabilities" slot. A new "Tools & Skills" category would be a second, semantically overlapping settings category and needs a deliberate decision, not a parallel screen.

---

## 11. Disclosed unverified items

Stated explicitly because they affect confidence in this blueprint:

- **What P2 will actually break is unknown.** No one has run this deployment with the canonical path live. M33's batches assume a working canonical path; if P2 finds substantial breakage, M33's sequencing may need revision. This is the single largest uncertainty in the chain.
- **F4 was verified by source reading, not by running the server.** The code path is unambiguous (`provider_keys.py:71` raises, `server.py:3007` catches and raises HTTP 500), but a live confirmation was not performed, and it remains possible that the secret is supplied at runtime by a mechanism not visible in the repository or in the Windows environment scopes.
- **`looks_like_credential_value`**, the redaction heuristic `EvidenceRecord.__post_init__` depends on, was not inspected. A7's redaction criterion assumes it is adequate; that assumption should be tested rather than trusted.
- **`dispatch_chain_explicit`'s envelope** was not inspected; only `dispatch_explicit`'s call site was. The pilot's envelope-preservation assertion (A3) covers the single-action case; the chained case needs the same treatment once that envelope is read.
- **Test counts** in §3 and the baseline in A12 are as recorded at the time of writing. P1 and P2 will change both; they are re-recorded at M33 start rather than carried forward.
- **No tests were executed** in producing this blueprint, and no server was started. Everything above is source inspection plus environment inspection.

### 11.1 Evidence provenance — what the author read personally

This matters under this repository's evidence-integrity rules, because delegated inspection is not the same standard of proof as direct reading.

**Read directly by the blueprint's author:** `canonical_execution.py:55-95` and `:300-334`; `server.py:1360-1400`, `:2995-3020`, `:3050-3072`, `:3198-3250`; `multi_action_dispatch.py:285-330`; `decision_gates.py:375-410`; `provider_keys.py:55-95`; `context_resolver.py:1-45`; `capabilities/base.py:88-130`; `registry.py` method list; `executor.py` permission line; `EvidenceLedger` construction default; `orchestrator.py` line count and its per-commit growth via `git log --stat`; the Windows User and Machine environment scopes; the repository-wide search for `URI_ENABLE_DECISION_ENGINE_LIVE`; and the working-tree diff statistics. F1, F2, F3 and F4 all rest on directly read source.

**Established by delegated read-only inspection and not re-read line by line by the author:** the exact key list of `capability_directory.to_summary_dict` (L95); `_FOUNDATIONAL_CAPABILITY_IDS` at L138; `plausible_matches` scoring internals and `preselect_candidate_ids`' threshold behavior; `capability_planner.py`'s 28/45/517 citations; `capability_resolver.py:174`; `skill_installer.py`; the `/skills` route definitions; `conversation_history.py`'s non-atomic write lines; `remember_fact.py`'s signature and its `capabilities_registry.json` entry; the `_execute_remember_fact` envelope field list; the per-file test counts in §3 and A12's baseline; and the claim in §9 that every E1–E16 line citation still resolves at current `HEAD`.

Nothing in the second list changes the chain's shape if it proves inaccurate, but several items feed implementation detail in §6 — particularly the `remember_fact` envelope, which A3 asserts field by field. **The implementer should re-verify the envelope and the `capabilities_registry.json` entry before relying on them**, rather than treating this document as the source of truth for either.

---

## 12. Questions for the independent reviewer

The review should treat these as the places this blueprint is most likely to be wrong:

1. Is P1-before-P2 the right order? The alternative — enabling canonical first and fixing the seam against observed live behavior — trades a known fail-open window for better evidence. This blueprint chose isolation over evidence; is that right?
2. Is `remember_fact` the right pilot? It is the strongest subtractive proof, but it is also foundational, approval-gated and consent-bearing, which makes it the riskiest of the candidates considered.
3. Does D3's per-generation registry replacement hold up under concurrent turns, or does it need explicit reference pinning beyond the immutable handle described?
4. Is D4's split of the 10000 and 4000 bounds into "stored" versus "projected" a genuine reconciliation, or does it preserve a latent inconsistency under a better name?
5. Is Batch C's constraint — rewrite `_make_evidence_item` as an adapter without growing `orchestrator.py` — actually achievable, or should the evidence helpers move out of that file as a precondition rather than as a fallback?
6. Are the twelve acceptance criteria sufficient to declare the contract genuinely generic, or is A10's diff-based no-Core-change proof doing too much of that work alone?

---

## 13. Addendum — Replaceable Brain architectural constraints (User-directed, 2026-09-18, added after freeze)

**This is an additive post-freeze addendum. §§1–12 above are unchanged except the one approved cross-reference correction in §3 (the "M32"→"M33" self-reference).** Recorded per direct User instruction, as constraints and acceptance considerations M33 must satisfy — **not** a requirement to implement M35 (URI Companion Experience & Mini AI) inside M33.

### 13.1 Constraints

- **No provider/model identity in the capability layer.** External capability descriptors (§5.2), the registry publisher (D3), and permission binding (P1) must carry no adapter/provider/model identity anywhere in their own shape — the same discipline `ProviderDescriptor.adapter`/`auth_transports` (`uri_core/core/provider_registry.py`) already applies across cloud API brains, desktop-local brains, and (per this addendum) an optional downloadable mobile-local Brain. A capability must be describable and dispatchable identically regardless of which Brain proposed it.
- **Capability negotiation, conservative by default.** The active Brain must only be offered the subset of capabilities/actions it can actually handle — extending the existing tool-schema-offering discipline (`build_tool_schemas`/`tool_call_translator.py`'s "never dispatch a tool the model wasn't offered" rule) to be Brain-capability-aware, not just registry-driven. **If the active Brain's support for a given capability/action shape is unknown, it must be treated as unsupported and not offered — never assumed supported, never offered speculatively.**
- **Optional mobile-local Brain.** Download/install optional; URI functions fully without it. Already-supported local/offline tasks remain available where the active Brain can handle them. Unsupported or heavier tasks escalate to the configured main Brain.
- **Escalation is explicit routing, never silent substitution.** An escalation from a constrained or local Brain to the main Brain must be a deliberate, visible routing decision — mirroring `ModelRouter`'s own "fail clearly, never silently substitute a different model" discipline (M32 D3) — never an unannounced swap the caller can't distinguish from the original Brain having handled the request itself.
- **Authority boundary, unconditional regardless of active Brain.** Permissions, grants, evidence, and audit stay exactly where M33 core already places them (`ApprovalGate`, `CapabilityResolver`, `EvidenceStore`/`EvidenceLedger`, `AuditTrail`) — never delegated to, inferred from, or bypassable by whichever Brain is currently active. No Brain, cloud or local, gains execution authority a capability's own registry entry doesn't already grant.
- **One integration serves every Brain type.** Switching the active Brain must never require rebuilding or duplicating a capability's own integration — the external-capability descriptor/registry/dispatch layer (§5) is the single integration surface for every Brain, exactly as `ModelProvider`/`ModelRouter` already let M32 D5's streaming work add real functionality with zero duplication across Ollama/Anthropic/OpenAICompatible adapters.

### 13.2 Acceptance considerations

To be specified as formal `A#` rows at M33 planning start (not retrofitted onto the already-NOT-RUN criteria in §7) — recorded here as the considerations those rows must cover:

- A capability descriptor correctly excludes itself from a Brain's offered set when that Brain lacks a declared prerequisite, and does so identically whether the Brain is cloud/API, desktop-local, or mobile-local.
- An unsupported-capability request from a constrained Brain escalates to the main Brain rather than silently failing or fabricating a result; the escalation itself is observable (logged/evidenced), not implicit.
- Permission/evidence/audit behavior is identical across at least two different active-Brain configurations exercising the same capability — proving the authority boundary holds regardless of which Brain is active, not merely asserted.
- An unknown-support case (a capability/action shape the active Brain's negotiation has no data on) is never offered — tested as its own explicit case, not inferred from the "known unsupported" case.

### 13.3 Explicit non-scope

This addendum does not require M33 to implement: the mobile-local Brain itself, any Brain↔Mini-AI escalation/delegation protocol, shared context/state boundaries between Brain and Mini AI, or Companion Mode/robot-face UI integration. Those are M35's scope (`docs/governance/URI_ACTIVE_MILESTONE.md` §1c). M33's obligation under this addendum is architectural: build the capability layer so none of that future work requires rebuilding it.

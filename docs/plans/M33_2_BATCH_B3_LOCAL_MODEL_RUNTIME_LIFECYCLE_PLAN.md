# M33.2 Batch B.3 — Local Model Runtime & Installation Lifecycle

**Status:** DRAFT → ACCEPTED (standing auto-approval, `ORCHESTRATION.md`
§1.5 — implements the architecture boundary the User explicitly authorized
this same session; does not touch core project structure, product
identity, or the security/authority model beyond that authorized
amendment)
**Authorized by:** direct User instruction, 2026-09-20, redefining B.3's
scope after Claude identified a conflict between the original B.3 request
and the frozen canonical architecture's §13 exclusion list, and separately
authorizing the architecture amendment below.
**Depends on:** Batch B.2 `b98620a` (CLOSED/ACCEPTED,
`docs/plans/M33_2_BATCH_B2_STATE.md`); the amended
`docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §13
(amendment recorded 2026-09-20).

## Architecture amendment this plan implements

`docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §13
originally excluded "runtime installation; OS-permission changes" as one
undifferentiated line. Per direct User instruction, that line is split
(auditable correction preserved in the architecture doc itself, not
overwritten silently):

- **Still excluded, unconditionally:** privileged/administrator/elevated
  installation; OS permission changes; system-wide package/runtime
  installation; GPU/driver/CUDA installation; system PATH/environment
  modification; registry/system-service modification; arbitrary
  third-party executable installation; installing anything outside
  URI-controlled storage.
- **Newly permitted, additive:** URI-managed, user-space model and
  portable-runtime lifecycle under deterministic validation and integrity
  controls — this batch's actual scope.

This batch does the minimum architecturally required to implement the
newly-permitted half without ever touching the still-excluded half. Any
implementation task derived from this plan that needs elevated privileges,
OS modification, or installation outside URI-controlled storage is
out-of-scope by definition and must stop and escalate rather than proceed.

## Purpose

URI currently has no mechanism for detecting, adopting, importing,
installing, updating, removing, or tracking the lifecycle of local
model/runtime assets used by the Edge/Second-Brain track. Confirmed by
direct inspection:

- `uri_core/core/edge/runtime_inventory.py`'s `EdgeRuntimeInventory` is an
  explicitly immutable, deployment-owned policy object
  (`"Immutable process/deployment policy. User preferences cannot mutate
  it."`) — it can describe a runtime's declared models, but has no
  install/detect/import/lifecycle behavior at all.
- `uri_core/core/edge/contracts.py` already defines minimal, real, frozen
  target-shape stubs this batch benchmarks/implements against:
  `ModelArtifact(artifact_id, content_hash, model_id)`,
  `ResourceBudget(max_rss_bytes, max_cpu_ms)`,
  `RuntimeInventory(runtime_id, status, models)`, and
  `RuntimeLease(lease_id, runtime_id)` — all currently unused stub shapes.
- The canonical architecture's §10 Resource Governor vocabulary
  (`UNAVAILABLE`, `NOT_LOADED`, `LOADING`, `RESIDENT`, `ON_DEMAND`,
  `SUSPENDED`, `UNLOADING`, `FAILED`) is already frozen and is the runtime
  state vocabulary this batch must reuse, not reinvent.
- The **Main Brain** provider system (`uri_core/core/provider_registry.py`,
  `uri_core/app/server.py:1034`/`3782`) already has
  `OllamaProvider.list_installed_models()` for cloud/local *chat* model
  discovery — this is a separate, existing, working mechanism for the
  Main-Brain provider catalogue and is explicitly **not** duplicated or
  replaced by this batch. B.3 is scoped to the **Edge/Second-Brain**
  perception/reasoner specialist runtime pool
  (`uri_core/core/edge/` and its future lifecycle sibling), which has no
  equivalent today. Where B.3's Ollama/LM Studio detection logic overlaps
  conceptually with the Main-Brain provider system's own detection, B.3
  reuses the same detection *primitives* (e.g. hitting Ollama's local
  `/api/tags`) rather than re-deriving them, but keeps its own registration
  additive and Edge-scoped — it does not modify `provider_registry.py`,
  the Main-Brain provider catalogue, or `GET /providers`.

## Zero-egress boundary: preserved and correctly scoped

Batches A/B/B.1/B.2 established a recursive, tested, zero-egress guarantee
over `uri_core/core/edge/` (no `http`/`httpx`/`requests`/`socket`/`urllib`
import anywhere in that tree, enforced by AST-walk tests in
`test_m33_2_batch_a_edge_foundation.py` and
`test_m33_2_batch_b2_perception_benchmark.py`). URI-managed model/runtime
**download** genuinely requires network access (fetching model weights the
user explicitly requested), which would violate that guarantee if placed
inside `uri_core/core/edge/` itself.

This batch resolves that by **not** placing lifecycle-management code
inside `uri_core/core/edge/`. Instead:

- A new, sibling package (e.g. `uri_core/core/edge_lifecycle/` — exact name
  is an implementation-time naming choice, not an architectural one) holds
  detection, import, download/install/update/remove, checksum/integrity,
  metadata, hardware probing, and registration. This package **is allowed**
  to import `requests` (already declared in `requirements.txt`) and make
  outbound HTTP calls, but **only** inside explicit, user/URI-initiated
  install/update/download functions — never automatically, never as a side
  effect of loading, and never inside any function reachable from the
  existing benchmark/inference path (`vision.py`, `speech.py`,
  `benchmark.py`, `ensemble.py`, `run_benchmark()`).
- The existing `uri_core/core/edge/` zero-egress AST tests are **not
  weakened, relaxed, or given new exceptions** — they continue to assert
  zero egress imports anywhere in that exact tree, unchanged.
- A **new, separate** test asserts the opposite-shaped invariant for the
  lifecycle package: every network-capable call is reachable only from a
  named, explicit set of install/update/download entry points (enumerated
  by the implementer), and the runtime/inference code paths this batch's
  registration feeds into remain unable to trigger a network call on their
  own. This is the same "prove a negative with a named allowlist, not an
  unbounded scan" discipline as the existing zero-egress test, applied to
  the one place in this codebase that is allowed to reach the network for
  a good, explicit, user-serving reason.
- Every network call the lifecycle package makes is logged as evidence
  (URL/host, purpose, byte count, checksum result, timestamp) — this
  mirrors B.1/B.2's "never fabricate, always log truthfully" discipline
  applied to the one place that is allowed to leave the machine.

## Scope: what B.3 implements

### 1. Detection and adoption of existing runtimes
Detect already-installed Ollama (local `/api/tags` or equivalent) and LM
Studio (or compatible OpenAI-compatible local server) installations without
installing or modifying them. Report truthfully: not found / found-but-
unreachable / found-and-reachable, with version where obtainable. Reuses
detection primitives already proven in the Main-Brain provider path (see
Purpose) but registers results into the Edge-scoped inventory, not the
Main-Brain provider catalogue.

### 2. Discovery of already-downloaded models
Enumerate models already present for a detected/adopted runtime (e.g.
Ollama's local model list) without downloading anything.

### 3. Manual model-file import
Accept a user-supplied local model file/directory path, verify it against
a declared checksum/format where the implementer can determine one, and
register it into URI-controlled storage under
`uri_workspace/edge_models/<runtime_id>/<model_id>/` (mirroring the
existing `uri_workspace/users/<user_id>/` user-scoped storage convention in
`uri_core/core/portable_paths.py` — exact path is an implementation detail,
not an architectural one) or leave it in place with a registered reference,
implementer's choice, documented either way.

### 4. URI-managed download/install/update/remove (user-space only)
Download model weights/assets **the user explicitly requested** into
URI-controlled storage, verify integrity (checksum/signature) before
marking a model usable, support update (fetch new version, verify, atomic
swap) and remove (delete from URI-controlled storage, deregister). Never
installs outside URI-controlled storage; never requires elevated
privileges; never modifies OS state, PATH, environment variables, the
registry, or a system service. If a model's runtime genuinely requires a
system-level component URI cannot safely provision in user space (e.g. a
GPU driver), URI: (1) detects whether it already exists, (2) reports the
dependency truthfully, (3) offers manual-adoption/installation guidance,
(4) does not attempt to install it itself.

### 5. Portable/self-contained runtime installation (user-space only)
Where a runtime ships as a genuinely self-contained/portable component
(no OS installer, no elevation, no system-wide registration) and licensing
permits redistribution/local execution, URI may install that component
into URI-controlled storage the same way it installs model weights. This
is explicitly narrower than "install any runtime" — the implementer must
document, per candidate runtime, whether it qualifies (portable, licensed
for this use, no elevation) before attempting it; if not, fall back to
detection/adoption/guidance only (item 1/4's "cannot safely provision"
path).

### 6. Checksum/signature/integrity verification
Every URI-managed asset (downloaded, imported, or installed) is verified
against a checksum before being marked usable. Verification failure keeps
the asset unregistered/unusable and is recorded as evidence, never
silently retried into a false "success."

### 7. Source/version/license metadata
Every registered model/runtime asset records where it came from (URL,
local path, or detected-runtime identity), its version where obtainable,
and its license (or `unknown`, never fabricated).

### 8. Capability and hardware probing
Reuse the existing benchmark harness's resource-instrumentation pattern
(`psutil` RSS, optional `pynvml`/`torch` GPU/VRAM, per
`uri_core/core/edge/adapters/benchmark.py`) to probe what this machine can
actually run — CPU/RAM ceiling, GPU/VRAM where observable, disk space for
a candidate download — before committing to an install, reporting
`unavailable` truthfully where a signal cannot be measured (same
discipline as B.1/B.2, never an invented resource reserve, matching §10's
existing invariant).

### 9. Model/runtime registration
Register a validated asset into an Edge-scoped inventory record shaped
around the existing frozen `RuntimeInventory`/`ModelArtifact` contract
stubs in `contracts.py` (additive fields only, matching B.1/B.2's own
"additive with a default, not a breaking change" discipline for
`BenchmarkResult`). This registration is proposal/observation-tier
infrastructure only — it does not touch `CapabilityDirectory`, the
multi-action capability registry, or any execution-authority surface, per
§12's unchanged compatibility invariants.

### 10. Runtime state management (lazy load/unload)
States are exactly the frozen §10 vocabulary: `UNAVAILABLE`, `NOT_LOADED`,
`LOADING`, `RESIDENT`, `ON_DEMAND`, `SUSPENDED`, `UNLOADING`, `FAILED`. No
new state vocabulary is introduced. No requirement that every registered
model be resident simultaneously — this batch's registration/lifecycle
layer must support lazy, on-demand loading and explicit unloading, per the
architecture's existing "vision/VLM models normally load on demand"
principle (§10) generalized to all Edge-managed models.

### 11. Development Edge-pack provisioning
A named, small, default set of already-benchmarked-shape models/runtimes
(informed by B.1's micro-model ensemble findings and B.2's perception
findings, not re-litigating their candidate selection) that a developer
can provision in one step for local development/testing. This is
tooling/convenience, not a production default — it does not change
`EDGE_ONLY`/`enabled` defaults, which remain §13's own explicitly
unresolved decision, untouched by this batch.

### 12. Safe recovery/rollback for URI-managed assets
If an update/install is interrupted or fails integrity verification, the
previously-working, already-verified asset remains usable (atomic
swap-on-verify, not overwrite-then-verify); a failed operation is recorded
as evidence and leaves the inventory in its last-known-good state, never a
half-registered/ambiguous one.

### 13. Foundational telemetry for a later Developer Log UI
Record, per model invocation attempt (not just install): whether the model
was actually invoked or bypassed and why, latency, RAM/VRAM/CPU usage where
measurable, and network activity for lifecycle operations (item 4's
download log). This batch produces the evidence/telemetry shape only — no
UI is built or wired (see Non-goals).

### 14. Provider-agnostic architecture
No hard-coding to Ollama, LM Studio, Needle, or any specific
model/runtime — detection, import, download, and registration are generic
operations parameterized by runtime/model identity, mirroring B.1/B.2's own
"no architecture hard-coding to a specific model" discipline.

## Explicit non-goals / architecture boundaries

- No privileged/administrator/elevated installation, OS permission
  changes, system-wide package/runtime installation, GPU/driver/CUDA
  installation, system PATH/environment modification, registry/system-
  service modification, arbitrary third-party executable installation, or
  installing anything outside URI-controlled storage (the amendment's
  still-excluded half, unconditionally).
- No UI implementation of any kind (model installation/management UI,
  Experimental Edge Lab, Developer Log/Runtime Evidence UI, voice
  interaction UX, Edge/Main Brain state UI, developer-mode model-
  combination UI) — this batch produces the backend lifecycle/telemetry
  substrate those future M31 UI requirements will consume; recorded here so
  the requirement is not lost, not implemented here.
- No change to `orchestrator.py`, `server.py`, the dispatcher, approval,
  credential, or capability-registry systems, or any execution-authority
  surface. Registered models remain proposal/observation-tier capability
  the same way B.1/B.2's benchmarked candidates were.
- No change to `EdgeRuntimeInventory`'s existing immutability/deployment-
  ownership semantics for the *policy* it already governs — B.3 adds a new,
  separate, lifecycle-managed inventory of *assets*, not a mutation path
  into the existing deployment policy object.
- No relaxation of the existing `uri_core/core/edge/` zero-egress AST
  tests — the lifecycle package's egress is additive, separate, and
  independently tested (see "Zero-egress boundary" above).
- No production promotion, no automatic default-enabling of any installed
  model, no change to `EDGE_ONLY`/`enabled` defaults.
- No requirement that every installed model be resident simultaneously.
- Candidate runtime/model selection for the "development Edge-pack" is
  deferred to implementation-time measurement, same discipline as B.1's
  DeepSeek/Qwen deferral and B.2's OCR/VLM/STT deferral.

## Files expected to change

- New package, e.g. `uri_core/core/edge_lifecycle/` (exact name
  implementer's choice) — detection, import, download/install/update/
  remove, checksum, metadata, hardware-probe, registration, and state
  modules. Sibling to, not inside, `uri_core/core/edge/`.
- `uri_core/core/edge/contracts.py` — additive fields only on
  `ModelArtifact`/`ResourceBudget`/`RuntimeInventory`/`RuntimeLease` if
  genuinely needed (e.g. `source`, `license`, `checksum`, `state`); no
  signature-breaking change; Protocol classes untouched.
- `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` —
  already amended by this plan (§13, above); no further architecture
  change expected during implementation unless a genuinely new boundary
  question surfaces, in which case implementation stops and escalates
  rather than deciding it unilaterally.
- `requirements.txt` — no new dependency expected (`requests` already
  declared); if the implementer finds a genuine need (e.g. a checksum/
  archive library not in the stdlib), it must be flagged explicitly, not
  added silently, per B.1/B.2's own convention.
- New fixture/evidence directory, e.g. `fixtures/m33_2_edge_lifecycle/` or
  `temp_evidence/m33_2_batch_b3/`, for recorded detection/install/
  checksum/telemetry evidence, same provenance discipline as prior
  batches.
- New focused test file(s), e.g.
  `test_m33_2_batch_b3_model_runtime_lifecycle.py`, including the new
  "network calls only from named entry points" test described above.
- New completion report + STATE file at closure
  (`docs/plans/M33_2_BATCH_B3_*`), same pattern as A/B/B.1/B.2.

**Not expected to change:** `orchestrator.py`, `server.py`, dispatcher,
approval, credential, capability registry, any UI file, `routing_policy.py`,
`trace.py`, `uri_core/core/edge/settings.py`'s existing schema,
`provider_registry.py`, `GET /providers`, `EdgeRuntimeInventory`'s
immutability contract.

## Stop condition

Implementation stops at `VERIFICATION_READY` with a completion report
listing: which runtimes/models were detected/adopted/imported/installed in
the test environment and their truthful states; checksum/integrity results;
hardware-probe results; the network-call-boundary test's pass/fail
evidence; and confirmation that no still-excluded (privileged/OS-level)
operation was attempted anywhere in the implementation. No commit/push
until Claude's independent audit runs and returns a verdict, per standing
release authority. No Batch C work, no B.3 UI work, no implementation of
this plan performed by Claude directly — Antigravity routes implementation
to Codex per standing AO-4 routing (complex, multi-file, precision-critical
work, same rationale as B.1/B.2).

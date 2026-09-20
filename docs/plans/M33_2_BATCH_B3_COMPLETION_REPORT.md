# M33.2 Batch B.3 — Local Model Runtime & Installation Lifecycle Completion Report

**Implementation status:** `VERIFICATION_READY`
**Date:** 2026-09-20
**Implementer:** Codex
**Plan:** `docs/plans/M33_2_BATCH_B3_LOCAL_MODEL_RUNTIME_LIFECYCLE_PLAN.md`

## Outcome

Implemented the accepted B.3 scope as the new sibling package
`uri_core/core/edge_lifecycle/`. The package provides confined URI-managed
asset storage, read-only runtime detection, verified manual import, explicit
download/update/remove operations, persistent Edge asset inventory, hardware
capacity observations, lazy lifecycle state management, development Edge-pack
inspection, and allowlisted telemetry.

The implementation does not modify `uri_core/core/edge/`, production routing,
the Main-Brain provider catalogue, the capability registry, execution
authority, or any UI. No model candidate was promoted or enabled.

## Implemented substrate

- `storage.py` confines every managed path beneath
  `uri_workspace/edge_models/<runtime_id>/<model_id>/` using canonical paths,
  strict path-component validation, and `os.path.commonpath` checks.
- `detection.py` probes only explicit loopback URLs for Ollama `/api/tags` and
  LM Studio/OpenAI-compatible `/v1/models`, records detected models, and
  distinguishes `found_reachable`, `found_unreachable`, and `not_found`.
- `integrity.py`, `importer.py`, and `downloader.py` stream SHA-256 calculation,
  fail closed on mismatch, write to staging, and call `os.replace` only after
  verification. Failed downloads remove staging and preserve the verified
  final artifact.
- `inventory.py` atomically persists detected runtime observations and
  verified artifact records with source, version, and truthful license
  metadata (`unknown` when not known). Removal deregisters the asset.
- `hardware.py` reports CPU, RAM, storage, and only observable GPU/VRAM data;
  `can_host_model()` performs disk/RAM admission before provisioning.
- `state_manager.py` implements exactly the frozen state vocabulary:
  `UNAVAILABLE`, `NOT_LOADED`, `LOADING`, `RESIDENT`, `ON_DEMAND`,
  `SUSPENDED`, `UNLOADING`, and `FAILED`.
- `telemetry.py` records lifecycle/network events and invocation attempts from
  an allowlisted schema. It accepts no private reasoning or chain-of-thought
  field.
- `edge_pack.py` declares development-only reflex, language, reasoner,
  OCR/vision, and STT component profiles and reports local availability,
  import/download readiness, or missing prerequisites. It changes no runtime
  defaults.

## Active-environment observations

The explicit detection entry points were run against their default loopback
endpoints. They performed no installation or modification:

- Ollama changed state during verification. The initial probe reported
  `found_unreachable`: the `ollama` command existed, but
  `http://127.0.0.1:11434/api/tags` timed out. After the first full regression,
  the same explicit probe reported `found_reachable` and truthfully enumerated
  `qwen3.5:9b` (6,594,474,711 bytes; digest recorded) and `gemma4:12b`
  (7,556,508,396 bytes; digest recorded). No version header was exposed.
- LM Studio: `found_unreachable`; the `lms` command was detected, but
  `http://127.0.0.1:1234/v1/models` timed out. Version and model identifiers
  were therefore unavailable and reported as such.
- No real model file was imported or downloaded in the active environment.
  The development Edge-pack inspection consequently reported the reflex and
  language profiles as ready for verified manual import, the tiny reasoner as
  ready for verified manual import/adoption, and the OCR/STT profiles as
  unavailable pending their explicitly named local model/runtime prerequisites.

Observed hardware at probe time:

- CPU: 12 physical cores, 24 logical cores, AMD64, observed current frequency
  4276 MHz.
- Memory: 24,500.84 MiB total; 9,159.98 MiB available.
- URI model-storage volume: 76,321.94 MiB free.
- GPU/VRAM: `unavailable`; neither supported observation path exposed a GPU,
  so no GPU or VRAM value was fabricated.

These are point-in-time host observations, not capacity guarantees.

## Integrity, rollback, and egress evidence

The focused tests exercised a valid import, a rejected SHA-256 mismatch, a
successful initial download, a verified atomic replacement, and a corrupted
replacement attempt. After corruption, the staging file was absent and the
previous verified bytes remained intact. Network evidence contained URL/host,
purpose, byte count, timestamp, and `verified`/`mismatch` checksum status.

AST enforcement found `requests` calls only in these named entry points:

- `detect_ollama_runtime`
- `detect_lmstudio_runtime`
- `download_model_artifact`

The recursive zero-egress assertion over `uri_core/core/edge/` passed unchanged.
Inference, benchmark, asset loading, and state-transition paths contain no
network call.

## Still-excluded operations

No privileged or machine-wide installation was attempted. The implementation
does not change OS permissions, machine environment configuration, system
services, registry state, GPU software, or system packages; it does not spawn
installers or subprocesses; and it cannot place managed assets outside the
confined URI storage root. No portable runtime executable was installed because
no candidate was established as self-contained, appropriately licensed, and
safe under the accepted boundary. Existing runtime detection/adoption and
truthful prerequisite reporting are used instead.

## Verification

Focused commands:

- `pytest test_m33_2_batch_b3_model_runtime_lifecycle.py -v` — **9 passed**.
- `pytest test_m33_2_batch_b2_perception_benchmark.py -v` — **16 passed**.
- `pytest test_m33_2_batch_b1_ensemble_benchmark.py -v` — **15 passed**.
- `pytest test_m33_2_batch_b_benchmark.py -v` — **2 passed**.
- `pytest test_m33_2_batch_a_edge_foundation.py -v` — **12 passed**.
- Combined predecessor run — **45 passed**.
- `python -m compileall -q uri_core/core/edge_lifecycle` — passed.
- `git diff --check` — clean except the pre-existing line-ending notice on
  `docs/governance/URI_ACTIVE_MILESTONE.md`.

Full regression:

- First `pytest -q` — **2,242 passed, 10 failed, 7 skipped, 40 subtests passed**
  in 1,099.05 seconds.
- All ten failure names exactly match the accepted Batch B/B.1 baseline set:
  `step3_test.py`, `step4_test.py`, the M20 feasibility/recovery/semantic
  resilience cases, orchestrator session workflow, orchestrator newline guard,
  and workflow restart recovery. No B.3 file or path appears in a failure.
- Pass-count reconciliation: the directive's accepted `2,232` result preceded
  Claude's one-test B.2 audit correction. The resulting pre-B.3 count is 2,233;
  adding B.3's nine passing tests yields exactly 2,242. There are zero new
  regressions.
- A final exact rerun after the last confinement edit produced **2,243 passed,
  16 failed, 0 skipped, 40 subtests passed** in 653.67 seconds. Direct probing
  established that Ollama had become reachable between runs but did not contain
  the configured `qwen3:14b` model. The same ten accepted baseline failures
  remained, while six formerly skipped live tests failed solely because the
  now-reachable service returned `ModelNotFoundError` or a consequent
  `unavailable` result: one M21 context-window live test, two Ollama-provider
  live tests, and three Ollama-reasoning-adapter live tests. The item-count
  reconciliation is exact: the prior seven skips became one pass plus six
  failures. No B.3 source appears in those failures, and B.3 does not start,
  stop, configure, or select the Main-Brain Ollama service/model. This is an
  ambient live-runtime state change, not a B.3 regression; it is disclosed
  rather than hidden by manipulating the service or test environment.

## Infrastructure / harness validation versus real model qualification

**INFRASTRUCTURE / HARNESS VALIDATION COMPLETE:** storage confinement,
loopback-only discovery, inventory metadata, import/download integrity,
atomic rollback, removal/deregistration, hardware probing, capacity admission,
state transitions, Edge-pack inspection, telemetry, and both egress boundaries
are implemented and covered.

**REAL MODEL QUALIFICATION NOT PERFORMED:** neither local service was reachable,
no weights were downloaded or imported, and no real model inference or resource
benchmark ran. This report makes no accuracy, latency, memory-footprint, model
fitness, or production-readiness claim for any Edge-pack candidate. B.1/B.2's
`REAL_CANDIDATE_QUALIFICATION_PENDING` boundary remains unchanged.

## Handoff

Batch B.3 stops at `VERIFICATION_READY`. Claude remains the independent auditor
and release authority. No commit or push was performed.

---

## Addendum: Claude's independent audit, 2026-09-20 (preserved, not overwritten)

**Verdict: VERIFIED — ACCEPT — `INFRASTRUCTURE_VALIDATION_COMPLETE` /
`REAL_MODEL_QUALIFICATION_PARTIAL`.**

Everything above this addendum is Codex's original `VERIFICATION_READY`
report, unmodified. Claude independently re-inspected the plan, this report,
governance records, and every file in `uri_core/core/edge_lifecycle/`
directly, and re-executed evidence rather than trusting the report alone.

### Bounded defect found and repaired

`detect_ollama_runtime`/`detect_lmstudio_runtime` in `detection.py` validated
only the *request* URL as loopback (`assert_loopback_url`), then called
`requests.get(endpoint, timeout=timeout_seconds)` with its default
`allow_redirects=True`. A compromised or malicious process bound to the
loopback detection port could respond with a 3xx redirect to an arbitrary
non-loopback host, and the confinement would be silently bypassed by
`requests` following it — the exact "escape via redirects/URL tricks" risk
this batch's own detection boundary exists to prevent.

Fix (bounded, `detection.py` only): both calls now pass
`allow_redirects=False`; a new `_reject_redirects()` helper inspects the
response before it is trusted and raises (caught by the existing
`requests.RequestException` handler, folding into the normal
`found_unreachable`/`not_found` path) on any 3xx/redirect status. No other
file changed. Added one locking regression test,
`test_runtime_detection_refuses_to_follow_redirect_off_loopback`,
independently reproduced failing against the pre-fix code and passing
post-fix.

### Re-verification

- Focused suite: **10/10** (9 original + 1 new locking test).
- Predecessor suite (B.2 16 + B.1 15 + B 2 + A 12): **45/45**, unaffected.
- `python -m compileall -q uri_core/core/edge_lifecycle`: clean.
- Full regression, run twice independently: the first run overlapped with
  the fix being applied mid-run (files edited during pytest's collection
  phase) and produced one false failure traced to that collection-time
  artifact, not a real defect — discarded. The clean rerun on the final,
  stable code returned **2,244 passed / 16 failed / 0 skipped / 40
  subtests** in 631.79s. All 16 failures were independently reproduced by
  exact name: the same 10 pre-existing baseline failures (`step3_test.py`,
  `step4_test.py`, four M20 feasibility/recovery/semantic-resilience cases,
  orchestrator session workflow, orchestrator newline guard, workflow
  restart recovery) plus 6 tests hardcoded to the `qwen3:14b` model (one M21
  context-window live test, two `test_ollama_provider_live.py` tests, three
  `test_ollama_reasoning_adapter_live.py` tests) — none reference B.3
  source or path. A live `curl http://127.0.0.1:11434/api/tags` probe, run
  independently rather than trusted from the report, confirmed Ollama
  reachable with `qwen3.5:9b` and `gemma4:12b` installed and `qwen3:14b`
  absent — the same environmental characterization this report gave,
  corroborated directly rather than taken on trust.
- `git diff --stat` against the full working tree (not just the files
  Codex listed) confirmed no production routing/approval/dispatcher/
  registry/orchestrator/server/credential/provider-catalogue/UI file was
  touched, and `uri_core/core/edge/contracts.py` was not modified at all.
  Scope stayed inside the accepted B.3 boundary; no still-excluded
  (privileged/OS-level) operation exists anywhere in the package.

### User's real-environment Needle evidence (recorded separately, not backdated)

The following is the User's own manual, real-environment testing, performed
*after* `VERIFICATION_READY` was reached and *not* produced by Codex or
Antigravity's automated report — recorded here as distinct evidence, not
folded into or rewritten as part of the automated infrastructure report
above:

- `cactus-needle` 3.0.2, native engine 3.0.1.
- Real tool routing: PASS.
- Competing-tool selection: PASS.
- Argument extraction: PASS.
- Structured record extraction: PASS.
- Peak RAM: ~108-109 MB.
- `confidence = null` for the tuned checkpoint.
- The `extract()` helper returned `null` once, while raw tool-schema
  extraction passed.
- The installed public API exposes no obvious audio/STT surface —
  classified conservatively as an installed-API/version mismatch, not a
  universal unsupported finding.

This is real tool-use qualification evidence for one candidate's behavior
only. It does not qualify any Edge-pack model end-to-end, and it does not
expand or change B.3's own infrastructure-only implementation scope — hence
`REAL_MODEL_QUALIFICATION_PARTIAL` rather than `PENDING` (B.2's designation)
or `COMPLETE`.

### Disposition

No model was promoted. `EDGE_ONLY`/`enabled` defaults are unchanged. No
Batch C work and no M31 UI implementation were performed or authorized by
this audit. Committed and pushed at `d395c1c`.

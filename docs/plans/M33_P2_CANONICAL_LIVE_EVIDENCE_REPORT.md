# M33 — P2: Canonical Default-On Live Evidence — Completion Report

Blueprint reference: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md` §2.
Context: recovered after a power interruption mid-session. P1
(`docs/plans/M33_P1_PERMISSION_SEAM_COMPLETION_REPORT.md`) was found
already committed and pushed (`69d54ea`, `origin/master` == local
`HEAD`, verified via `git fetch` + `git log origin/master..HEAD` /
`git log HEAD..origin/master`, both empty). P2 itself had not been
run — `scripts/m33_p2_live_evidence.py` existed on disk (untracked)
but no output, report, or state file recorded it ever executing.

## What P1's own report left open

P1 §6/§8 disclosed two concrete, unverified P2 gaps: the
killswitch/allowlist rollback lever had never been live-demonstrated,
and no live-observation battery had been run against
`run_canonical_for_ask` specifically (M32's own live evidence exercised
`native_tool_loop`, a different, still-off-by-default tier). This
report closes both.

## Evidence run — script and method

`scripts/m33_p2_live_evidence.py`, executed against the real FastAPI
app (`uri_core.app.server.app`) via `TestClient`, `run_canonical_for_ask`
and `UriOrchestrator.process_user_input` wrapped with
`unittest.mock.patch(..., wraps=<real function>)` so both still execute
their real bodies — the wrap only counts calls, it changes nothing.
Environment recovery performed before running: local Ollama was down
(fresh dev-machine restart); started it, discovered the packaged
default model (`qwen3:14b`) was not pulled locally. Per explicit user
instruction, did not pull that 9GB+ model — instead routed Task 2
through URI's existing LM Studio / OpenAI-compatible provider path
(already implemented, `uri_core/core/model_providers/openai_compatible_
provider.py`; already catalogued, `provider_registry.py`'s `lm_studio`
entry), which the user already had running with `qwen3-14b` installed.

**Task 3 — canonical default-on, flags unset:**
```
URI_ENABLE_DECISION_ENGINE_LIVE unset -> decision_engine_live_enabled() = True
URI_ENABLE_NATIVE_TOOL_LOOP unset -> native_tool_loop_enabled() = False
URI_CANONICAL_EXECUTION_ALLOWLIST unset -> canonical_killswitch_enabled() = False
```
Confirms the flags themselves resolve correctly purely from being
unset — no server call needed for this one.

**Task 1a — killswitch via EMPTY allowlist (`URI_CANONICAL_EXECUTION_
ALLOWLIST=""`), real `/ask` call:**
```
HTTP status: 200
run_canonical_for_ask call count: 0
process_user_input call count: 1
```
Canonical never reached; legacy served the turn. Rollback lever proven
live, not by reading code.

**Task 1b — killswitch via a NARROW, non-matching allowlist
(`"Gmail,remember_fact"`), real `/ask` call:**
```
HTTP status: 200
run_canonical_for_ask call count: 0
process_user_input call count: 1
```
Confirms `canonical_killswitch_enabled()`'s documented contract: ANY
configured allowlist value is a full kill switch at `server.py`'s outer
gate, not a per-capability narrowing of live traffic — matches the
function's own docstring exactly, not a defect.

**Task 2 — real default `/ask` → `run_canonical_for_ask`, native_tool_
loop disabled, genuine model completion:**

Because `build_provider()` requires a real `principal` for any
non-`ollama` provider (`uri_core/config/model_roles.py:328-334`) — the
anonymous ambient path (`principal=None`, used by Tasks 1a/1b/3 and by
every other test in this codebase's server-wiring suite) cannot reach
LM Studio at all — Task 2 signed up one real, throwaway user via the
production `/auth/signup` endpoint, then configured LM Studio as that
user's Active Brain entirely through existing per-user config seams,
no production code touched:
- `ProviderConfigStore(user_id).set_active_brain("lm_studio", "qwen3-14b")`
  — the same store/method the real Active-Brain-selection UI path uses.
- `ProviderKeyStore(user_id).set_key("lm_studio", <key>)` — the same
  encrypted-at-rest per-user key store every real provider key goes
  through. The raw key came from an `LM_STUDIO_LOCAL_KEY` environment
  variable set at invocation time, never written into the script file,
  never logged, erased from the local variable immediately after the
  store call.
- `URI_PROVIDER_KEY_SECRET` (required by `ProviderKeyStore`'s own
  constructor contract) was set to a random per-run value — this
  encrypts the on-disk key store for the life of this one evidence run
  only; the throwaway user and its `uri_workspace/users/<id>/` directory
  were deleted immediately after the run.

Result, with `Authorization: Bearer <token>` for that real user, no
canonical/killswitch/tool-loop flags set:
```
HTTP status: 200
run_canonical_for_ask call count: 1
process_user_input call count: 0
response status: success
response message: "The user's message is a casual greeting with no
  actionable request or capability trigger."
```
`native_tool_loop_enabled()` reconfirmed `False` immediately before
this call. Canonical was reached (count 1) and answered the turn
directly (legacy call count 0) with a genuine model-generated response,
not a fail-closed "unavailable" — LM Studio (`qwen3-14b`) actually
produced this content, confirmed by `response status: success` (the
prior, pre-recovery attempt against an unpulled Ollama model produced
`response status: unavailable` with a provider-unreachable message —
the contrast is direct proof this run reached a real model).

All four tasks: **PASS**, script exit code 0.

## Cleanup performed after the run

- LM Studio local server stopped (`lms server stop`) — restored to the
  state found at session start (not running).
- Ollama process killed (it was not running at session start either;
  started only to attempt the now-abandoned qwen3:14b pull, which was
  cancelled per user instruction before completion).
- The throwaway `/auth/signup` test user's entire
  `uri_workspace/users/<user_id>/` directory deleted (`git status`
  confirms `uri_workspace/` carries no tracked changes — it is
  gitignored).
- No production code file was modified by this evidence pass. `git
  status` at report time shows only the untracked, already-present
  `scripts/m33_p2_live_evidence.py` (extended, not newly created) and
  pre-existing `graphify-out/` churn — nothing under `uri_core/`.

## P2 exit-criteria re-check (blueprint's own four items)

- Real `/ask` turn observed via genuine execution through
  `run_canonical_for_ask`, not by reading code — **NOW VERIFIED**
  (Task 2, `COMPLETED_WITH_RESULT`, real HTTP 200, real model content).
- Legacy fallback (`CANONICAL_KILLSWITCH`/`CANONICAL_EXECUTION_
  ALLOWLIST`) demonstrated, not assumed — **NOW VERIFIED** (Tasks 1a,
  1b, both real HTTP calls, both call-count-proven).
- `orchestrator.py` does not grow — unaffected by this verification
  pass (no orchestrator.py edit made); still holding per P1's own
  confirmation.
- Full regression, zero new failures — unaffected; no production code
  changed in this pass, so P1's own already-`COMPLETED_WITH_RESULT`
  full-suite run (§4 of the P1 report: 2042 passed / 20 pre-existing
  failures, zero new) remains the current, valid full-regression
  evidence. Not re-run here since nothing changed that could invalidate
  it — re-running would be redundant, not stronger evidence.

**Classification: P2 SATISFIED.** All four blueprint exit-criteria
items are now backed by genuine live evidence gathered in this session,
not by source-reading or prior-milestone inference. The one item this
report cannot independently re-verify — the general full-suite
regression state — was not touched by this pass and remains correctly
attributed to P1's own evidence, per this repository's auditable-
correction-history convention (this is a disclosure, not a gap: no
code changed here that the full-suite run wouldn't already cover).

## Verdict

**P2: VERIFIED.** M33 Batch B is unblocked on both dimensions P1's own
report tracked separately — the permission-seam fix (P1) and the
canonical-default-on live-evidence gap (P2). Batch B has not been
started; this session performed verification only, per explicit
instruction.

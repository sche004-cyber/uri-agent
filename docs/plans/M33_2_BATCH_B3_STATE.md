# M33.2 Batch B.3 — State

**Status:** VERIFIED — ACCEPT (Claude independent audit, 2026-09-20)
**Designation:** `INFRASTRUCTURE_VALIDATION_COMPLETE` /
`REAL_MODEL_QUALIFICATION_PARTIAL`
**Plan:** `docs/plans/M33_2_BATCH_B3_LOCAL_MODEL_RUNTIME_LIFECYCLE_PLAN.md`
**Depends on:** Batch B.2 `b98620a`, CLOSED/ACCEPTED; architecture
amendment to `docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`
§13, recorded 2026-09-20.

## History log

- **2026-09-20 — VERIFICATION_READY → VERIFIED/ACCEPT (Claude independent
  audit):** Independently re-inspected the plan, completion report,
  governance records, and every file in `uri_core/core/edge_lifecycle/`
  directly, re-executing evidence rather than trusting Codex's report alone
  (reran the 9-test focused suite, all 45 predecessor tests, and the
  full-suite regression twice — the first run is discarded as contaminated
  because it overlapped with the fix below being applied mid-run, producing
  one false failure that was a collection-time artifact, not a real defect).

  Found one genuine, bounded defect: `detect_ollama_runtime` and
  `detect_lmstudio_runtime` in `detection.py` used `assert_loopback_url` to
  validate only the *request* URL, then called `requests.get(endpoint,
  timeout=timeout_seconds)` with its default `allow_redirects=True`. A
  compromised or malicious process listening on the loopback detection port
  could respond with a 3xx redirect to an arbitrary non-loopback host, and
  `requests` would silently follow it — bypassing the loopback confinement
  the plan explicitly requires. Applied the smallest bounded fix consistent
  with the frozen plan: both calls now pass `allow_redirects=False`, and a
  new `_reject_redirects()` helper raises before any redirect response is
  trusted, treating it the same as any other unreachable/failed probe. No
  other file was touched. Added one locking regression test,
  `test_runtime_detection_refuses_to_follow_redirect_off_loopback`
  (independently reproduced failing against the pre-fix code, passing
  post-fix).

  Focused suite: 10/10 (9 original + 1 new). Predecessor suite: 45/45,
  unaffected. Clean full regression on the final, stable code: **2,244
  passed / 16 failed / 0 skipped / 40 subtests**, in 631.79s. The 16
  failures were independently reproduced by exact name: the same 10
  pre-existing baseline failures (`step3_test.py`, `step4_test.py`, four
  M20 feasibility/recovery/semantic-resilience cases, orchestrator session
  workflow, orchestrator newline guard, workflow restart recovery) plus 6
  tests hardcoded to the `qwen3:14b` model (one M21 context-window live
  test, two Ollama-provider live tests, three Ollama-reasoning-adapter live
  tests) — none reference B.3 source. A live `curl
  http://127.0.0.1:11434/api/tags` probe, run independently rather than
  trusted from the report, confirmed Ollama reachable with `qwen3.5:9b` and
  `gemma4:12b` installed and `qwen3:14b` absent, corroborating the
  environmental characterization directly. No production routing/approval/
  dispatcher/registry/orchestrator/server/credential/provider-catalogue/UI
  file was touched by B.3, confirmed via `git diff --stat` against the full
  working tree, not just the files Codex listed. Scope stayed inside the
  accepted B.3 boundary; no still-excluded (privileged/OS-level) operation
  exists anywhere in `uri_core/core/edge_lifecycle/`.

  Separately recorded, not backdated and not produced by Codex/Antigravity's
  automated report: the User's own manual, real-environment Needle test,
  performed after `VERIFICATION_READY` — `cactus-needle` 3.0.2, native
  engine 3.0.1: real tool routing PASS, competing-tool selection PASS,
  argument extraction PASS, structured record extraction PASS, peak RAM
  ~108-109 MB, `confidence = null` for the tuned checkpoint, the `extract()`
  helper returning `null` once while raw tool-schema extraction passed, and
  the installed public API exposing no obvious audio/STT surface —
  classified conservatively as an installed-API/version mismatch, not a
  universal unsupported finding. This is real tool-use qualification
  evidence for one candidate only; it does not qualify any Edge-pack model
  end-to-end and does not expand B.3's infrastructure-only scope.

  **Verdict: VERIFIED — ACCEPT — `INFRASTRUCTURE_VALIDATION_COMPLETE` /
  `REAL_MODEL_QUALIFICATION_PARTIAL`** (partial, not pending, specifically
  because of the User's manual Needle evidence above). No model is
  promoted, `EDGE_ONLY`/`enabled` defaults are unchanged, and no Batch C or
  M31 UI work is authorized by this closure. Committed and pushed at
  `d395c1c`.

- **2026-09-20 — ACCEPTED → VERIFICATION_READY (Codex):** Implemented the
  accepted B.3 lifecycle substrate in the new sibling package
  `uri_core/core/edge_lifecycle/` without changing the zero-egress Edge core,
  production routing, authority surfaces, provider catalogue, or UI. Focused
  verification passed 9/9 new tests and 45/45 predecessor tests. The full
  first regression produced 2,242 passed / 10 failed / 7 skipped / 40 subtests;
  all ten failures exactly match the accepted baseline, and the pass-count
  increase reconciles to Claude's one-test B.2 audit correction plus the nine
  B.3 tests. A final exact rerun after the last confinement edit produced 2,243
  passed / 16 failed / 0 skipped / 40 subtests because Ollama became reachable
  between runs while the configured live-test model `qwen3:14b` remained absent:
  the former seven skips became one pass and six environment-driven live-test
  failures. Direct read-only probing confirmed installed `qwen3.5:9b` and
  `gemma4:12b`; no B.3 path appears in any failure and B.3 does not control the
  Main-Brain Ollama service/model. LM Studio remained unreachable. No detected
  model was imported, qualified, or promoted. Hardware and
  integrity/rollback evidence, the still-excluded-operation confirmation, and
  the explicit infrastructure-versus-real-qualification boundary are recorded
  in `docs/plans/M33_2_BATCH_B3_COMPLETION_REPORT.md`. No model was promoted;
  no commit or push was performed.

- **2026-09-20 — Architecture conflict found, then DRAFT → ACCEPTED
  (Claude):** After closing and releasing Batch B.2 (`b98620a`), Claude
  began drafting B.3 per the User's original scope (URI-managed local model
  installation, install/update/remove lifecycle, etc.) and, per the
  Verification-First standard's requirement to inspect primary evidence
  before returning a plan, checked the frozen
  `M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §13 non-goals list.
  Found a direct contradiction: §13 explicitly excluded "runtime
  installation; OS-permission changes" as one undifferentiated item, which
  the User's B.3 request directly conflicts with. Rather than silently plan
  around this or auto-approve past it, Claude stopped and asked the User
  how to resolve it (a genuine architectural-boundary question, per this
  project's own "preserve User review authority" rule). The User chose to
  redefine B.3 directly: authorize a narrow architecture amendment that
  splits the single excluded line into (a) still-excluded, unconditional:
  privileged/OS-level/system-wide installation, OS permission changes,
  GPU/driver installation, PATH/registry/service modification, third-party
  executable installation, and installation outside URI-controlled storage;
  and (b) newly permitted, additive: URI-managed, user-space model and
  portable-runtime lifecycle under deterministic validation and integrity
  controls. Claude applied this amendment to the architecture doc itself
  with full auditable correction history (original line preserved, not
  overwritten), then drafted this plan against the amended boundary.

  The plan additionally resolves a second real conflict Claude identified
  during drafting (not User-raised, found independently per the
  Verification-First standard's "independent defect discovery" rule):
  URI-managed model **download** requires network egress, which would
  violate the existing recursive zero-egress AST tests covering
  `uri_core/core/edge/` if lifecycle code were placed inside that tree.
  Resolution: lifecycle code lives in a new sibling package (outside
  `uri_core/core/edge/`), the existing zero-egress tests are preserved
  unweakened, and a new, separate test proves network calls are reachable
  only from a named, explicit set of install/update/download entry points.

  This is a routine, standing-auto-approved planning extension once the
  boundary and egress questions were explicitly resolved by direct User
  instruction and independent inspection respectively — it does not itself
  touch core project structure or the security/authority model beyond the
  User-authorized amendment. Per standing AO-4 governance, Claude produced
  this plan and the paired architecture amendment, and now stops:
  implementation is routed through Antigravity to Codex, outside this
  session, not performed directly by Claude.

## Routing

Antigravity: pick up this ACCEPTED plan, route implementation to Codex
(multi-file, new-package, precision-critical, security-boundary-adjacent
work fits "complex/precision-critical" routing criteria over Gemma's
bounded-task profile — same rationale used for B.1/B.2), and persist
milestone state through the usual `STATE.md`/completion-report handoff
artifacts this repository already uses for M33.1/M33.2 batches.

**Binding constraint for the implementation task package:** the
implementation task Antigravity writes for Codex must explicitly quote
this plan's "still-excluded, unconditional" list and instruct Codex to stop
and escalate (not implement a workaround) if any part of the work would
require privileged installation, OS permission changes, or writing outside
URI-controlled storage.

## Next action

Antigravity packages the completion report, source diff, generated
evidence, and test results for Claude's independent audit once
implementation reports `VERIFICATION_READY`. Claude determines ACCEPT or
REPAIR REQUIRED. Codex does not self-verify, commit, or push.

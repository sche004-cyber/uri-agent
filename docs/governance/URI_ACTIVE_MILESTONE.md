# URI Active Milestone Control

**Single Authoritative Record of the Current Approved Development Milestone**  
*This file records permissions, scope, and state that have already been approved by the User or accepted project governance. It does NOT grant new permissions by itself.*

---

## 1. Milestone Identity & State

**PRIOR MILESTONE (CLOSED):**  
M30-PFC — Provider-Failure False-Consent Repair — **CLOSED: ACCEPTED**
(User closure instruction, 2026-09-14). CLAUDE ACCEPT verdict, full
evidence trail in `docs/plans/M30_PROVIDER_FAILURE_FALSE_CONSENT_
STATE.md` "2026-09-14: Claude ACCEPT". No new regression found; one
pre-existing, disclosed architecture-debt item (orchestrator.py
newline-count guard, already failing before this repair) does not
block ACCEPT.

**PRIOR MILESTONE (CLOSED):**  
Scenario 2 Connection Gate Repair — **CLOSED: ACCEPTED** (User
approval + Claude implementation + Claude ACCEPT, 2026-09-14). See
`docs/plans/M30_SCENARIO2_CONNECTION_GATE_STATE.md`. Single-file
(`decision_gates.py`) bounded repair; live-reconfirmed real
`DISCONNECTED` + `capability_id: "Gmail"`; zero regression (6 new + 69
existing gate/engine tests passing).

**PRIOR MILESTONE (CLOSED):**  
M30.7C — Canonical Readiness Evidence Closure, RESUMED — **COMPLETE**
(User instruction, 2026-09-14). See `docs/plans/M30_7C_READINESS_
EVIDENCE_CLOSURE_REPORT.md`. M30 readiness ACCEPTED by the User; see
that report for the rebuilt 12-scenario matrix and regression result
(1,743 total items, 8 pre-existing failures, 0 new).

**PRIOR MILESTONE (CLOSED):**  
Architecture revision, PLANNING ONLY — **COMPLETE** (User instruction,
2026-09-14). Two plans produced and returned for review:
`docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md` (Plan A) and
`docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md` (Plan
B, supersedes `M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md` and the
original migration plan's separate M30.8/M30.9/M30.10 rows).

**PRIOR MILESTONE (CLOSED):**  
Graphify Foundation (Plan A) — **CLOSED: ACCEPTED** (User approval +
implementation + verification + Claude ACCEPT, 2026-09-14). See
`docs/plans/M30_GRAPHIFY_FOUNDATION_STATE.md`.

**PRIOR MILESTONE (CLOSED):**  
M30.8 — Canonical Cutover + Legacy Retirement — **CLOSED: COMPLETE — CLAUDE ACCEPT**
(User authorized 2026-09-14; Claude independent audit, bounded repair, Phase A live observation battery, and final ACCEPT recorded in `docs/plans/M30_8_CLAUDE_AUDIT.md` and `docs/plans/M30_8_PHASE_A_OBSERVATION_AND_PHASE_B_DISPOSITION.md`). Full regression 1,759 passed, 16 failed (exact standing baseline + Ollama environment change), 0 new.

**PRIOR MILESTONE (CLOSED):**  
URI Approved UI Functional Prototype — **CLOSED: ACCEPTED**  
(User authorization 2026-09-14; all 4 batches completed, independently audited by Claude, live-verified against running app and approved reference: Batch 1 fixed board framing/13-item nav/unread Gmail; Batch 2 card geometry/honest charts/right-rail fit; Batch 3 responsive scaling/theme propagation/local switching/continuous chat; Batch 4 typography unification/link button contrast repair). Delivered with clean analysis and 23/23 passing tests. Prototype code preserved in working tree.

**PRIOR MILESTONE (CLOSED):**  
M31 — Model & Brain UX — **CLOSED: CLAUDE VERIFIED — COMPLETE**
(Claude independent final audit, 2026-09-16). All 8 live-acceptance
defects and the 3 Round 2 pre-final findings confirmed genuinely fixed
at the source level; 4 additional defects found during this audit and
bounded-fixed in-session (Flutter attachment-chip `Chip`/`RawChip`
collision, stale route-count guard, an LM Studio Active-Brain
regression, and a shared `ModelRouter` test-double signature drift
plus one unguarded best-effort call). Full evidence, all fixes, and
regression results in `docs/plans/M31_STATE.md` ("Claude Final Audit
(2026-09-16) — VERIFIED"). Full `pytest`: 1798 passed, 10 failed (all
10 independently confirmed pre-existing via clean-`HEAD` comparison,
0 new). Full `flutter test`: 135/135. Committed and pushed to
`origin/master` per Claude's standing release authority.

**PRIOR MILESTONE (CLOSED):**  
M32 — Brain Latency / Core Execution Architecture — **CLOSED: CLAUDE
VERIFIED — COMPLETE** (User closure instruction, 2026-09-18: "Final
M32 closure approved"). Batches A–C (canonical cutover, fast/native
tiered path) plus D1–D6 (OAuth refresh persistence, single shared
`CapabilityDirectory` per turn, default-model-resolution correctness
fix, bounded context-probe skip + parallel-tool-worker cap, streaming
`POST /ask/stream`, and a committed/reproducible benchmark harness).
Two headline latency findings (redundant `CapabilityDirectory`
construction; un-persisted OAuth refresh) fixed and re-confirmed fresh
with a 10-iteration real-model measurement; one correctness defect
(default-model resolution) fixed with dedicated regression (58
`test_model_router_*` tests); two resource-exhaustion risks (unbounded
parallel-tool-dispatch threads; unbounded streaming connections) now
bounded and deployment-configurable. Zero regression: 561 passed / 5
failed (all 5 independently confirmed pre-existing, environment-only —
`qwen3:14b` not installed on the dev machine — via clean-HEAD
comparison, 0 new) across the full focused sweep, re-confirmed in this
same closure session. Full evidence, before/after metrics, the final
deferred/residual register, and the milestone-number reconciliation
record are in `docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_
PLAN.md` §10–§15 (§15.10 for the register, §15.11 for the
reconciliation, §15.12 for the CLOSE recommendation this closure
adopts). **Two items explicitly carried forward, NOT resolved by this
closure** — see "M32 residual items, carried forward" below.

**PRIOR MILESTONE (CLOSED):**  
M34 — Model-Native Capability Preservation & Adaptive Scaffolding —
**CLOSED: CLAUDE VERIFIED — COMPLETE** (User closure instruction,
2026-09-19: "Close M34 documentation only... current verified state:
master == origin/master, M34 closure audit verdict: M34 READY TO
CLOSE"). Three accepted, independently audited, committed/pushed
slices:
1. **Graphify Hint Activation** (`78fb5e1`) — activated the existing
   M30 `graphify_index.py` as a per-turn skill/memory orientation hint
   in Turn State and the Brain's decision prompt, behind a killswitch
   (`GRAPHIFY_HINT_ENABLED`), with benchmark evidence and zero
   regression. See `docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_STATE.md`.
2. **C3.3 — Heterogeneous Multi-Capability Routing** (`4aa3478`) — let
   a `multi_action` Decision Contract name actions spanning more than
   one capability without collapsing authority to a single
   `capability_id`, with independent per-capability gating, a
   deterministic aggregate-outcome rollup (reusing the module's own
   established gate-check precedence order, not an invented one), and
   an allowlist derivation fixed to read every effective capability
   directly off the contract rather than off gate internals. Three
   independent audit rounds (Claude, Codex, Claude again) each found
   and fixed a real, execution-verified defect before release. This
   closes item 1 of the "C3.3 — cross-capability native multi-tool
   routing" scope note below — direct execution-level verification in
   this milestone confirmed `MultiActionDispatch` already supported
   capability-heterogeneous chains, so the routing-restriction lift
   did not in fact require M33's P1 fix first, contrary to that scope
   note's original blocked-on-M33 framing (preserved below, not
   deleted, per this file's auditable-correction-history convention).
3. **Attachment-Turn Brain / Tool-Selection Reliability** (`b994270`)
   — resolves the M32 residual item named below (§1, "M32 residual
   items" #2): uploaded-file turns ("summarize this") no longer
   compete against Gmail purely on lexical overlap. `/ask` gained an
   explicit, validated `attached_file_ids` field (authenticated-user +
   session-scoped, fail-closed on unknown/blank/cross-user/cross-
   session/excessive ids); validated references flow as one shared,
   additive `current_turn_attachments` Turn State signal into both the
   canonical and native tool-calling paths; capabilities self-declare
   `reads_current_attachments` (reusing the existing `foundational`
   flag pattern) to be force-included as *candidates*, never force-
   *selected* — Gmail remains fully selectable. `read_attached_file`
   gained an explicit-id execution mode that reads only the referenced
   file(s), never falling back to scanning older session files, while
   preserving the legacy session-scoped behavior exactly when no
   explicit ids are supplied. Independently audited across two rounds
   (a first-round execution-scope gap found and routed back, then a
   second-round final audit that independently reproduced end-to-end
   id-validation and real-dispatch-stack execution-scoping live, not
   merely via unit tests). See `test_m34_attachment_turn_routing.py`
   and `test_read_attached_file.py`.

Every accepted checkpoint above was independently audited by Claude
(source inspection, live re-execution, full regression) before its own
commit/push, per standing AO-4 release authority. Full evidence trail:
this milestone's own audit exchanges (no single `docs/plans/M34_*`
umbrella plan/state pair was created for the C3.3 or attachment-turn
slices — see §6g below for the consolidated closure record).

**CURRENT MILESTONE:**  
None active — M33.2 Batch B.3 is CLOSED / ACCEPTED (B.2 is also CLOSED /
ACCEPTED, see below). No Batch C or M31 UI work is authorized.
**Prior M33.1 closure correction, 2026-09-20:** M33.1 — Real Integrations / Acquire & Manage Abilities is **CLOSED / ACCEPTED**.
None active — M32, M31, and M34 are all CLOSED. Per §1a, the Hybrid UI
initiative's own hard-dependency gate was already opened by M31's own
earlier closure, independently of M32/M34 — see that section for the
initiative's own separate role set and status before any implementation
work begins on it. Neither M32's nor M34's closure opens or affects
that gate.

**M33.2 implementation checkpoint, 2026-09-20:** M33.2 — Edge / Second Brain
Foundation Batch A is **CLOSED / ACCEPTED** at baseline `7e2e093`; its state
and independent-review evidence are in `docs/plans/M33_2_BATCH_A_STATE.md`.
Batch B — the reversible URI-owned benchmark and qualification harness — is
the authorized active implementation scope. No candidate is promoted, and no
Batch C work is authorized by this checkpoint.
The four-stage package is:
`docs/research/M33_2_EDGE_SECOND_BRAIN_ROOT_CAUSE_AUDIT.md`,
`docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md`, and
`docs/plans/M33_2_EDGE_SECOND_BRAIN_MIGRATION_PLAN.md`. Its frozen scope is
proposal/observation intelligence only; URI remains the sole authority for
permissions, approvals, credentials, dispatch, evidence, and execution.
This checkpoint authorizes no Batch A work or production-code change.

**M33.2 Batch B closure, 2026-09-20 (additive):** Batch B — the reversible
URI-owned benchmark and qualification harness — is **CLOSED / ACCEPTED**
after Claude's independent audit (source, diff, live end-to-end run, and a
fresh full-suite re-run, not the prior invalid Windows-temp-ACL
`WinError 5` run). One in-scope defect was found and bounded-fixed: the
Batch A static import-boundary test used a non-recursive glob and never
scanned the new `adapters/` subdirectory; repaired to a recursive scan and
re-verified clean. Full state, evidence, and three disclosed mandatory
carry-forward residuals (unbinned ECE/MCE, presence-only `score_semantics`
validation, 2-item corpus) are recorded in
`docs/plans/M33_2_BATCH_B_STATE.md`. Committed and pushed at
`906c527`. No candidate is promoted; no Batch C work is
authorized. **M33.2 Batch B.1 — Micro-Model Ensemble Qualification** is
authorized as the next active implementation scope by direct User
instruction, 2026-09-20: a further benchmark/qualification-only extension
evaluating non-production Needle 3 / language-generation / tiny-reasoner
configurations. It must not create production language or reasoning
provider contracts (no `EdgeLanguageProvider`, no `EdgeReasoningProvider`),
must not wire any ensemble into production routing, and must not begin
Batch C.

**M32 residual items, carried forward (NOT resolved by this closure):**
1. **Resumed approval across turns** (durable cross-turn pending-
   approval state + natural-language resumption recognition) —
   real, live-demonstrated (Batch B), confirmed still untouched through
   Batch C and D1–D6 (re-checked directly against source in this
   closure session, not merely re-quoted from earlier reports). A
   genuine functional/product gap, out of scope for a latency work
   stream, requiring its own design/implementation. **Destination
   assigned, 2026-09-18: M32.1 — Execution Continuation Residual
   Hardening (see §1c). Assignment is not resolution** — M32.1 is
   NOT STARTED.
2. **Attachment-turn Brain tool-selection reliability** (chose `Gmail`
   over `read_attached_file`) — a model/prompt-reliability finding
   (Batch B), explicitly not independently re-tested since (Batch C's
   own disclosure), out of scope for D1–D6. **Destination assigned,
   2026-09-18: M34 — Model-Native Capability Preservation & Adaptive
   Scaffolding (see §1c). Assignment is not resolution** — M34 is
   NOT STARTED. **Resolved, 2026-09-19 (additive, this line preserved
   verbatim as the original disclosure): M34's "Attachment-Turn Brain /
   Tool-Selection Reliability" slice (`b994270`) closed this item — see
   the PRIOR MILESTONE (M34) entry above.**

Neither item may be treated as resolved, implicitly or explicitly, by
this milestone's CLOSED status, nor by having since been assigned a
destination milestone number. Full detail: `docs/plans/M32_POST_
BATCH_C_LATENCY_ARCHITECTURE_PLAN.md` §15.9–§15.10, §15.14.

**CURRENT STATE:**  
M33.2 Batch B.3 — CLOSED / ACCEPT (Claude independent audit, 2026-09-20).
`INFRASTRUCTURE_VALIDATION_COMPLETE` / `REAL_MODEL_QUALIFICATION_PARTIAL`.

**M33.2 Batch B.1 closure, 2026-09-20 (additive):** Codex completed the
accepted benchmark-only scope and stopped at `VERIFICATION_READY` without
commit or push. Claude's independent audit re-verified every claim against
primary evidence (source reads, a hand-computed ECE/MCE check, independent
focused-suite re-execution, a from-bytes corpus hash recomputation, on-disk
evidence spot-checks, and two independent full-suite regression runs) and
returned **ACCEPT — `HARNESS_COMPLETE` / `REAL_CANDIDATE_QUALIFICATION_PENDING`**,
with one disclosed non-blocking limitation (`reflex_accuracy` is a generic,
not bespoke, tier metric). Focused verification: 29/29. Nine-run evidence
matrix: five qualifying deterministic fixtures, four truthfully unavailable
actual configurations. Full regression, independently reproduced twice:
2,217 passed / 10 failed / 7 skipped / 40 subtests, exact accepted Batch B
failure set, no new regression. See
`docs/plans/M33_2_BATCH_B1_COMPLETION_REPORT.md` and
`docs/plans/M33_2_BATCH_B1_STATE.md`. No candidate is promoted and no Batch C
work is authorized by this closure.

**M33.2 Batch B.2 — Edge Perception Qualification, ACCEPTED, 2026-09-20
(additive):** authorized as the next planning scope by direct User
instruction immediately following the Batch B.1 ACCEPT verdict — an
additive extension of the same benchmark-only harness pattern to Vision
and Audio/Transcription qualification, reusing the frozen Batch A
`EdgeVisionProvider`/`EdgeSpeechProvider` contract stubs and
`vision`/`speech` settings slots as the target shape. During planning,
Claude found genuinely conflicting evidence on Needle 3's documented
audio/transcription capability: direct GitHub/tag inspection (full
recursive tree of `main` and the latest release tag `v3.0.2`, raw
`llms.txt` byte content, `README.md`, and the product page) found no audio
API surface anywhere in the live repository, contradicting indexed
upstream evidence the User separately identified citing a `doc/apis.md`
path with `audio=`/`sample_rate`/`channels` parameters that does not exist
at that path in either inspected ref. Per direct User instruction, this is
recorded as a neutral planning state — `NEEDLE_AUDIO_DOCUMENTATION_CONFLICT
/ RUNTIME_UNVERIFIED` — rather than resolved by assertion in either
direction. Batch B.2's own empirical probe is the tie-breaker: a four-state
classification (`AVAILABLE_SUPPORTED` / `API_PRESENT_RUNTIME_UNAVAILABLE` /
`NOT_SUPPORTED` / `FAILED_QUALIFICATION`) with mandatory reproducibility
recording (installed package version, commit/tag, inspected API
signature), and automatic fallthrough to a provider-agnostic alternative
STT candidate on any non-`AVAILABLE_SUPPORTED` result — the documentation
conflict must never block or manually gate the batch's progress. Full plan
in `docs/plans/M33_2_BATCH_B2_EDGE_PERCEPTION_PLAN.md`; state in
`docs/plans/M33_2_BATCH_B2_STATE.md`. No candidate is promoted, no Batch C
work is authorized, and Claude does not implement B.2 — implementation
routes through Antigravity to Codex/Gemma.

**M33.2 Batch B.2 implementation checkpoint, 2026-09-20 (additive):**
Codex completed the accepted benchmark-only scope and stopped at
`VERIFICATION_READY` without commit or push. Focused verification passed
44/44. The runner wrote nine evidence bundles; deterministic fixtures validate
the harness only, while all actual vision candidates and the faster-whisper
fallback remained truthfully unavailable. The installed-environment Needle
probe classified `NOT_SUPPORTED` (corrected by Claude's audit below to
`PACKAGE_NOT_INSTALLED`) and automatically continued to the alternative STT
path. Full regression: 2,232 passed / 10 failed / 7 skipped / 40 subtests,
the exact accepted B.1 failure set with 15 new B.2 passes and no new
regression. See `docs/plans/M33_2_BATCH_B2_COMPLETION_REPORT.md` and
`docs/plans/M33_2_BATCH_B2_STATE.md`.

**M33.2 Batch B.2 closure, 2026-09-20 (additive):** Claude's independent
audit re-inspected the plan, completion report, governance records, and all
changed/new files directly, re-executing evidence (focused suite, live
runner, two full-suite regressions) rather than trusting the report alone.
Found and bounded-fixed one genuine defect: `probe_needle_audio()` classified
an un-importable needle/cactus_needle module as `NOT_SUPPORTED`, conflating
"package not installed" with the frozen plan's actual `NOT_SUPPORTED`
definition (an installed, introspected API confirmed to lack audio
capability). Added one additive `PACKAGE_NOT_INSTALLED` sub-state to
`NeedleAudioClassification` (speech.py only) plus one locking test;
regenerated the Needle evidence artifact under the corrected classification,
confirmed reproducible. Focused suite: 45/45 (44 + 1 new). Live runner
re-executed independently, reproducing every fixture number bit-for-bit. No
production routing/approval/dispatcher/registry/orchestrator/server/
credential/UI code touched, confirmed against the full working tree.
**Disclosed, out-of-scope, non-blocking:** independent full-suite runs
returned (across two independent runs, pre-fix and post-fix) 12 failed /
2230-then-2231 passed / 7 skipped / 40 subtests, not the claimed
10-failure shape — 2 extra failures in `test_m19_office_readiness.py`
(Gmail/Drive), root-caused to real, gitignored `token.json`/
`credentials.json` OAuth files present on this machine (an environment
state unrelated to B.2's or B.1's code; B.1's own audit reproduced the clean
10-failure shape earlier the same day, before this credential state
existed). Not remediated under B.2's bounded-fix authority — entirely
outside B.2's scope. **Verdict: ACCEPT — `HARNESS_COMPLETE` /
`REAL_PERCEPTION_CANDIDATE_QUALIFICATION_PENDING`.** No candidate is
promoted and no Batch C work is authorized by this closure.

**Architecture amendment + M33.2 Batch B.3 planning, 2026-09-20
(additive):** after closing B.2, Claude began drafting Batch B.3 (Local
Model Runtime & Installation Lifecycle) per the User's original scope and,
per this project's Verification-First standard, checked the frozen
`docs/architecture/M33_2_EDGE_SECOND_BRAIN_CANONICAL_ARCHITECTURE.md` §13
non-goals before returning a plan. Found a direct contradiction: §13
excluded "runtime installation; OS-permission changes" as one
undifferentiated item, which the requested B.3 scope conflicts with.
Claude stopped and asked the User to resolve it rather than silently
planning around it or auto-approving past it. The User authorized a narrow
architecture amendment, applied to §13 with full auditable correction
history (original line preserved, not overwritten): the single excluded
item is split into (a) still-excluded, unconditional — privileged/
administrator/elevated installation, OS permission changes, system-wide
package/runtime installation, GPU/driver/CUDA installation, system PATH/
environment/registry/service modification, arbitrary third-party
executable installation, and installation outside URI-controlled storage;
and (b) newly permitted, additive — URI-managed, user-space model and
portable-runtime lifecycle (detect/adopt existing runtimes, discover/
import/download/install/update/remove models and portable runtime
components inside URI-controlled storage, checksum/integrity verification,
source/version/license metadata, capability/hardware probing, lazy-load
registration and state management, dev Edge-pack provisioning, safe
recovery/rollback) under deterministic validation and integrity controls.
Claude separately identified (not User-raised) that URI-managed download
requires network egress, which would violate the existing recursive
zero-egress AST tests covering `uri_core/core/edge/` if lifecycle code
were placed inside that tree; resolved by scoping lifecycle code to a new
sibling package outside `uri_core/core/edge/`, leaving the existing
zero-egress tests unweakened, with a new test proving network calls are
reachable only from a named, explicit set of install/update/download entry
points. Full plan in
`docs/plans/M33_2_BATCH_B3_LOCAL_MODEL_RUNTIME_LIFECYCLE_PLAN.md`; state in
`docs/plans/M33_2_BATCH_B3_STATE.md`. Status: **ACCEPTED** (planning only).
No implementation performed by Claude; Antigravity routes implementation to
Codex per standing AO-4 routing. No Batch C work is authorized.

**M33.2 Batch B.3 implementation checkpoint, 2026-09-20 (additive):** Codex
completed the accepted scope in the new sibling package
`uri_core/core/edge_lifecycle/` and stopped at `VERIFICATION_READY` without
commit or push. Focused verification passed 9/9. Active-environment
detection found Ollama `found_unreachable` then `found_reachable` between
probes (installed `qwen3.5:9b`/`gemma4:12b`), LM Studio `found_unreachable`
throughout; no model was imported, downloaded, or promoted. Full regression:
2,242 passed / 10 failed / 7 skipped, then 2,243 passed / 16 failed / 0
skipped after Ollama became reachable mid-session (six additional failures
all reference the unrelated, hardcoded `qwen3:14b` live-test fixture, not
installed on this machine). See
`docs/plans/M33_2_BATCH_B3_COMPLETION_REPORT.md` and
`docs/plans/M33_2_BATCH_B3_STATE.md`.

**M33.2 Batch B.3 closure, 2026-09-20 (additive):** Claude's independent
audit re-inspected the plan, completion report, governance records, and
every source/test file directly, re-executing evidence (focused suite,
predecessor suites, two independent full-suite regressions, and a live
`curl` probe of the Ollama loopback API) rather than trusting the report
alone. Found and bounded-fixed one genuine defect: `detect_ollama_runtime`/
`detect_lmstudio_runtime` in `detection.py` validated only the *request*
URL as loopback via `assert_loopback_url`, but called `requests.get` with
its default `allow_redirects=True` — a compromised or malicious process
bound to the loopback detection port could respond with a 3xx redirect to
an arbitrary non-loopback host, and the confinement would be silently
bypassed. Fixed by passing `allow_redirects=False` and explicitly rejecting
any 3xx/redirect response in both functions before it is trusted; added one
locking regression test (`test_runtime_detection_refuses_to_follow_redirect_off_loopback`,
reproduced failing pre-fix, passing post-fix). No other file was touched.
Focused suite: 10/10 (9 + 1 new). Predecessor suite: 45/45, unaffected.
Independently re-ran the full regression twice: the first run overlapped
with the fix being applied mid-run and is discarded as contaminated (one
false failure traced to the file being edited during collection, not a
real defect); the clean rerun on the final, stable code returned **2,244
passed / 16 failed / 0 skipped / 40 subtests**, the exact same 16 failures
independently reproduced by name (10 pre-existing baseline failures +
6 tests hardcoded to the absent `qwen3:14b` model), with zero B.3-attributable
failures. Live `curl http://127.0.0.1:11434/api/tags` independently confirmed
Ollama reachable with `qwen3.5:9b`/`gemma4:12b` installed and `qwen3:14b`
absent, corroborating the environmental-failure characterization rather than
trusting it. No production routing/approval/dispatcher/registry/orchestrator/
server/credential/provider-catalogue/UI code was touched by B.3, confirmed
against the full working tree (`git diff --stat`), not just the files Codex
listed. Scope stayed inside the accepted B.3 boundary; no still-excluded
(privileged/OS-level) operation exists anywhere in the new package.

Also recorded, separately and without backdating (the User performed this
real-world testing after `VERIFICATION_READY`, not before, and it was not
produced by Codex/Antigravity's automated report): the User's manual,
real-environment Needle test — `cactus-needle` 3.0.2, native engine 3.0.1 —
found real tool routing PASS, competing-tool selection PASS, argument
extraction PASS, structured record extraction PASS, peak RAM ~108-109 MB,
`confidence = null` for the tuned checkpoint, the `extract()` helper
returning `null` once while raw tool-schema extraction passed, and the
installed public API exposing no obvious audio/STT surface — classified
conservatively as an installed-API/version mismatch, not a universal
unsupported finding. This is real evidence for one candidate's tool-use
behavior; it does not qualify any Edge-pack model end-to-end and does not
change B.3's own infrastructure-only scope.

**Verdict: VERIFIED — ACCEPT.** **Designation:
`INFRASTRUCTURE_VALIDATION_COMPLETE` / `REAL_MODEL_QUALIFICATION_PARTIAL`**
(partial, not pending, because the User's manual Needle evidence above is
real tool-use qualification for one candidate; every Edge-pack model
remains otherwise unqualified). No model is promoted, `EDGE_ONLY`/`enabled`
defaults are unchanged, and no Batch C or M31 UI work is authorized by this
closure. Committed and pushed at `d395c1c`.

**Correction, 2026-09-19 (auditable, preserving history rather than
silently rewriting it):** the text immediately below this note
previously said "M33 — External Capability Bridge is explicitly NOT
started." That was already false at the time it was written relative
to this repository's own commit history and was never updated as M33
actually proceeded. As of this correction, M33 Batches A
(`b86c6dd`), P1 (`69d54ea`), P2 (`bf71f73`), B (`85eb445`), and now C
(`8926bb4`) are all committed on `master`. Batch C — durable
evidence/operation ledger, sole evidence-authority cutover — is
**CLOSED: CLAUDE VERIFIED — ACCEPTED (2026-09-19)** per Claude's
independent final audit this session: frozen requirements D4/D5 and
acceptance rows A7/A8/A13/A14 confirmed by direct code reading and by
independently rerunning the relevant test suites; one bounded defect
found (an unauthenticated-path `TypeError` in `server.py`'s
`_UserContext` construction, introduced by this batch and untested by
its own new tests) was fixed, reverified, and included in the same
commit; a full `pytest -q` regression (2134 passed, 14 failed, 7
skipped, 40 subtests passed) was independently cross-checked against
unmodified `HEAD` and all 14 failures reproduced identically pre-batch,
confirming zero regressions attributable to Batch C.

**Further correction, 2026-09-19, same day (additive, preserving the
paragraph above rather than editing it):** Batch D (CLI/HTTP/in-process
transports, `remember_fact` common-path migration) is now also
**CLOSED: CLAUDE VERIFIED — ACCEPTED (2026-09-19)**, committed as
`8008ab6`. Verified by Claude's independent audit: all three transport
adapters resolve through `registry_bridge.py`'s single
`transport_handler()` seam with input/output validated by
`ExternalActionValidator`; the CLI adapter cannot be shell-injected
(fixed argv list, `shell=False`, user data only on stdin); the HTTP
adapter's loopback check (`ipaddress.ip_address(...).is_loopback`) was
independently probed against `localhost`, decimal/octal/shorthand
IPv4, `0.0.0.0`, and the IPv4-mapped-IPv6 bypass form
`::ffff:127.0.0.1`, and behaves correctly in every case;
`canonical_execution.py`'s hardcoded `remember_fact` branch and its
`_execute_remember_fact` helper are genuinely deleted, with
`remember_fact` now dispatched as a real `Capability` through the same
path Gmail uses, its authorization boundary traced and confirmed
identical to the pre-migration `CapabilityResolver.is_allowed(...)`
check `ApprovalGate.execute_tool` already used. One bounded defect was
found and fixed in the same commit: a pre-existing M34 test
(`test_m34_c3_3_heterogeneous_routing.py`) mocked the now-deleted
`_execute_remember_fact` symbol as one of three guarded execution
boundaries; updated to the two boundaries that still exist, with the
underlying safety property unchanged. A full `pytest -q` regression
(2140 passed, 14 failed, 7 skipped, 40 subtests passed) shows the
identical pre-existing 14-failure set from the Batch C audit above,
with the one new failure this batch introduced (an `AttributeError`
from the same deleted-symbol mock) root-caused and fixed rather than
merely compared away. Disclosed, non-blocking residual: the HTTP
fixture adapter does not re-validate a redirect's `Location` host
against loopback — not exploitable today (no live untrusted endpoint
exists yet), but must be closed before any M33.1 live HTTP vendor
work.

**Further correction, 2026-09-19, same day (additive):** that
redirect-revalidation prerequisite has now been implemented and is
**CLOSED: CLAUDE VERIFIED — ACCEPTED**, together with **M33.1 Batch 1**
(Connected Service/credential foundations), committed as `d78366d`.
**No frozen M33.1 plan document exists anywhere in this repository** —
only the M33 blueprint's §10 lists M33.1's scope boundaries and three
open prerequisites (vendor pair, credential store, settings-surface
collision); this session's direct User instruction to audit and
conditionally commit is recorded as the explicit authorization this
gate requires for Batch 1 specifically, not as retroactive cover for
Batch 2/3 or for the still-open §10 prerequisites. Verified by Claude's
independent audit: the redirect fix was tested against a real local
server (userinfo/backslash/scheme-change/public-IP/hostname redirects
rejected; `::ffff:127.0.0.1` correctly accepted; a real 2-hop redirect
loop terminates via urllib's own loop detection; a 307 POST body
reaches a second, separately-validated loopback target intact) in
addition to the four adversarial tests Gemini's own implementation
added to `test_m33_batch_d_transports.py`. `ConnectedServiceDescriptor`/
`ConnectedServiceStore`/`ExternalCredentialStore` are architecturally
distinct from the Skill/Capability lifecycle (no shared class or method
surface); `ExternalCapabilityStore.remove()` hard-deletes the descriptor
+lifecycle+credential record in one call, verified by test to produce a
registry generation without the removed capability on re-publish. One
blocking security defect was found and fixed in the same commit:
`ExternalCredentialStore` stored secrets with a plain `json.dump` — a
regression against this repository's own existing, "non-negotiable"
Fernet/PBKDF2 encryption-at-rest policy for this exact class of secret
(`provider_keys.py`'s `ProviderKeyStore`), not an unaddressed new
question. Fixed with the identical pattern under its own secret
(`URI_EXTERNAL_CREDENTIAL_SECRET`); verified empirically that the file
on disk contains only ciphertext and that the wrong secret returns
`None` rather than leaking anything. A full `pytest -q` regression
(2150 passed, 14 failed, 7 skipped, 40 subtests passed) shows the
identical pre-existing 14-failure set from the Batch D baseline, +10
passed matching the 10 new tests this batch added — zero regressions.
Disclosed, non-blocking residuals carried to Batch 2/3: `Connected
ServiceStore`/`ExternalCredentialStore`/the new `connection_status.py`
branch all default to `DEFAULT_USER_STATE_ROOT` rather than reading
`server.py`'s actual configured root (currently inert — nothing in
`server.py` constructs these stores yet); no live endpoint yet
re-publishes the registry after `remove()`; `LifecycleController.
remove()` is implemented but unused outside its own test. **M33.1
Batches 2/3, and its still-open §10 prerequisites (vendor pair,
Tools & Skills settings-surface collision), remain NOT STARTED** —
this correction closes Batch 1 only.

**LOOP_STATE:**  
IDLE (M33.1 Batches 1/2/3 CLOSED / ACCEPTED, 2026-09-19; awaiting explicit User instruction before the M33.1 closure batch)

**M33.1 planning correction, 2026-09-19 (additive):**
`docs/plans/M33_1_REAL_INTEGRATIONS_EXTENSION_VALIDATION_PLAN.md` is now the
authoritative frozen execution plan and Batch 2 entry gate for the remainder
of M33.1. Batch 1 remains **CLOSED / ACCEPTED** (`d78366d`, governance
`0558a99`). User authorization was granted 2026-09-19 for the corrected bounded
**Batch 2 entry slice** (status: `READY_WITH_BOUNDED_ENTRY`): the three §4 residual
corrections (store-root consistency, immediate live removal propagation, and
deletion of `LifecycleController.remove()`) plus the developer-authored,
committed descriptor for pinned `yt-dlp` (`--dump-json`) executing through the
unchanged generic CLI adapter on a stable public URL. Agent-Reach, browser
automation, MCP dependencies, Firecrawl, Batches 3–5, and M33.2 remain excluded.

**M33.1 Batch 2 final independent audit, 2026-09-19 (additive):**
the bounded pinned-`yt-dlp` CLI-Skill acceptance case is **CLOSED / ACCEPTED**
at implementation commit `dd4863a`. The audit verified one configured
user-state root across all three external stores; synchronous full-dispatch
generation replacement on register/configure/enable/disable/remove; immediate
registry, discovery, permission-resolver, execution, and derived-Graphify
retirement; strict per-user isolation; and deletion of the duplicate
`LifecycleController.remove()` authority. The committed developer-authored
descriptor permits only `dump_json`, uses fixed argv with `shell=False`, exact
`yt-dlp==2026.08.19` dependency pin/version enforcement, strict JSON
input/output, bounded timeout/error handling, no credentials, and a
Wikimedia-Commons-only HTTPS URL contract that rejects arbitrary,
loopback/private, userinfo, port, query, and fragment targets. The unchanged
generic descriptor → qualification → registry → CLI adapter → dispatch →
canonical-result/evidence path was exercised; no Agent-Reach, Firecrawl,
browser automation, M33.2 work, `cli.py`, or `orchestrator.py` change entered
the slice.

Focused evidence: 41 passed. Full regression: 2,218 passed, 16 failed, 7
skipped. An independently recreated `0558a99` worktree yielded 2,211 passed,
15 failed, 7 skipped; 14 failure names were identical. The two current-only
M19 failures require an ambient `credentials.json` that pre-dated this slice
(17 Sep) in the main working tree; both pass directly in the isolated baseline
worktree, and the accepted diff does not change Google/Drive code. The one
baseline-only privacy failure likewise follows the isolated worktree's missing
credentials. This is environment-state drift, not a Batch 2 regression.
Batch 3 (GitHub Skill / Package Lifecycle) and the M33.1 closure batch remain
**NOT STARTED**.

**M33.1 roadmap revision, 2026-09-19 (additive):** Firecrawl is removed as an
M33.1 acceptance and closure requirement. The generic HTTP/API bridge remains
available; Firecrawl may be a future optional Connected Service but is not a
dependency for Sources, Watches, crawling, Edge / Second Brain, or Knowledge
Fabric. The next batch is **M33.1 Batch 3 — GitHub Skill / Package Lifecycle**:
one specifically pre-audited immutable GitHub repository/ref must be inspected,
qualified, installed in a URI-managed location, registered, enabled/disabled,
updated, removed, live-retired, and reflected in Discovery/Graphify through
generic contracts. It is **NOT STARTED / BLOCKED ON TARGET SELECTION AND
PRE-AUDIT**. The remaining extension-matrix proof, natural-language/UI lifecycle
seam, compatibility, and regression evidence are consolidated into one later
M33.1 closure batch. M33.2 is reserved for **Edge / Second Brain Foundation**;
M33.3 is reserved for **Unified URI Interaction & Capability UI**; M33.4 is
reserved for **Knowledge Fabric / Sources / Watches**. None is implemented or
opened by this revision.

**M33.1 Batch 3 final independent audit, 2026-09-19 (additive):** the GitHub
Skill/package lifecycle acceptance case (`strip-json-comments-cli`, per
`M33_1_REAL_INTEGRATIONS_EXTENSION_VALIDATION_PLAN.md` §11) is **CLOSED /
ACCEPTED** at implementation commit `0fcdf29`. The audit independently
re-verified, live against the real npm registry and GitHub repository (not
trusted from the plan or the implementation report), that: both pinned
revisions' committed `package.json`/`package-lock.json` pairs have complete,
correct `resolved`/`integrity` fields for their full transitive dependency
tree (4 packages at v3.0.0, ~40 at v2.0.2, all cross-checked hash-for-hash
against the live registry); neither lockfile carries an npm
`hasInstallScript` marker on any entry; the two commit SHAs are the
dereferenced commits, matching npm's own published `gitHead` exactly (a
prior candidate draft had cited the annotated-tag-object SHAs instead,
corrected in plan §11.A before this implementation). Install runs only
`npm ci --ignore-scripts --omit=dev` inside a from-scratch environment that
cannot inherit the real user's `HOME`/`npmrc`/token/cache, staging into a
content-addressed, lockfile-hash-keyed immutable cache via atomic
`os.replace`; a staging failure never touches persisted lifecycle state.
Execution invokes only `[node, cli.js]` with zero positional arguments -
the real `cli.js`'s own optional file-path argument is confirmed
unreachable by construction. `adapters/cli.py`'s new `output: "json"|"text"`
field is confirmed generic (default unchanged, zero effect on the existing
`yt-dlp` descriptor) and no package-specific branch exists anywhere in
`canonical_execution.py`, `multi_action_dispatch.py`, `orchestrator.py`,
`permission_binding.py`, `registry_bridge.py`, or `qualification.py`
(independently grepped, zero matches).

A real, un-mocked end-to-end lifecycle was independently run against the
actual npm registry: install v2.0.2 → register → configure → enable → live
execute → disable (live dispatch denial confirmed) → re-enable (live
dispatch restored) → real staged update to v3.0.0 → live execute → a
rejected re-stage attempt that leaves v3.0.0 fully authoritative and still
dispatchable (previous working version survives a failed update) → remove
with real shared-cache garbage collection, all without a server restart or
context rebuild. Cross-user isolation (User B cannot see, execute, disable,
update, remove, or inherit Graphify entries for User A's installation) and
corrupt-user-state fail-closed behavior (with no leakage to an unaffected
user) were both independently confirmed in the same live test, and the
derived Graphify record was confirmed free of `command`/`runner`/
`credential`/`secret`/`node_modules` content.

Full `pytest -q`: 2,164 passed, 16 failed, 7 skipped, 40 subtests. 14 of the
16 failures are this repository's already-established pre-existing set. The
other 2 (`test_m19_office_readiness.py`'s Gmail/Drive "no credentials"
tests) were independently reproduced identically against the unmodified
pre-Batch-3 baseline with this entire diff stashed away - proving they
depend on this machine's live Gmail/Drive credential/network state, exactly
the same environment-drift pattern already recorded for Batch 2 above, and
not on any code in this commit. Zero regressions attributable to Batch 3.
The M33.1 closure batch (extension-matrix proof, natural-language/UI
lifecycle seam, final regression/live evidence) remains **NOT STARTED**.

**M33.1 Batch 4 final independent closure review, 2026-09-20 (additive):**
M33.1 — Real Integrations / Acquire & Manage Abilities is **CLOSED / ACCEPTED**.
The recovered, uncommitted Batch 4 implementation was reviewed exactly as
survived the power interruption: generic lifecycle catalog/sanitization seam,
deterministic opt-in `/ask` interpreter and authenticated executor closure,
mutation-boundary fail-closed guards, and two acceptance suites. No bounded
production-code fix was required. The accepted matrix is four materially
distinct mechanisms: pinned `yt-dlp` CLI, Gmail OAuth Connected Service,
`remember_fact` in-process capability, and reviewed lockfile-installed
`strip-json-comments-cli` package. Arbitrary `SKILL.md` prose is neither
executed as authority nor double-counted as a fifth mechanism.

Independent isolated Batch 2–4 lifecycle/live evidence: **35/35 passed**.
That includes real `yt-dlp`, real reviewed npm-package lifecycle, and live
`/ask` install/enable/disable/remove, credential-required, isolation and
fail-closed cases. Full recovered-tree regression: **2,175 passed / 23 failed
/ 7 skipped / 40 subtests**. Clean detached `5973f6d` baseline: **2,165 passed
/ 15 failed / 7 skipped / 40 subtests**. Fourteen recovered failures overlap
the baseline; seven transient external DNS/npm/yt-dlp failures later passed in
the isolated rerun; two Drive tests are environment-sensitive and outside all
Batch 4 paths. This is documented test-environment nondeterminism, not an
M33.1 regression.

The lifecycle-intent seam remains opt-in only through
`URI_ENABLE_LIFECYCLE_INTENT_SEAM=1`. M33.3 graphical lifecycle management
remains out of scope. M33.2 planning artifacts remain unrelated, unmodified,
and do not authorize M33.2 implementation. See
`docs/plans/M33_1_REAL_INTEGRATIONS_EXTENSION_VALIDATION_PLAN.md` §13.H for
the binding closure record.

**M31 OBJECTIVE (achieved, preserved for reference):**  
Implement M31 Model & Brain UX per approved Figma frames 02 (node 1:71 — Connect Provider) and 04 (node 1:201 — Chat Model Selector) — API-key + local provider functionality, dynamic model discovery, verified-model inventory, `/providers/{id}/verify`, fallback routing, conversation-level model override, and the two Flutter screens. All items delivered and independently verified per `docs/plans/M31_STATE.md`. `orchestrator.py`-must-never-grow and `/ask`-unchanged-when-override-omitted regression guards both hold (confirmed by this audit's own full regression, not merely re-asserted).

**M31 Critical Invariants (held, now closed with the milestone):**
- Direct-Model Brain Separation: confirmed — zero `subprocess`/`Popen` references to `claude`/`codex` anywhere in `uri_core`.
- Subscription Transport Seam: `subscription_oauth` remains schema-only on `ProviderDescriptor.auth_transports`; Subscription card shows the honest, sourced unavailable state. Unchanged, not implemented in M31 (by design).
- Roadmap Reservation: direct subscription-backed Brain access remains a deferred requirement; M32 stays reserved for external-skill qualification/integration. **[Superseded, 2026-09-18 — preserved verbatim above as the historical M31-era record, not silently edited: M32 was subsequently assigned to Brain Latency / Core Execution Architecture (see the PRIOR MILESTONE entry above) and is now CLOSED. The external-skill-qualification/integration reservation this bullet originally named has been roadmap-reconciled to M33 — see §1b below.]**

**M32 Critical Invariants (held, now closed with the milestone):**
- `run_native_tool_loop()` (`uri_core/core/native_tool_loop.py`) — the central Tier-0/Tier-1 fast-path function this entire work stream builds around — remained completely unmodified throughout D1–D6, confirmed by `git diff --stat` before every commit; every extension (streaming, worker cap) went through its own existing seams (the injectable `model_callable` parameter) rather than editing it.
- No silent model substitution: default-model-resolution failures (D3) fail clearly and never silently pick a different, arbitrary installed model.
- Approvals/grants/audit/dispatch: unweakened throughout, confirmed by full regression after every batch and by the streaming work (D5) specifically proving a late tool call correctly aborts provisional prose and continues through the real, unmodified gate chain (verified against the real `ApprovalGate`/`ToolDispatcher`/`MultiActionDispatch` fixture, not a mock).
- Provider/model-agnostic architecture preserved throughout (D3's default-model fallback logic, D5's `complete_stream()` default fallback for unupgraded providers).
- Roadmap Reservation (current, supersedes the M31-era bullet above): **M33 is reserved for external-skill qualification/integration** — see §1b.

---

## 1a. Queued Initiative (not milestone-numbered): URI Hybrid UI Implementation

**Status:** FROZEN BLUEPRINT (2026-09-16) — planning/review complete;
implementation **not yet started**. See
`docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` (the frozen implementation
blueprint) and `docs/plans/UI_OVERHAUL_IMPLEMENTATION_PLAN.md` /
`docs/design_library/UI_DESIGN_AUTHORITY.md` / `docs/design_library/
COMPONENT_MAPPING.md` / `docs/design_library/UI_ACCEPTANCE_CHECKLIST.md`
(inputs the blueprint incorporates and corrects).

**Roles for this initiative (2026-09-16 explicit User instruction, overrides
the CURRENT MILESTONE (M31) role table in §3 for this initiative only):**
Claude/Codex — planning and independent plan review only; Antigravity —
primary implementer; Qwen 3 14B (local) — implementation review; Antigravity
— repair of Qwen's findings. See `ORCHESTRATION.md` §0 and `AGENTS.md` item 7.

**Mandatory sequencing — hard dependency on M31: GATE OPEN (2026-09-16).**
M31 — Model & Brain UX (§1 above) reached Claude `VERIFIED` and was
committed/pushed to `origin/master` in this same audit pass — see
`docs/plans/M31_STATE.md` ("Claude Final Audit (2026-09-16) — VERIFIED")
for the full evidence trail. The hard dependency that previously blocked
this initiative is satisfied: Antigravity may now initiate UI-initiative
Batch 1 under the role set below. This gate note is preserved for its
own auditable history — the dependency it recorded is resolved, not
retroactively deleted.

**Authorization basis for this queued-initiative record:** direct User
instruction in a live session with Claude, 2026-09-16 ("Accept
READY_WITH_CHANGES... Proceed directly to incorporate your findings and
produce the Frozen UI Implementation Blueprint... Current User-confirmed
development roles are: ..."). This records the frozen blueprint and role
set; it does not advance M31's own state, and it does not authorize UI
implementation to start ahead of the M31 dependency above.

**Naming disambiguation, added 2026-09-18 (governance-level only — the
frozen Hybrid UI documents themselves are not edited; see §1c's M35
entry).** This initiative's existing "Compact" presentation mode — the
420×580 floating chat-window overlay described in `UI_HYBRID_FROZEN_
BLUEPRINT.md` §4.4 and shipped in `UI_HYBRID_BATCH_4_REPORT.md` (all
4 batches report complete, 150–168/168 Flutter tests passing, still
**paused, not accepted, not closed** per commit `7bb916f`) — is
henceforth referred to in governance and roadmap documents as
**"Compact Chat Mode"**, to disambiguate it from M35's distinct new
"Companion Mode" (expressive robot-face interface) concept. It remains
the same feature, same code, same status; only the disambiguating
label is new, and only at the governance level.

**Status, current:** still paused, still not milestone-numbered, still
awaiting User live acceptance and Claude's final audit/release before
it can close — unaffected by M32's closure or by the roadmap additions
in §1c.

---

## 1b. Roadmap Reservation: M33 — External Capability Bridge (renumbered from M32, 2026-09-18)

**Provenance correction, 2026-09-18, same-day follow-up (auditable,
not a silent rewrite of the paragraph below).** This section
originally framed the M32→M33 renumbering as a fresh discovery/
decision made during the same closure session. A subsequent read-only
roadmap audit, later the same day, found that `docs/plans/M32_EXECUTION_
ARCHITECTURE_PLAN.md` §0 ("Identifier collision — RESOLVED") had
**already** authoritatively decided this exact numbering — M32 =
Brain Latency, M33 = External Capability Bridge, M34 = Model-Native
Capability Preservation & Adaptive Scaffolding — on **2026-09-17**,
one day before M32's own D-batches began, and the M33 blueprint
(`M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`, also frozen 2026-09-17)
already built on that same resolution. The 2026-09-18 User instruction
below **ratified and completed the propagation** of an already-decided
number into this governance file — it was not itself the original
numbering decision. The paragraph below is preserved as written at the
time, since it is not factually wrong (the User's instruction was
real and is what caused this file to be updated) — only incomplete
about its own prior history. See `docs/plans/M32_POST_BATCH_C_
LATENCY_ARCHITECTURE_PLAN.md` §15.11 for the same correction applied
to that report.

**Decision:** on M32 (Brain Latency / Core Execution Architecture)'s
closure, the User directly instructed: "Keep M32 = Brain Latency /
Core Execution Architecture. Renumber the unimplemented External
Capability Bridge to M33. Update governance/planning references
consistently." This section records that decision as the current,
authoritative roadmap-numbering state.

**Why this was the cleaner direction (Claude's recommendation, adopted
by the User):** External Capability Bridge has produced planning
documents only and was never authorized to implement — its own state
file, `docs/plans/M32_STATE.md`, records "Implementation: NOT
AUTHORIZED; NOT STARTED." M32 (Brain Latency), by contrast, closes
with substantial shipped, tested, committed work across six D-batches.
Renumbering unimplemented planning work is lower-cost and lower-risk
than renaming a completed work stream's own history.

**A prior session had already partially converged on this same
number, independently.** `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_
BLUEPRINT.md` (dated 2026-09-17, status: FROZEN — planning finality,
implementation NOT AUTHORIZED/NOT STARTED) already exists and already
explicitly supersedes the earlier M32-numbered External Capability
Bridge drafts (`M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`, `../
architecture/EXTERNAL_CAPABILITY_CONTRACT.md`, `../architecture/
M32_CANONICAL_ARCHITECTURE.md`, `../research/M32_ROOT_CAUSE_AUDIT.md`,
`M32_MIGRATION_PLAN.md` — "all Codex drafts, 2026-09-15"). That
blueprint's own §10 states plainly: "Those files remain in place" —
i.e. the established convention in this repository is to supersede a
superseded planning document in place, recording the correction,
never to rename or delete it. This governance update follows that
same convention: **no `docs/plans/M32_*` External Capability Bridge
file has been renamed or deleted.** They remain exactly where they
are, as historical/superseded drafts, exactly as the M33 blueprint
itself already established one day before this reconciliation. This
governance file is simply the first place to formally record that the
number these drafts describe is now M33, matching the already-frozen
blueprint, not a new decision invented here.

**Current authoritative state:**
- **M32 = Brain Latency / Core Execution Architecture — CLOSED.** See the PRIOR MILESTONE entry in §1.
- **M33 = External Capability Bridge — NOT STARTED.** Authoritative planning document: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md` (frozen 2026-09-17; implementation not authorized; additive post-freeze §13 addendum added 2026-09-18, see §1c). Earlier `M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`/`M32_STATE.md`/`M32_CANONICAL_ARCHITECTURE.md`/`M32_ROOT_CAUSE_AUDIT.md`/`M32_MIGRATION_PLAN.md` remain in place as superseded historical drafts, per that blueprint's own §10 and this repository's standing auditable-correction-history convention — not renamed, not deleted.
- **M33.1 = Real Integrations + Tools & Skills UI — NOT STARTED.** Scope boundaries only (blueprint §10); depends on M33 core landing plus the three unresolved prerequisites named there (vendor pair, credential store/F4, settings-surface collision with Hybrid UI).
- **Do NOT begin M33 or M33.1 implementation** without a separate, explicit User instruction — explicitly not authorized by this reconciliation record.

---

## 1c. Roadmap Reservations, 2026-09-18: M32.1, M34, M35

Recorded per direct User instruction ("Approve the consolidated
governance/planning proposal... Apply the pending roadmap items").
All three are reservations/scope records only — **none is started,
none is authorized to begin implementation.**

### M32.1 — Execution Continuation Residual Hardening
**Status:** NOT STARTED. **Scope:** durable resumed approval across
turns only (cross-turn pending-approval state + natural-language
resumption recognition) — the item named in §1's "M32 residual items"
#1. Source: Batch B Completion Report §5/§7; Batch C Completion
Report §10 item 7; `M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md`
§15.9/§15.10. Deliberately narrow — does not absorb any other M32
residual or any M33/M34/M35 scope.

### M34 — Model-Native Capability Preservation & Adaptive Scaffolding
**Status:** **CLOSED: CLAUDE VERIFIED — COMPLETE (2026-09-19).** See
the PRIOR MILESTONE (M34) entry in §1 for the three accepted
checkpoints (`78fb5e1`, `4aa3478`, `b994270`) and §6g for the
consolidated closure record. Originally recorded (2026-09-17) as name-
only, carrying two items forward —
1. **C3.3 — cross-capability native multi-tool routing.** `native_
   tool_loop.py`'s `translate_tool_calls` refuses a Brain tool-call
   batch spanning more than one capability (R12/SR-4). Blocked on P1
   (`multi_action_dispatch._action_permitted`, specified and fixed
   under M33 §3) — but note (from the 2026-09-18 roadmap audit): the
   M33 blueprint fixes P1 only; it does not itself lift `translate_
   tool_calls`'s own restriction. That lift is M34's to do.
   **[Correction, 2026-09-19, preserved not deleted: implementation
   found this "blocked on M33 P1" framing to be inaccurate — direct
   execution-level verification confirmed `MultiActionDispatch`
   already supported capability-heterogeneous action chains, so C3.3
   was implemented and closed under M34 directly, without any M33
   dependency.]**
2. **Attachment-turn Brain tool-selection reliability** — see §1
   item #2 above. **Resolved by the third M34 checkpoint (`b994270`),
   2026-09-19.**

Both items' underlying code was untouched from Batch B/C's own
disclosure until this M34 closure implemented and resolved them.

### M35 — URI Companion Experience
**Status:** NOT STARTED. Net-new concept — no prior documentation
existed anywhere in this repository before the 2026-09-18 roadmap
audit confirmed a zero-match search. **Scope direction (not yet a
detailed plan):**
- Expressive robot-face **Companion Mode** — interactive visual
  states/expressions. Distinct from, and must not be confused with,
  the existing **Compact Chat Mode** (§1a) — same repository, same
  Flutter app, different feature, different name.
- Integration with Compact Chat Mode and the full URI UI.

**Scope correction, 2026-09-20:** M33.2 owns URI's sole Edge / Second-Brain
intelligence architecture, including any bounded Main-Brain preparation,
resource/fallback policy, and its context boundaries. M35 must not create,
rename, or retain a competing Mini-AI architecture, delegation path, or
resource policy. It is limited to Companion Experience presentation and
consumes M33.2's URI-owned contracts when that later milestone is planned.

**Dependency, recorded explicitly:** the last bullet implies M35
integration work has a prerequisite on Hybrid UI (Compact Chat Mode's
home) reaching an accepted/closed state — Hybrid UI is currently
paused, not accepted (§1a). This is a sequencing note, not a hard gate
recorded here the way M31→Hybrid UI's gate was — M35 has no detailed
plan yet for such a gate to attach to.

**Relationship to M34:** M34's model-native capability preservation remains
compatible with this presentation-only M35 scope. M35 does not own a separate
model or intelligence architecture.

---

## 2. Authoritative Files
- `docs/plans/M31_MODEL_BRAIN_UX_PLAN.md`
- `docs/plans/M31_STATE.md`
- `docs/governance/URI_AGENT_RELAY.md`
- `docs/governance/URI_ACTIVE_MILESTONE.md`
- Figma nodes: `1:71` (02 — Connect Provider) and `1:201` (04 — Chat Model Selector)

---

## 3. Authorized Agent Roles (M31 — CLOSED, preserved for reference)

- **Claude:**  
  Visual and architectural authority, plan author, and final architectural auditor / release authority.
- **Antigravity:**  
  Development loop manager / orchestrator, task relay, evidence collection, visual/UX compliance audit against Figma 1:71 and 1:201, and milestone-state maintenance. (Does not edit production code or perform final audit).
- **Codex:**  
  Primary implementer (Codex only) for backend contracts and Flutter UI implementation per accepted M31 plan.
- **User:**  
  Final authority. M31 approval granted, implemented, and Claude-verified/released — see §1.

This role table stood for M31 specifically. §1a's own role table (Claude/Codex planning-and-review only, Antigravity primary implementer, Qwen implementation reviewer) governs the now-open Hybrid UI initiative instead; it does not reuse this table.

---

**WRITE SCOPE (M31 — CLOSED, preserved for reference, no longer an active grant):**  
- `uri_ui/` — Flutter UI files (providers screen, ask_uri screen, composer, models, state, widgets, tests).
- `uri_core/` — backend contracts for M31 (`core/model_router.py`, `core/provider_registry.py`, `app/server.py` for `/providers`, `/providers/{id}/verify`, `/providers/fallback-routing`, `AskRequest.model_override`, `core/fallback_routing_store.py`, `core/turn_state.py`, `core/conversation_history.py`) — strictly respecting that `orchestrator.py` must never grow.
- `tests/` — backend pytest suites for M31.
- `docs/plans/M31_*` — state, reports, verification files.
- `docs/governance/URI_ACTIVE_MILESTONE.md`, `docs/governance/URI_AGENT_RELAY.md`, `PROJECT_MEMORY.md`.
- `uri_workspace/dev_workflow/tasks/` — task directives for Codex and Claude.
- `scripts/run_codex_m31.py` — execution runner script.

No milestone write scope is currently active. The next milestone (or the Hybrid UI initiative, per its own §1a scope) must define its own before implementation starts.

---

## 5. Stop Conditions & Invariants (M31 — CLOSED; invariants below remain standing project-wide, not milestone-scoped)
 
- URI Brain providers are direct-model providers only. Claude Code, Codex, Antigravity, or other development harnesses must NEVER be introduced into the URI Brain runtime. (Confirmed holding by this audit — zero `subprocess`/`Popen` references to `claude`/`codex` anywhere in `uri_core`.)
- `subscription_oauth` is an architectural schema-ready seam on `ProviderDescriptor.auth_transports` only; it remains unimplemented. The Subscription card in Design 02 shows an honest, sourced unavailable state.
- M33 is reserved for external-skill qualification/integration (see §1b — roadmap-reconciled from M32, 2026-09-18; M32 is now used and CLOSED for Brain Latency / Core Execution Architecture, see §1). Direct subscription-backed Brain access is recorded as a deferred requirement for later roadmap reconciliation.
- Only discovered AND verified-usable models are ever selectable anywhere in the product.
- Composer model selector is the single interactive model selector in the product.
- `orchestrator.py` must never grow; keep routing logic in `model_router.py`. (Note: `orchestrator.py` is already at 6153 lines, past the `test_usage_import_boundary.py` guard's 5460 threshold, as of commit `8fa9ac6` — pre-existing, standing architecture debt confirmed to pre-date M31, not a new violation; see `docs/plans/M31_STATE.md`'s final audit section.)
- Preserve existing working code and tests; no regression in existing provider routing or `/ask` calls.
- Do NOT commit or push without separate explicit User instruction.

---

## 6. Next Milestone Status

**NEXT MILESTONE:**  
Roadmap recorded in §1c (2026-09-18): **M32.1** (Execution Continuation Residual Hardening) → **M33** (External Capability Bridge, `M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`, frozen 2026-09-17 + additive §13) → **M33.1** (Real Integrations + Tools & Skills UI) → **M35** (URI Companion Experience & Mini AI). **M34** (Model-Native Capability Preservation & Adaptive Scaffolding) is no longer next — it CLOSED 2026-09-19 (see §1 and §6g) out of the originally-recorded sequence, since none of these items were ever a hard dependency chain except M33.1-on-M33 and M33's own Hybrid-UI-Batch-1 gate (blueprint §2). Direct subscription-backed Brain access remains a separately deferred requirement, still unassigned to any milestone number.

**NEXT MILESTONE STATUS:**  
NOT AUTHORIZED — none of M32.1/M33/M33.1/M35 implementation has been started; each requires its own separate, explicit User instruction to begin (per direct User instruction, 2026-09-18: "Do not begin M33 yet" / "Do not start any milestone yet"). M34 is CLOSED, not pending authorization.

---

## 6g. Closure Record (M34 — Claude VERIFIED, released)

```markdown
VERDICT: VERIFIED
VERDICT AUTHORITY: CLAUDE (independent final audit, per standing AO-4 release authority)
MILESTONE: M34 — Model-Native Capability Preservation & Adaptive Scaffolding
BASIS: Three independently audited slices, each committed and pushed
  separately after its own final audit:
  1. Graphify Hint Activation (78fb5e1) — GRAPHIFY_HINT_ENABLED
     killswitch, capability_index_hint threaded through Turn State and
     the decision prompt, skill/memory-only scope, benchmark evidence
     recorded in docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_STATE.md.
  2. C3.3 Heterogeneous Multi-Capability Routing (4aa3478) — per-action
     capability identity in multi_action contracts, independent per-
     capability gating (no permission/approval inheritance across
     capabilities), deterministic rollup precedence reusing the
     module's own established gate-check order, and an allowlist
     derivation (effective_capability_ids) fixed to read every
     effective capability directly off the contract. Three independent
     audit rounds each found and fixed one real, execution-verified
     defect before release (non-deterministic first-blocker-wins
     rollup; an allowlist-check gap keyed off empty gate sub_results;
     a null-handling gap in per-action capability validation).
  3. Attachment-Turn Brain / Tool-Selection Reliability (b994270) — an
     explicit, validated /ask attached_file_ids field; one shared,
     additive current_turn_attachments Turn State signal consumed
     identically by canonical and native tool-calling; capability-
     declared reads_current_attachments force-includes candidates
     without force-selecting them (Gmail remains selectable);
     read_attached_file's explicit-id execution mode reads only the
     referenced file(s), never falling back to older session files,
     while the no-explicit-id path is byte-identical to the prior
     session-scoped behavior. Two audit rounds: the first found a
     genuine execution-scope gap (routing was correctly scoped but the
     read tool itself still scanned the whole session); the second
     independently reproduced both the fix and live end-to-end
     evidence (id validation and real-dispatch-stack execution
     scoping) that the implementing session's own environment could
     not produce (a Windows TEMP ACL limitation that did not reproduce
     under this audit).
  Full regression run after every slice: zero new failures against
  each slice's own clean-baseline comparison (188/188 passing across
  the attachment-turn slice's eight targeted suites in the final audit
  alone). No parallel discovery/routing/dispatch architecture was
  created by any of the three slices; each reused an existing
  established mechanism (graphify_index.py's own relevant_subset,
  MultiActionDispatch.dispatch_chain_explicit, and the foundational-
  flag preselection pattern, respectively).
RESIDUAL: none blocking. Real /ask-scale latency for the attachment-
  turn signal was not benchmarked end-to-end (isolated FileStore
  lookup overhead measured at ~130us/call, negligible against model-
  call latency) — recorded as open, non-blocking evidence, not a
  defect.
RELEASE ACTION: Claude performed the release commit/push to
  origin/master for each of the three slices per standing release
  authority, on the User's own explicit ACCEPT/commit instruction for
  each slice this session.
TIMESTAMP: 2026-09-19
```

---

## 6f. Closure Record (M32 — Claude VERIFIED, released)

```markdown
VERDICT: VERIFIED
VERDICT AUTHORITY: CLAUDE (independent final audit, per standing AO-4 release authority)
MILESTONE: M32 — Brain Latency / Core Execution Architecture
BASIS: Batches A-C (canonical cutover, fast/native tiered execution
  path) plus D1-D6 (OAuth refresh persistence, single shared
  CapabilityDirectory per turn, default-model-resolution correctness
  fix, bounded parallel-tool-worker cap + context-probe skip,
  streaming POST /ask/stream, committed/reproducible benchmark
  harness). Every acceptance criterion each batch/D-item defined for
  itself is implemented, tested, and independently re-verified. Two
  headline latency findings (redundant CapabilityDirectory
  construction; un-persisted OAuth refresh) fixed and re-confirmed
  fresh with a 10-iteration real-model measurement in this closure
  session, not merely re-cited from earlier batches. One correctness
  defect (default-model resolution) fixed with dedicated regression
  (58 test_model_router_* tests). Two resource-exhaustion risks
  (unbounded parallel-tool-dispatch threads; unbounded streaming
  connections) bounded and deployment-configurable. Streaming
  implemented and real-verified end to end against a live model,
  including a genuine tool-call turn through the completely
  unmodified gate/dispatch chain (native_tool_loop.py has zero diff
  across all of D1-D6, confirmed via git diff --stat before every
  commit). A measurement-confidence question raised after the first
  D6 benchmark pass (multi-tool scenario variance) was independently
  re-investigated in this same closure session and traced to a
  scenario-wording mismatch against the original D1+D2 baseline
  prompt, not a code regression - corrected, and the committed harness
  fixed so it cannot silently drift again. Full regression: 561
  passed / 5 failed (all 5 independently confirmed pre-existing,
  environment-only - qwen3:14b not installed on the dev machine - via
  clean-HEAD comparison, 0 new), re-confirmed fresh in this closure
  session, not merely re-asserted from an earlier batch. Full evidence
  in docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
  §10-§15.
RESIDUAL, EXPLICITLY NOT CLAIMED AS RESOLVED: (1) resumed approval
  across turns (durable cross-turn pending-approval state) - real,
  live-demonstrated in Batch B, confirmed still untouched through
  Batch C and D1-D6 by direct re-inspection of source in this closure
  session; (2) attachment-turn Brain tool-selection reliability -
  disclosed in Batch B, not independently re-tested since. Both carried
  forward per direct User instruction ("Do not claim resumed approval
  or attachment-turn tool selection as resolved") - see the residual
  register in docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md
  §15.10 and the PRIOR MILESTONE entry in §1 above.
RELEASE ACTION: Claude performed the release commit/push to
  origin/master per standing release authority, on direct User
  instruction this session ("Final M32 closure approved... commit D6 +
  final M32 closure + approved milestone-number reconciliation...
  push to master").
TIMESTAMP: 2026-09-18
```

**Follow-up, same day (additive — the VERDICT block above is preserved
verbatim, not edited):** the two RESIDUAL items above were assigned
destination milestone numbers later the same day, per direct User
instruction — resumed approval across turns → **M32.1**; attachment-
turn Brain tool-selection reliability → **M34**. Both remain
explicitly NOT resolved by this closure or by that assignment; see
§1c for the reservation record and §1's "M32 residual items" for the
inline annotation.

---

## 6e. Approval Record (M32 Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M32 — Brain Latency / Core Execution Architecture
APPROVAL BASIS: Explicit User instruction, delivered incrementally
  across D1-D6 and confirmed at final closure: "Final M32 closure
  approved. Roadmap decision: Keep M32 = Brain Latency / Core
  Execution Architecture. Renumber the unimplemented External
  Capability Bridge to M33. Update governance/planning references
  consistently. Preserve the final deferred/residual register exactly
  as reported. Do not claim resumed approval or attachment-turn tool
  selection as resolved." Each individual batch (D1+D2, D3, D4, D5,
  D6) was separately User-verified and separately authorized to
  commit/push before this final closure instruction; see the
  individual commit messages (a6fe87c, 5d76a40, f9cfc92, and this
  closure's own commit) for each batch's own citation of its specific
  authorization.
APPROVAL TIMESTAMP: 2026-09-18
```

---

## 6d. Closure Record (M31 — Claude VERIFIED, released)

```markdown
VERDICT: VERIFIED
VERDICT AUTHORITY: CLAUDE (independent final audit, per standing AO-4 release authority)
MILESTONE: M31 — Model & Brain UX
BASIS: All 8 originally-reported live-acceptance defects and the 3 Round 2
  pre-final findings independently confirmed fixed at the source level
  (not merely re-quoted from Codex/Antigravity's evidence trail). 4
  additional defects found during this audit, all bounded-fixed and
  re-verified in-session (see docs/plans/M31_STATE.md "Claude Final
  Audit (2026-09-16) — VERIFIED" for full detail). Full regression:
  pytest 1798 passed / 10 failed (all 10 confirmed pre-existing via
  clean-HEAD comparison, 0 new); flutter test 135/135; flutter analyze
  0 errors.
RELEASE ACTION: Claude performed the release commit/push to
  origin/master per standing release authority, on direct User
  instruction this session ("If VERIFIED, perform the authorized M31
  release checkpoint... commit/push M31").
TIMESTAMP: 2026-09-16
```

---

## 6c. Approval Record (M31 Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M31 — Model & Brain UX
APPROVAL BASIS: Explicit User instruction: "M31 — Model & Brain UX is ACCEPTED and ready for execution. Please take ownership of URI_ACTIVE_MILESTONE.md as required by AO-4, set M31 as the active milestone, and initiate the established execution loop. Route implementation to Codex only."
APPROVAL TIMESTAMP: 2026-09-15
```

---

## 5a. Approval Record (M30-PFC Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30-PFC
APPROVAL BASIS: Explicit User instruction: "I approve implementation of
  the finalized M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_PLAN.
  Proceed with the bounded repair exactly as planned... M30.8 remains
  NOT AUTHORIZED until this repair receives Claude ACCEPT."
APPROVAL TIMESTAMP: 2026-09-13
```

Authorizes exactly the scope in `docs/plans/M30_PROVIDER_FAILURE_
FALSE_CONSENT_REPAIR_PLAN.md` and §4/§5 above - the primary
model-failure-state gate, the empty-match defense-in-depth, the 8
required tests, live re-verification, and full regression. Does not
authorize M30.8, does not authorize any redesign beyond this exact
gate, and does not authorize commit/push.

---

## 6a. Approval Record (M30.7C Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30.7C
APPROVAL BASIS: Explicit User instruction: "I approve a bounded M30.8
  readiness evidence-closure pass. Scope is limited to: MANDATORY -
  Scenario 2 ... Scenario 8 ... Scenario 12 ...; BEST EFFORT -
  Scenario 7 ...; DO NOT REOPEN - Scenario 5, 9, 4. No production
  source changes are authorized unless an unexpected real defect is
  discovered. If a defect is discovered, stop and return for scope
  approval rather than repairing it automatically."
APPROVAL TIMESTAMP: 2026-09-13
```

This approves exactly the scope in
`docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_PLAN.md` - it does
**not** authorize M30.8, does not authorize any source change absent a
real discovered defect (and even then, only after a further, separate
approval), and does not authorize commit/push. Scenarios 4, 5, and 9
are explicitly excluded from this milestone and must not be reopened.

---

**BLOCKERS / PREREQUISITES BEFORE M30.8 CAN BE AUTHORIZED:**
1. Scenarios 2, 5, 7, 8, 12 still lack full live canonical closure:
   - Scenario 2 never reaches real `DISCONNECTED` gate outcome.
   - Scenario 5 model performs a one-time search instead of an honest refusal for recurring automation.
   - Scenario 7 lacks a real attachment-bearing email to complete the chain.
   - Scenario 8 pre-approval draft-content envelope is unobserved (approval boundary itself is proven).
   - Scenario 12 visible end-user provider-unavailable fallback message is unconfirmed.
2. Scenario 9 (`convert_document`) is confirmed `BLOCKED_BY_CURRENT_SCOPE` (not Layer-3 schema/executor-ready).
3. M30.2 `WorkflowPlanner` template inventory is confirmed absent across repository artifacts.


---

## 6b. Approval Record (M30.7B Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: CLAUDE
APPROVED MILESTONE: M30.7B
APPROVAL BASIS: Explicit User instruction: "I approve M30.7B — Canonical
  Readiness Closure. Record my approval in
  docs/governance/URI_ACTIVE_MILESTONE.md and initiate the loop."
APPROVAL TIMESTAMP: 2026-09-13
```

This approval authorizes M30.7B exactly as scoped in
`docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md` - root-cause-
first investigation of 6 named scenarios, one decision (scenario 9),
and at most the two conditional source changes named in §4. It does
**not** authorize M30.8, does not authorize any source change beyond
those two conditional boundaries, and does not authorize commit/push.
The User explicitly directed: "Keep M30.8 NOT AUTHORIZED. Do not
expand beyond the two conditional source-change boundaries already
defined in the M30.7B plan" - both instructions are binding invariants
for this milestone, not merely defaults.

---

## 6a. Prior Approval Record (M30.7A Authorization)

```markdown
USER APPROVAL: APPROVED
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M30.7A
APPROVAL BASIS: Explicit User request: "Create a bounded milestone: M30.7A — CANONICAL LIVE EVIDENCE CLOSURE ... to claude"
APPROVAL TIMESTAMP: 2026-09-13
```

M30.7 was closed (`LIVE_VERIFIED + CLAUDE ACCEPT (documented residual)`). M30.7A was explicitly authorized by the User to close the missing live evidence for all 12 mandatory canonical scenarios before M30.8 can be considered. State transitioned to M30.7A (`PLANNING`).

Note: this approval authorizes starting M30.7A. It does NOT authorize starting M30.8 or committing/pushing.

### Confirmation (2026-09-13, given directly to Claude)

Claude's own M30.7A plan (`docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_PLAN.md`)
had flagged the relay-channel deviation above for the User's awareness,
not silently accepted it. The User has since directly confirmed it:

```markdown
APPROVAL AUTHORITY: USER
APPROVAL RELAY: USER DIRECT
APPROVED MILESTONE: M30.7A
PROTOCOL NOTE: This was a one-off direct approval given by the User
  outside the normal Claude-relay channel. It does not change the
  standing protocol.
CONFIRMATION TIMESTAMP: 2026-09-13
```

**Standing protocol, restated and unchanged by this confirmation:**
User approvals for future milestone advancement should normally be
communicated through Claude (per §7's User Approval Channel Protocol)
and then recorded into this shared governance file. This M30.7A
approval is a User-confirmed, valid, one-off exception - it is not a
revision to that standing protocol, does not establish "direct to
Antigravity" as an alternate channel going forward, and does not block
or invalidate M30.7A, which remains authorized and in progress
(Antigravity → Codex → evidence → Claude audit).

---

## 7. Governance & Maintenance Rules

### Update Rule
Antigravity must update this file whenever:
- A milestone is approved.
- A milestone enters `IMPLEMENTING`.
- A milestone becomes `VERIFICATION_READY`.
- Claude returns `ACCEPT` / `ACCEPT WITH FOLLOW-UP` / `REPAIR REQUIRED` / `HOLD`.
- The User marks a milestone `LIVE_VERIFIED`.
- The User authorizes the next milestone.

The file must always reflect the latest accepted project state.

### Do Not Self-Authorize
Antigravity must **NOT** change `NEXT MILESTONE STATUS: NOT AUTHORIZED` to an authorized state unless there is explicit User approval or an already-approved governing instruction that clearly authorizes that exact transition. The file records authorization; it never creates it.

### Milestone Handoff Rule
When one milestone completes and another is approved:
1. Archive the completed state in existing milestone/state/report files.
2. Update `URI_ACTIVE_MILESTONE.md`.
3. Change `CURRENT MILESTONE`.
4. Change `CURRENT STATE`.
5. Update authoritative files.
6. Update current write scope.
7. Update stop conditions.
8. Update `NEXT MILESTONE`.
9. Preserve the User as final approval authority.

### Shared Active-Milestone Invariant
`docs/governance/URI_ACTIVE_MILESTONE.md` is the **SINGLE** canonical current-state file for URI development coordination.
Claude, Codex, and Antigravity must all read this exact file before starting milestone work.
There must NOT be:
- Separate Claude milestone files.
- Separate Codex active-state files.
- Duplicated copies of `URI_ACTIVE_MILESTONE.md`.
- Agent-local milestone state treated as authoritative.

**Write Ownership:**
- **Antigravity** is the coordinator and primary writer of `URI_ACTIVE_MILESTONE.md`.
- **Claude** reads the file, audits/plans, returns verdict/evidence, and does not independently advance milestone state.
- **Codex** reads the file, implements/verifies, returns status/reports, and does not independently authorize or advance the next milestone.
- **User** remains the non-delegable final authority for next-milestone authorization.

### Autonomous Loop Execution Invariant
For the CURRENT milestone, Antigravity executes the loop automatically:
`Codex completion → Antigravity collects evidence → Claude audits → [if repair required: route to Codex → collect evidence → Claude re-audits] → update URI_ACTIVE_MILESTONE.md after each transition`

Continue until the current milestone reaches:
`LIVE_VERIFIED + CLAUDE ACCEPT`

**HARD STOP:** Do NOT start the NEXT milestone unless `docs/governance/URI_ACTIVE_MILESTONE.md` explicitly records that the User has authorized it.

### User Approval Channel Protocol (Claude Relay)
The User remains the non-delegable final authority for milestone advancement. During this development period, the User communicates approvals **ONLY through Claude**.

- **No Direct Wait in Antigravity:** Antigravity must NOT pause or wait for a direct User message inside the Antigravity chat session.
- **Claude is the Authorized Approval Relay:** Claude receives the User's explicit decision and records or relays it for Antigravity to record in `URI_ACTIVE_MILESTONE.md`.
- **Relay, Not Authority:** Claude may NOT approve a milestone on the User's behalf, infer approval from silence, or convert its own audit recommendation into User approval. It records User approval *only* when the User has explicitly granted it to Claude.
- **Canonical Approval Record Format:**
  ```markdown
  USER APPROVAL: APPROVED
  APPROVAL RELAY: CLAUDE
  APPROVED MILESTONE: <exact milestone>
  APPROVAL BASIS: Explicit User approval communicated through Claude
  APPROVAL TIMESTAMP: <timestamp>
  ```
  When this record appears in `URI_ACTIVE_MILESTONE.md`, Antigravity treats the named milestone as User-authorized and advances `CURRENT MILESTONE` automatically.

### Automatic Milestone Loop Resumption Rule
When a new milestone has been explicitly approved by the User through Claude and that approval is recorded in `docs/governance/URI_ACTIVE_MILESTONE.md`:
- **CONTINUE WITH THE LOOP AUTOMATICALLY.** Do not stop merely because the approval was relayed through Claude rather than given directly in Antigravity.
- Resume execution immediately from the newly authorized milestone:
  `Claude-approved plan → Antigravity coordination → Codex implementation → Antigravity evidence collection → Claude audit → [bounded repair if required] → Claude re-audit → live verification → update URI_ACTIVE_MILESTONE.md`
- Continue autonomously until that newly authorized milestone reaches its own hard stop or requires another NEW milestone approval.

### Routine Execution Authorization & Permission Prompt Rule
Once a milestone is explicitly authorized in `docs/governance/URI_ACTIVE_MILESTONE.md`, Antigravity is authorized to perform all routine coordination actions required to complete that **SAME** milestone without requesting additional User permission.

**Authorized Routine Actions:**
- Preparing the Codex implementation prompt.
- Handing the prompt to Codex.
- Allowing Codex to inspect authorized files.
- Allowing Codex to edit files within the milestone's approved write scope.
- Running approved tests and test suites.
- Collecting logs, results, and completion reports.
- Sending implementation evidence to Claude.
- Routing bounded repairs back to Codex after Claude audit.
- Repeating test/audit/repair cycles within the SAME milestone.
- Updating `URI_ACTIVE_MILESTONE.md` after valid state transitions.

**Permission Prompt Rule:**
If Antigravity's own execution environment presents an approval dialog for an action already covered by `URI_ACTIVE_MILESTONE.md`: use the existing approved authorization automatically where the platform permits. Do not convert routine internal milestone work into a new User-approval gate.

**Strict Boundaries — Request User Approval ONLY when:**
1. Starting a NEW milestone not yet approved.
2. Expanding beyond the current authorized write scope.
3. Performing commit/push when not already authorized.
4. Performing destructive or high-risk actions requiring explicit approval.
5. Changing security or authentication policy.
6. Encountering an architectural conflict requiring scope expansion.

### Direct Codex Execution & Permission Reduction Rule
Antigravity acts as a coordinator, not an execution proxy. The objective is to eliminate repeated host permission prompts while strictly preserving milestone governance and safety boundaries.

**Codex Direct Execution Authority:**
Within the currently approved milestone and write scope, Codex executes routine implementation directly inside `C:\Users\cheta\Development\uri-agent`:
- Reading repository files.
- Editing approved source files.
- Creating approved milestone files.
- Running the project Python interpreter and test suites (`pytest`, etc.).
- Running approved verification scripts.
- Inspecting test output and generating milestone completion reports.
- Collecting implementation evidence.

**Antigravity Non-Proxy Invariant:**
Antigravity must NOT repeatedly launch shell/Python commands (`python -c ...`, `pytest ...`, helper scripts, etc.) merely to duplicate or proxy work that Codex performs directly. Antigravity's role is:
- Milestone coordination and handoff.
- Scope enforcement.
- Repository evidence collection (via native file read tools).
- Milestone state updates.
- Relay between Codex and Claude via repository files.

**No Claude Session Scraping:**
Do NOT inspect `C:\Users\cheta\.claude\**`, Claude JSONL session logs, or private conversation histories. All Claude ↔ Antigravity ↔ Codex communication flows through repository artifacts (`URI_ACTIVE_MILESTONE.md`, `URI_AGENT_RELAY.md`, audit reports).

**Repository Trust Boundary:**
Routine Codex work remains strictly inside `C:\Users\cheta\Development\uri-agent`. Unrelated external directories are never accessed.

**Continuous Loop Invariant:**
Antigravity does not pause after generating a prompt, receiving an intermediate report, or seeing an internal state transition. The loop proceeds automatically:
`Claude plan → Antigravity coordination → Codex direct execution & evidence → Claude audit → [bounded Codex repair if needed] → Claude re-audit → live verification → update URI_ACTIVE_MILESTONE.md`

### Scheduled Monitoring Invariant
Automated scheduled monitoring is a mandatory, continuous component of this loop:
- Whenever an asynchronous background runner is active (`run_codex_current_milestone.py` or `run_claude_current_handoff.py`), Antigravity must maintain an active, periodic monitoring schedule (e.g. 180-second check-in intervals) conditioned on the task ID.
- At each monitoring interval:
  1. Inspect process health and output logs.
  2. Check repository mailbox (`URI_AGENT_RELAY.md`) and milestone state for updates.
  3. Report concise progress to the user.
  4. Automatically renew the monitoring schedule until the active runner completes.
- Upon task completion, the schedule early-terminates and the loop immediately advances to the next stage without delay.

### Handoff Monitoring Rule (No Idle Gap Invariant)
After EVERY agent handoff, Antigravity must automatically monitor the handoff to completion:
`HANDOFF → DELIVERY → MONITORING → COMPLETION DETECTION → EVIDENCE COLLECTION → NEXT LOOP ACTION`

- Applies to all agent transfers: Antigravity ↔ Claude, Antigravity ↔ Codex, Codex ↔ Claude.
- Applies to all phases: PLAN, PLAN_REVISION, IMPLEMENTATION, AUDIT, REPAIR, VERIFICATION, RE-AUDIT.
- Antigravity must never treat "handoff created" as task completion.
- Antigravity must not sit idle, wait for manual prompts, or create duplicate runner processes while a bridge is active.
- Default loop behavior is always:
  `handoff sent → monitor → collect → continue`


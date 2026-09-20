# M33.2 Batch B.4 — State

**Status:** CLOSED / ACCEPT (Claude independent audit, 2026-09-20)
**Plan:** `docs/plans/M33_2_BATCH_B4_REAL_MODEL_QUALIFICATION_PLAN.md`
**Depends on:** Batch B `906c527`, Batch B.1 `a792a8c`, Batch B.2 `b98620a`,
Batch B.3 `d395c1c` (all CLOSED/ACCEPTED).

## History log

- **2026-09-20 — VERIFICATION_READY → CLOSED/ACCEPT (Claude independent
  audit):** Performed the Verification-First independent final audit
  against primary evidence, not the completion report alone. Independently
  verified, by direct inspection/reproduction rather than trusting Codex's
  report:
  - `git diff HEAD` for every changed file (`ensemble.py`, `corpus.json`,
    `manifest.json`, `.gitignore`, `test_m33_2_batch_b1_ensemble_benchmark.py`)
    matches the completion report's described changes exactly; `requirements.txt`,
    `vision.py`, `speech.py`, `edge_lifecycle/`, `uri_core/core/orchestrator.py`,
    `server.py`, and the dispatcher are byte-unchanged (confirmed
    `orchestrator.py` is identical to baseline `737ddcf`, including its
    reported 6,121-newline count).
  - Independently recomputed SHA-256 for all three downloaded assets
    (llama.cpp `b11063` Windows CPU runtime, SmolLM2-135M-Instruct Q3_K_M
    GGUF, Qwen2.5-0.5B-Instruct Q4_K_M GGUF) directly against the files on
    disk in `uri_workspace/edge_models/` — all three match
    `source_assets.json` and the completion report exactly; byte sizes
    match; the directory is correctly gitignored and untracked.
  - Read `scripts/m33_2_needle_bridge.py` and confirmed Needle is
    constructed with `tools=[]`/JSON schemas only (never executable Python
    callables) and `Needle.complete()` is the only method called —
    `Needle.run()` is never invoked, confirming proposal-only behavior;
    `NEEDLE_TELEMETRY=0`, `DO_NOT_TRACK=1`, `HF_HUB_OFFLINE=1` are set
    before import, confirming local-only/zero-egress posture. Grepped the
    full diff and both new scripts for `pull`: zero matches, confirming no
    Ollama pull was ever issued.
  - Read `temp_evidence/m33_2_batch_b4/consolidated_results.json` directly
    and confirmed every headline number in the completion report
    (Needle 8/8 routing, 4/4 structured extraction, 2/4=50% argument
    extraction, ~101.4–101.7 MB provider peak RAM; SmolLM2 0.625 rubric/
    0/4 exact/~203.8–203.9 MB RSS; Qwen2.5-0.5B 2/4=50% bounded reasoning/
    ~493.6–494.1 MB RSS; both Main-Brain controls 1.0/1.0) is the literal
    evidence-file value, not a rounded or invented figure.
  - Traced Configuration D's anomalous 94.64 ms matrix p50 to source: in
    `EnsembleAdapter.__call__` (`ensemble.py`), a missing `language`/
    `reasoner` component causes an immediate zero-cost escalate for those
    tiers; Configuration A only wires `reflex`, so 16/24 items are
    near-zero and the median lands in the fast group. Configuration D wires
    all three roles, so 16/24 items now make real model calls and the
    median lands in the slow group — the same corpus, same methodology,
    a real distributional shift, not a fabricated or inconsistent number.
    This matches the completion report's own disclosed caveat.
  - Read `test_m33_2_batch_b4_real_model_qualification.py` and confirmed
    `_short_answer()` normalization (used identically for the Qwen2.5-0.5B
    reasoner and both Main-Brain Ollama controls) is generic pattern-based
    normalization, not tuned per expected answer — confirming the
    Main-Brain-vs-Edge-reasoner bounded-reasoning comparison is scored
    fairly on both sides.
  - Independently reran the full required regression set (`test_m33_2_batch_a_edge_foundation.py`,
    `test_m33_2_batch_b_benchmark.py`, `test_m33_2_batch_b1_ensemble_benchmark.py`,
    `test_m33_2_batch_b2_perception_benchmark.py`,
    `test_m33_2_batch_b3_model_runtime_lifecycle.py`,
    `test_m33_2_batch_b4_real_model_qualification.py`) and reproduced
    **60/60 passed**, independently, not merely re-reading the report's claim.
  - Independently reran all eleven files containing the report's 16 claimed
    full-suite failures and reproduced **exactly 16 failed, 7 passed**, with
    test names matching the report's classification 1:1 (obsolete
    `DriveService.list_recent_files` calls, M20 fallback/recovery/resilience/
    session/workflow tests expecting older orchestrator behavior, the stale
    newline-count boundary, and `qwen3:14b`-dependent live tests — a tag B.4
    was expressly prohibited from pulling). None of the 16 touch any
    B.4-changed file; zero B.4 regressions confirmed independently.
  - Confirmed governance doc updates (`URI_ACTIVE_MILESTONE.md`,
    `URI_AGENT_RELAY.md`) accurately restate the verified evidence with no
    inflation beyond what the primary evidence supports.

  **Verdict: ACCEPT.** Final resident/on-demand/bypass determination:
  - **Needle 3 → `RESIDENT`**, scope-limited to reflex tool
    routing/competing-tool selection and structured-record extraction only.
    Its measured 50% normalized-argument-extraction rate means URI must
    continue to treat argument values as an untrusted proposal requiring
    validation/confirmation before use — argument extraction is explicitly
    **not** part of the qualified resident scope.
  - **SmolLM2-135M-Instruct → `BYPASS / REDUNDANT`.** 0/4 exact-match
    language answers and missing required refusal/acknowledgement wording
    do not justify ~204 MB resident memory; verdict justified.
  - **Qwen2.5-0.5B-Instruct → `BYPASS / REDUNDANT`.** 50% accuracy with
    substantive reasoning errors (wrong constraint answer, wrong set
    intersection) at ~494 MB, materially worse than both already-installed
    100%-accurate Main-Brain controls at lower or comparable latency and
    without the extra resident memory; verdict justified, and unsuitable as
    the current bounded reasoner.
  - **STT / OCR / VLM → `UNQUALIFIED / UNAVAILABLE`**, confirmed truthful
    (no fake qualification, no architecture workaround, no forced result;
    perception adapter files byte-unchanged).
  - Zero-egress Edge core, local-only Needle bridge, user-space-confined
    model storage, no Ollama pulls, no production/UI wiring, and unchanged
    deterministic URI authority are all independently confirmed, not merely
    asserted.

  **Nothing unverifiable found that affects this verdict.** One immaterial
  disclosure: the two-hop chain from downloaded-file-SHA-256 (independently
  recomputed, matches) to "this is genuinely the intended upstream model" was
  not re-derived from the original HuggingFace/GitHub release pages in this
  audit session (would require live network egress this audit intentionally
  avoided); the completion report's stated source URLs are taken as given.
  This does not affect the verdict — the qualification numbers are measured
  against whatever weights are actually on disk, verified by hash, regardless
  of upstream provenance, and no production authority depends on this chain.

  No bounded defects were found; no fix was required. This batch is
  qualification-only, additive, and reversible — nothing here fails, weakens,
  or executes anything with new authority.

- **2026-09-20 — IMPLEMENTING → VERIFICATION_READY (Codex):** Executed the
  accepted real-model qualification plan without production promotion.
  Needle 3, SmolLM2-135M-Instruct Q3_K_M, Qwen2.5-0.5B-Instruct Q4_K_M,
  configurations A–D, and the existing `qwen3.5:9b` / `gemma4:12b`
  Main-Brain controls were measured. Needle qualified as the sole `RESIDENT`
  recommendation for reflex routing/structured extraction; SmolLM2 and the
  0.5B reasoner are `BYPASS / REDUNDANT`; STT/OCR/VLM remain truthfully
  `UNQUALIFIED / UNAVAILABLE`. Required M33.2 regressions are 60/60 passing;
  the full suite is 2,249 passed / 16 unrelated baseline-environment failures
  / 40 subtests passed. Completion evidence:
  `docs/plans/M33_2_BATCH_B4_COMPLETION_REPORT.md` and
  `temp_evidence/m33_2_batch_b4/`. No commit or push.

- **2026-09-20 — DRAFT → ACCEPTED (Claude, standing auto-approval,
  `ORCHESTRATION.md` §1.5):** Immediately after Claude's independent audit
  closed Batch B.3 (`d395c1c`/`d6b97d7`), the User directly authorized the
  real Edge-model qualification scope: qualify Needle 3 (already installed
  and manually demonstrated by the User), a lightweight language worker, a
  bounded local reasoner, speech/STT, OCR, and a small VLM if practical,
  compare practical combinations (A-D per B.1's ensemble definitions, plus
  Edge+speech, Edge+vision, and a Main-Brain-bypass control), and determine
  which specialists materially improve URI, which are redundant, which
  should stay resident vs. `ON_DEMAND`, and when to bypass Edge for the
  Main Brain. Explicitly qualification-only: no new architecture layer, no
  Batch C, no M31 UI.

  Before drafting, Claude directly inspected the relevant source
  (`uri_core/core/edge/adapters/ensemble.py`, `vision.py`, `speech.py`,
  `uri_core/core/edge_lifecycle/`) and confirmed the four ensemble
  configurations (A-D) and the VLM/STT/OCR gating already exist as real,
  tested extension points — every real candidate has simply never had a
  real callable injected. Also directly inspected the environment:
  `cactus-needle==3.0.2` is installed and importable as `needle` in a
  dedicated `.venv-needle` (not the main `.venv`), explaining why prior
  batches' own test runs saw Needle as `PACKAGE_NOT_INSTALLED` without
  contradicting the User's real manual test; `pytesseract`/`Pillow` are
  installed but no `tesseract` binary is on PATH; `faster-whisper`,
  `torch`, `transformers`, and any GGUF runtime are installed nowhere.

  **Self-review correction before acceptance (Verification-First
  standard):** the first draft suggested sourcing the tiny language/reasoner
  models by instructing the already-adopted Ollama runtime to pull new
  model tags. On review this was found to exceed B.3's own frozen scope,
  which explicitly limited Ollama interaction to detecting/adopting
  runtimes and discovering *already-downloaded* models "without downloading
  anything" — an active new pull would write outside URI-controlled storage
  via a third-party executable, neither authorized by B.3 nor by this plan.
  Repaired before acceptance: language/reasoner weights must be sourced only
  through B.3's own checksum-verified `edge_lifecycle` download/import path;
  an already-present, already-adopted Ollama model may be used as-is
  (genuine adoption), but a new pull may not be requested. A local GGUF
  inference runtime dependency (e.g. `llama-cpp-python`) was added to the
  plan and explicitly flagged, since downloaded weights need something to
  execute them.

  Full plan in
  `docs/plans/M33_2_BATCH_B4_REAL_MODEL_QUALIFICATION_PLAN.md`. No
  implementation performed by Claude; Antigravity routes implementation to
  Codex per standing AO-4 routing (real-model-integration work fits
  "complex/precision-critical," same rationale as B.1/B.2/B.3). No Batch C
  work is authorized. No M31 UI work is authorized.

## Routing

Antigravity: pick up this ACCEPTED plan, route implementation to Codex, and
persist milestone state through the usual `STATE.md`/completion-report
handoff artifacts this repository already uses for M33.1/M33.2 batches.

**Binding constraint for the implementation task package:** the
implementation task Antigravity writes for Codex must explicitly quote this
plan's boundary on Ollama sourcing (item 2/3: adoption of an
already-present model is fine, a new `ollama pull`-equivalent request is
not) and its "no forced result" rule (item 6/Non-goals: VLM, and possibly
OCR, may truthfully end `UNAVAILABLE` rather than be forced). It must also
require every new Python dependency to be flagged explicitly in the
completion report, never added silently.

## Next action

CLOSED. M33.2 Batch B.4 is ACCEPTED and released. Claude will prepare the
final M33.2 closure handoff next (no Batch C, no M31 UI, no ARN
implementation, per the User's explicit scope boundary for this session).

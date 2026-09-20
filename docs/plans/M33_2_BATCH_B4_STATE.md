# M33.2 Batch B.4 — State

**Status:** ACCEPTED — awaiting Antigravity-routed implementation
**Plan:** `docs/plans/M33_2_BATCH_B4_REAL_MODEL_QUALIFICATION_PLAN.md`
**Depends on:** Batch B `906c527`, Batch B.1 `a792a8c`, Batch B.2 `b98620a`,
Batch B.3 `d395c1c` (all CLOSED/ACCEPTED).

## History log

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

Antigravity packages the completion report, source diff, generated
evidence, and test results for Claude's independent audit once
implementation reports `VERIFICATION_READY`, as one consolidated run
covering every item in the plan — not a model-by-model series of separate
handoffs. Claude determines ACCEPT or REPAIR REQUIRED. Codex does not
self-verify, commit, or push.

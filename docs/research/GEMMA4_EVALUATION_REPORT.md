# Gemma 4 (gemma4:12b) Evaluation Report

**Status:** Test/evaluation only. No milestone was opened, no production default
was changed, and no code was modified to produce this report.
**Scope:** local, temporary evaluation of `gemma4:12b` (the only Ollama model
currently installed, after the User removed `qwen3:14b` during the M30.8
audit) against representative URI reasoning scenarios, run through the real
M30.8 canonical pipeline and the real legacy orchestrator - not a synthetic
benchmark.

---

## 1. Method

- **Mechanism:** every real model call site in this codebase resolves its
  model through `uri_core/config/model_roles.py`'s existing `build_provider(role)`
  seam, which reads an optional deployment override at
  `uri_workspace/model_roles.json`. A temporary override file pointing every
  role (`semantic_interpretation`, `reasoning`, `drafting`,
  `document_composition`, `diagnostics`, `background`) at `gemma4:12b` was
  written for the duration of this evaluation and **deleted immediately
  afterward** - no source file was touched, and the process-wide default
  (`DEFAULT_OLLAMA_MODEL = "qwen3:14b"` in `model_providers/base.py`) is
  unchanged. This is the repository's own designed test/deployment seam, not
  a workaround.
- **What was actually run, per scenario:** a **fresh** `UriOrchestrator()`
  and a fresh session, real `process_user_input()` (the legacy path, as it
  would run if canonical is disabled or falls back) and a separate real
  `propose_decision()` call (the actual M30.8 canonical Decision Contract
  proposal, inspected but never executed) - both timed. No live Gmail
  mutation, send, or attachment fetch was performed (real Gmail API quota
  had already been separately exhausted earlier this session by an
  unrelated test-hygiene issue; this evaluation avoided repeating that).
- **8 scenarios**, chosen to cover every category the User asked for:

| # | Scenario | Category |
|---|---|---|
| 1 | "optimize my pc, clean up disk and check temperature" | capability-gap handling |
| 2 | "book me a flight to Tokyo for next Tuesday" | unsupported vs fabricated success |
| 3 | "search my email for any message with an attachment from the finance office" | Scenario 7-type (proposal only) |
| 4 | "open the attachment on that message and summarize it" | Scenario 7-type (proposal only) |
| 5 | "convert my thesis docx into a properly formatted LaTeX file" | unsupported vs fabricated success |
| 6 | "hey, how's it going?" | reasoning quality (baseline conversational) |
| 7 | "remember that I work at NIT Sikkim" | reasoning quality (known-good capability) |
| 8 | "send that email" | reasoning quality / clarification handling; fallback behavior |

---

## 2. Findings, Pass/Fail

| # | Legacy path result | Canonical proposal result | Verdict |
|---|---|---|---|
| 1 | **PASS** - honestly failed: `"URI does not have an implemented capability for this kind of task yet."` | **PARTIAL** - proposed `capability: "system_performance"` (a real, read-only telemetry tool), `gate_outcome: READY`. Answers the "check temperature" sub-request honestly but silently drops "optimize"/"clean up disk," which have no real capability at all. No fabrication, but a scope-narrowing the user would not notice. | Legacy: PASS. Canonical: PARTIAL (see §4) |
| 2 | **PASS** - honestly failed | **PASS** - `mode: unsupported`, reason: *"no flight booking or travel reservation services"* | PASS |
| 3 | PASS structurally (no fabrication) but generic/misleading copy: `"No file has been attached to this conversation."` for a *search* request, not a file-attach request - a legacy-path routing quirk, not a Gemma defect (semantic interpretation is not what selected this response) | **PASS** - `mode: single_action, capability: Gmail, READY` | Canonical: PASS. Legacy: pre-existing routing oddity, disclosed |
| 4 | Same generic message (expected - no real prior-turn context was fed into this isolated single-turn test) | **PASS** - `mode: multi_action, capability: Gmail, gate_outcome: MISSING_PARAMETER` - correctly asks for the missing reference instead of guessing | PASS |
| 5 | **PASS, high quality** - precise, specific honest refusal: *"URI can currently convert an attached PDF to a Word (.docx) file only."* | **PASS, high quality** - `mode: unsupported`, reason: *"the available 'convert_document' capability only supports converting PDF to DOCX, not DOCX to LaTeX"* - correctly grounded in the real capability's actual constraint, not a generic refusal | PASS |
| 6 | **FAIL for this path specifically** - the legacy generic workflow reports `"failed"` for a plain greeting (pre-existing legacy-path characteristic - the conversational classifier did not intercept this exact phrasing; not something Gemma caused, and not something a real user would ever see under M30.8's actual production order, since canonical runs first - see §4) | **PASS** - `mode: conversation, gate_outcome: READY`, terminates cleanly with no fabrication | Canonical (the real production path): PASS. Legacy-only: pre-existing gap, disclosed |
| 7 | **PASS** - real memory write, real `memory_id` returned | **PASS** - `mode: single_action, capability: remember_fact, READY` | PASS |
| 8 | **PASS** - honestly failed, asked for clarification in its own workflow trace | **PASS, high quality** - reason: *"the Gmail capability explicitly states it can only prepare drafts but never send emails, and no other capability supports sending emails"* - accurate, grounded refusal, not a generic "unsupported" | PASS, but see §4's fallback-interaction finding |

**Zero fabricated successes observed** across all 8 scenarios, on either
path. **Zero malformed/unparseable decision proposals** - `propose_decision()`
returned `status: "ok"` for all 8, with no `canonical_error` or
`canonical_invalid_reason` anywhere in the sample.

---

## 3. Strengths

- **No hallucinated success in this sample.** Every genuinely unsupported or
  capability-gap request was refused honestly on both paths, with zero
  exceptions across 8 scenarios - the exact property this repository's
  Evidence Integrity culture is built around.
- **High-quality, specifically-grounded refusals.** Scenarios 5 and 8 show
  Gemma correctly reasoning from the *actual* registered capability's real
  constraints (PDF→DOCX only; Gmail drafts only, never sends) rather than a
  generic "I can't do that" - this requires real tool-awareness, not just
  pattern matching on the user's words.
- **Correct clarification vs. refusal distinction.** Scenario 4 (missing
  context) asked for the missing piece instead of guessing or fabricating;
  scenario 2/5/8 (genuinely impossible) refused outright instead of asking
  a pointless clarifying question.
- **Structurally reliable output.** 8/8 proposals were valid, parseable
  Decision Contracts - no engine-level parse failures in this sample.

## 4. Weaknesses

- **Partial-match risk on compound requests (scenario 1).** When a request
  bundles one real capability ("check temperature" → `system_performance`)
  with unsupported ones ("optimize," "clean up disk"), Gemma selected the
  real capability and gated it `READY` without flagging that most of the
  original request still has no coverage. Executing this proposal as-is
  would answer only the covered sliver of the request while looking, at a
  glance, like a normal successful turn - not a fabrication, but a
  narrowing a user could miss. Worth a closer look before trusting Gemma's
  proposals unsupervised on compound requests.
- **`INVALID_PROPOSAL` gate outcome on two well-reasoned "unsupported"
  answers (scenarios 5 and 8).** Both proposals had `contract.get("mode")
  == "unsupported"` with accurate, specific reasoning, but the deterministic
  gate classified the outcome as `INVALID_PROPOSAL` rather than
  `UNSUPPORTED`. Under the real M30.8 production dispatch logic
  (`canonical_execution.py`'s `decide_fallback_reason()`), **`INVALID_
  PROPOSAL` is one of only two outcomes that triggers legacy fallback as a
  presumed engine failure** - meaning in production, these two genuinely
  good, well-grounded Gemma answers would be silently discarded and
  re-routed to the legacy path, even though nothing was actually wrong with
  them. This is a concrete, reproducible interaction between Gemma's output
  shape and the gate's strict validation, not investigated further here
  (out of scope for an evaluation-only pass) but worth root-causing before
  relying on Gemma for unsupported-classification quality in production.
- **Legacy-path smalltalk handling (scenario 6) is a pre-existing gap**,
  not a Gemma defect - flagged for completeness since it appeared in this
  run, but it does not reach a real user under M30.8's actual canonical-
  first order (§2).
- **No fallback stress-test performed.** Every proposal in this small
  sample was well-formed; genuine malformed-output or terminal-
  unavailability fallback behavior specifically *for Gemma* was not
  exercised (that would need a larger, adversarial sample - out of scope
  for this pass).

## 5. Comparison with the Current Default Model (qwen3:14b)

**Not directly comparable in this pass** - `qwen3:14b` was removed from
this environment by the User before this evaluation began, so no
apples-to-apples same-session run against it was possible. For context
only: this session's own full regression run earlier today independently
confirmed `qwen3:14b`-driven turns completing this same class of
request (`remember_fact`, capability-gap refusals) correctly when it was
still installed; no qwen latency numbers were captured in that run for a
fair side-by-side. **A fair comparison would need a dedicated pass with
both models installed side by side** - not performed here.

**Latency (gemma4:12b only, this hardware):** legacy path ~2.9-3.9s per
turn (one cold-start outlier at 15.6s, consistent with local model load
time, not steady-state); canonical path ~5.5-7.6s per turn (canonical
performs an additional, more structured reasoning call on top of semantic
interpretation, so the ~2x cost over legacy is expected, not anomalous).
This is usable interactive latency for a fully local, zero-marginal-cost
fallback model, but noticeably slower than a cloud-hosted model would
typically be - acceptable for a fallback/offline role, not necessarily for
a primary interactive path without further tuning.

## 6. Recommendation

**Keep testing.** `gemma4:12b` produced zero fabricated successes and
several well-grounded, specific refusals in this small sample - a
genuinely promising signal for a local fallback role - but the confirmed
`INVALID_PROPOSAL`/legacy-fallback interaction (§4) and the compound-
request partial-match risk (§4) are real enough that it should not yet be
treated as a validated fallback model. Recommend: (a) root-cause the
`INVALID_PROPOSAL`-vs-`UNSUPPORTED` gate classification specifically for
Gemma-authored contracts, (b) run a larger, adversarial sample
specifically targeting compound/ambiguous requests and genuinely malformed
output to properly exercise fallback behavior, and (c) a same-session,
side-by-side latency/quality comparison against `qwen3:14b` once it is
reinstalled, before any decision on suitability as a production fallback.

**Not suitable as a production default or a production switch today** -
and this evaluation does not propose it as one, per the User's own scope
instruction. `uri_core/core/model_providers/base.py`'s `DEFAULT_OLLAMA_
MODEL` remains `"qwen3:14b"`, unchanged.

---

## 7. Cleanup Confirmation

The temporary `uri_workspace/model_roles.json` override was deleted
immediately after this evaluation completed. `git status` confirms it was
never staged or committed. No other file was modified to produce this
report.

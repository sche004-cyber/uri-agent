# M33.2 Batch B.2 — Edge Perception Qualification Completion Report

**Implementation status:** VERIFIED — ACCEPT (Claude independent audit,
2026-09-20)  
**Designation:** `HARNESS_COMPLETE` / `REAL_PERCEPTION_CANDIDATE_QUALIFICATION_PENDING`
(same convention as Batch B.1's closure)  
**Date:** 2026-09-20  
**Authority:** `docs/plans/M33_2_BATCH_B2_EDGE_PERCEPTION_PLAN.md`

## Outcome

Batch B.2 is implemented as an additive, benchmark-only perception extension.
It does not promote a vision or speech candidate, implement the production
`EdgeVisionProvider`/`EdgeSpeechProvider` Protocols, or alter routing,
authority, approval, credentials, dispatcher, orchestrator, server, or UI
code. Perception outputs remain proposal/observation evidence only.

The runner wrote nine evidence bundles under
`temp_evidence/m33_2_batch_b2/`: three fixture vision pathways, three actual
vision pathways, the Needle audio probe, one fixture STT pathway, and the
actual faster-whisper fallback. Every candidate directory contains
`manifest.json` and `result.json`; every materialized manifest recomputes the
frozen corpus SHA-256.

## Frozen corpora

- Vision: 12 synthetic URI-owned items covering screenshot errors, structured
  field extraction, UI state, VQA, low-quality ambiguity, and explicit Main
  Brain escalation. SHA-256:
  `0e8143395bab304249cf77ecbaa508bab8eb4bd69b16eab7b6a5e33d2a6aa452`.
- Audio: 8 synthetic URI-owned items covering short commands, dictation,
  noisy/ambiguous speech, and sensitive-command confirmation. SHA-256:
  `e457ab641d0fb58c6eee2c5712893fc5d71fd263570ac12a5ab7a736437f1087`.

## HARNESS VALIDATION — deterministic fixtures

These results validate scoring, control flow, resource instrumentation,
confidence behavior, and fallback handling. They do **not** qualify the named
real OCR, VLM, Needle, or faster-whisper runtimes.

| Candidate | Runtime | Qualification | Correctness | Field F1 | VQA score | p50 / p95 ms | Fixture TTFT ms |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| V1 `fixture-v1-ocr` | available | QUALIFIED_FOR_COMPARISON | 0.667 | 1.000 | 0.600 | 0.0015 / 0.0065 | 2.0 |
| V2 `fixture-v2-vlm` | available | QUALIFIED_FOR_COMPARISON | 0.667 | 0.000 | 0.800 | 0.0016 / 0.0051 | 14.0 |
| V3 `fixture-v3-hybrid` | available | QUALIFIED_FOR_COMPARISON | 1.000 | 1.000 | 1.000 | 0.0021 / 0.0076 | 18.0 |

V1 was deliberately perfect on the four common structured/text-heavy items
(two field extractions and two application-error screens) and weaker on open
visual/UI questions. V2 showed the complementary simulated behavior. V3
combined both. This directly exercises the research question: the harness
supports keeping a VLM optional/on-demand when OCR confidence is high on
structured text, but real OCR accuracy and resource evidence are still
required before making that production recommendation.

The fixture STT candidate produced correctness `0.875`, WER
`0.017857142857142856`, CER `0.01293103448275862`, mean transcript confidence
`0.8875`, p50/p95 `0.0010/0.0043 ms`, and fixture TTFT `6.0 ms`. Its one
deliberate noisy-speech deletion makes the WER/CER paths non-trivial.

Fixture process measurements reflect deterministic Python only. RSS load
deltas were `0.0 MiB`; benchmark RSS deltas were `3.5117 MiB` for the first
vision run and `0.0–0.0039 MiB` for subsequent fixture runs. They are not
model footprint or inference-performance claims.

## REAL CANDIDATE QUALIFICATION — pending/unavailable

| Candidate | Result | Truthful reason |
| --- | --- | --- |
| V1 `actual-v1-ocr` | UNAVAILABLE | `tesseract` binary absent from PATH and `URI_EDGE_TESSERACT_PATH` unset |
| V2 `actual-v2-vlm` | UNAVAILABLE | `URI_EDGE_VLM_MODEL_PATH` unset |
| V3 `actual-v3-hybrid` | UNAVAILABLE | both required sub-runtimes above unavailable |
| Needle audio | `PACKAGE_NOT_INSTALLED` | neither `needle` nor `cactus_needle` importable in the installed environment |
| Alternative `actual-stt-faster-whisper` | UNAVAILABLE | `URI_EDGE_STT_MODEL_PATH` unset and `faster-whisper` library unavailable |

Actual candidates report p50, p95, TTFT, GPU, and VRAM as `unavailable`; no
values were fabricated. No new dependency was installed or added to
`requirements.txt`. The adapters statically probe optional local runtimes and
accept injected/local callables without network access.

## Needle empirical probe

**Audit correction (2026-09-20):** the implementation's original probe logic
defaulted an un-importable module straight to `NOT_SUPPORTED`, which
conflates "package not installed" with the frozen plan's actual definition
of `NOT_SUPPORTED` ("the installed/current Needle API genuinely exposes no
speech/audio capability, introspectable at the Python object/signature
level"). Nothing is introspectable when no module imports at all, so that
case can never satisfy `NOT_SUPPORTED`'s own definition. Claude's
independent audit applied the smallest bounded fix consistent with the
frozen plan: `uri_core/core/edge/adapters/speech.py`'s
`NeedleAudioClassification` gained one additive sub-state,
`PACKAGE_NOT_INSTALLED`, used only when no needle/cactus_needle module can be
imported; the original `NOT_SUPPORTED` semantics (an installed, introspected
API with confirmed no audio parameters) are unchanged and remain covered by
existing tests. A new focused test
(`test_needle_probe_distinguishes_package_not_installed_from_not_supported`)
locks this distinction in, and the live runner was re-executed to
regenerate `temp_evidence/m33_2_batch_b2/needle-audio-probe/result.json`
under the corrected logic.

The documentation-conflict state was resolved for this installed environment
as exactly **`PACKAGE_NOT_INSTALLED`** (not `NOT_SUPPORTED`):

- package version: unavailable (`null`), because neither supported package
  import nor matching installed distribution metadata was found;
- git commit/tag: unavailable (`null`);
- inspected `complete`/`run`/`embed` signatures: none, because no module was
  importable;
- audio input capability: false;
- transcription output capability: false;
- transcript-confidence capability: false;
- runtime/load status: `unavailable` / `not_loaded`;
- local/offline behavior: not verifiable without an installed runtime.

This remains the neutral tie-breaker outcome the plan called for: it says
nothing about whether an installed Needle build would support audio, only
that no Needle build is installed in this environment to introspect.

The complete reproducibility dictionary is stored in
`temp_evidence/m33_2_batch_b2/needle-audio-probe/result.json`. Because the
classification was not `AVAILABLE_SUPPORTED`, the runner automatically
continued to both the deterministic fixture STT and the provider-agnostic
faster-whisper fallback. The fallback also remained truthfully unavailable.

## Resource and safety evidence

- `psutil` RSS before/after load, load time, benchmark delta, and latency
  p50/p95 are present for every benchmark result.
- GPU/VRAM and TTFT remain the literal string `unavailable` when they cannot
  be measured.
- `outbound_deny=True` and `candidate.local_only=True` remain mandatory.
- Recursive AST tests confirm the entire `uri_core/core/edge/` tree imports no
  authority/execution modules and no network/egress libraries.
- Batch A's no-dynamic-import-residue guard remains passing; the Needle probe
  uses static optional imports and signature inspection.

## Verification

Codex's original figures (pre-audit-fix):

- `pytest test_m33_2_batch_b2_perception_benchmark.py -v` — **15 passed**.
- `pytest test_m33_2_batch_b1_ensemble_benchmark.py -v` — **15 passed**.
- `pytest test_m33_2_batch_b_benchmark.py -v` — **2 passed**.
- `pytest test_m33_2_batch_a_edge_foundation.py -v` — **12 passed**.
- Requested focused total: **44 passed**.
- Live runner: **9/9 evidence directories written** with matching corpus
  hashes and truthful runtime states.
- Full `pytest -q`: **2,232 passed, 10 failed, 7 skipped, 40 subtests passed**
  in 1,175.06 seconds.

Claude's independent audit re-ran the focused suite and, after the
`PACKAGE_NOT_INSTALLED` bounded fix above (which added one locking test),
reproduced:

- `pytest test_m33_2_batch_b2_perception_benchmark.py -v` — **16 passed**
  (15 original + 1 new: `test_needle_probe_distinguishes_package_not_installed_from_not_supported`).
- `pytest test_m33_2_batch_b1_ensemble_benchmark.py test_m33_2_batch_b_benchmark.py test_m33_2_batch_a_edge_foundation.py -q` together with the file above — **45 passed** focused total (44 original + 1 new).
- Live runner re-executed independently: **9/9 evidence directories
  regenerated**, reproducing every fixture correctness/WER/CER value in this
  report bit-for-bit, with the Needle probe now correctly reporting
  `PACKAGE_NOT_INSTALLED`.
- `python -m compileall -q ...` — passed.
- `git diff --check` — clean (line-ending notices only).

**Auditable correction — full-suite reproduction, disclosed 2026-09-20
(out of B.2's scope, does not block ACCEPT):** Claude ran the full suite
twice independently. First run (pre-fix B.2 test count, 15 in that file):
**12 failed, 2230 passed, 7 skipped, 40 subtests passed** (2,249-item
total). Second run, after the `PACKAGE_NOT_INSTALLED` fix and its added
test (16 in that file): **12 failed, 2231 passed, 7 skipped, 40 subtests
passed** in 1,232.21s (2,250-item total) — identical failure names both
times, and the pass count increased by exactly the 1 new test, confirming
no other change. Neither run reproduced the claimed 10-failure shape. The
10 originally-claimed failures reproduced exactly as named both times. Two
additional failures appeared that are **not** in the accepted B.1/B.2
baseline set:
`test_m19_office_readiness.py::GmailDraftAndDriveUploadSafetyTests::test_drive_upload_resolves_most_recent_session_file`
and
`test_m19_office_readiness.py::GmailDraftAndDriveUploadSafetyTests::test_no_credentials_reports_unavailable_honestly`.
Root cause, confirmed directly: both tests assert `result["status"] ==
"unavailable"` under a "no credentials" assumption, but this machine's
working tree currently has real, gitignored `token.json` (modified during
this very audit session) and `credentials.json` files, so the Gmail/Drive
tools genuinely succeed instead. This is a **local, real-credential
environment state**, not a code regression: `test_m19_office_readiness.py`
and every Gmail/Drive source file are untouched by B.2 (confirmed via `git
status`/`git diff`, and `test_m19_office_readiness.py` shows no pending
changes at all), and B.1's own completion report independently reproduced
the clean 10-failure shape on 2026-09-20 before these credential files were
present in this state. This is disclosed rather than silently corrected or
hidden, per this repository's evidence-integrity standard, and is recorded
as a separate, out-of-scope environment-hygiene issue (these two tests
should probably skip or mock credential discovery rather than depend on
the ambient absence of real OAuth files) — not a defect in B.2's vision/
speech scope, and not remediated under B.2's bounded-fix authority.
Claude's independently re-executed focused B.2 suite (45/45) and B.2's own
zero-egress/authority-boundary AST test remain the operative regression
check for this milestone's actual scope.

## Changed files

- `fixtures/m33_2_edge_perception/{vision,audio}_corpus.json` and manifests.
- `uri_core/core/edge/adapters/vision.py` and `speech.py`.
- `uri_core/core/edge/adapters/benchmark.py` and `__init__.py`.
- `scripts/m33_2_edge_perception_benchmark.py`.
- `test_m33_2_batch_b2_perception_benchmark.py`.
- This completion report and the B.2 state/governance handoff records.

## Architectural conclusions and limitations

1. The deterministic comparison validates the intended tiering: OCR can
   cover common structured text/error-dialog cases while a VLM remains lazy
   and optional; hybrid fusion can cover both classes. This is a harness
   conclusion only, not a real-model qualification.
2. Needle's suitability for URI STT needs remains unqualified in this
   environment, not disproven: no needle/cactus_needle build is installed
   to introspect, so the probe correctly reports `PACKAGE_NOT_INSTALLED`
   rather than a capability verdict. This says nothing about whether an
   installed Needle build would or would not support audio, and is not a
   universal claim about all Needle builds.
3. The benchmark harness itself is lightweight and zero-egress. Whether real
   perception is lightweight enough for Edge Brain remains unqualified until
   local binaries/weights are supplied and produce measured accuracy,
   latency, RSS/VRAM, and confidence evidence.
4. Synthetic references intentionally do not contain real user media. Actual
   candidates therefore require separately materialized local image/audio
   files and configured runtimes for real qualification.

Production architecture remains unchanged. Claude must independently audit
the implementation and evidence before acceptance or release. Codex stops at
`VERIFICATION_READY`; no commit or push was performed.

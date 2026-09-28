# M36 implementation report

State: `M36_IMPLEMENTED_VERIFICATION_READY_FOR_INDEPENDENT_AUDIT`.
Implemented and self-qualified by Codex on 2026-09-28. Independent closing audit, freeze, release and production adoption remain open. No push.

## Authority and baseline

Starting HEAD: `23f5cd9a5f1ac5d17d431c7a76a15533e5c570a4`, branch `m35-uri-v1-parallel-architecture`; includes accepted plan through A4. Frozen M33.3 comparison baseline: `291c9daa48435200c4b56857d0e3bc630016e82a`.

The direct User implementation package supplies `PG_M1_ACCEPTED` and grants PG_M2. The prior planning header still awaited final A4 acceptance; the direct authorization supersedes that header, with provenance explicitly recorded. No separate final A4 acceptance report was supplied or located. The original and focused independent reports and accepted plan are unchanged. Governing safeguards, model/runtime authority, D4-R1, D-A/OD-2..OD-5/VG-1/LF-1 and harness_run_ref deferral remain intact.

## Scope and nine waves

| Wave | Delivered |
|---|---|
| 1 Contracts | Closed immutable records/enums, canonical serialization, derived authority, bounded payload/trace/path/credential validation, SHAREABLE rejection. |
| 2 Log/index | Per-user monthly append-only JSONL, stable lock, flush/fsync and exact read-back, quarantine original bytes, replay/idempotency, causal heads/conflicts/tombstones; no timestamp winner. |
| 3 Sources | Explicit roots; private-memory exclusion; bounded complete scans; symlink/junction/reparse containment; checked-handle fingerprint; stable root/path identity; 64 MiB/no-hydration degradation. |
| 4 Task/history | Trusted task/open/state evidence, all accepted transitions, expectation heads, user corrections with atomic logical pair/read-back recovery, factual outcomes and derivatives. |
| 5 Verifiers | Immutable process-bootstrap registry; trusted callable invocation and protected exact-digest receipt; typed status; no caller-controlled VERIFIED. Negative verdicts retained. |
| 6 Retrieval | Session first, no durable read when satisfied; task/time/current-reference filters before budgets; current live rediscovery; complete collision union independent of model type hints; deterministic last-use/source-ID ordering. |
| 7 Adapter | Raw URI intake/attachment manifest; A3 initial-expression and A4 FREE_INPUT admission; live scope/hash checks before real frozen S1; S7 event/S11 version links; no frozen edits or core dependency on RAR implementation. |
| 8 Context/telemetry | ≤8 KiB task package with authority/provenance/hash/freshness, historical bindings, checkpoint-linked outcome/next step, protected verdicts and stale lineage; content-free query/write telemetry. |
| 9 Qualification | 91 M36 tests; predeclared valid-file real S1/S7/S11 driver; 45 cases ×2, fault/restart/forced termination, frozen/regression/governance evidence. |

No Brain, agent-loop, S13, legacy Memory, uri_core, UI, Office demonstrator, Edge/Harness, embeddings, model transport, preference learning, S9 or harness_run_ref implementation. This module is not claimed to meet the permanent live Brain/UI acceptance rule; that production integration is explicitly outside M36 authorization.

## Files

New implementation, tests, driver and frozen-before-run threshold/battery inputs:

- `fixtures/m36_memory/battery.json`
- `fixtures/m36_memory/threshold_gate.json`
- `scripts/m36_memory_qualification.py`
- `tests/test_m36_memory_adversarial.py`
- `tests/test_m36_memory_contracts.py`
- `tests/test_m36_memory_grounding.py`
- `tests/test_m36_memory_qualification.py`
- `tests/test_m36_memory_retrieval.py`
- `tests/test_m36_memory_sources.py`
- `tests/test_m36_memory_storage.py`
- `tests/test_m36_memory_support.py`
- `tests/test_m36_memory_verifier.py`
- `uri_v1/memory/__init__.py`
- `uri_v1/memory/context_package.py`
- `uri_v1/memory/contracts.py`
- `uri_v1/memory/index.py`
- `uri_v1/memory/log.py`
- `uri_v1/memory/recorder.py`
- `uri_v1/memory/retrieval.py`
- `uri_v1/memory/sources.py`
- `uri_v1/memory/telemetry.py`
- `uri_v1/memory/uri_adapter/__init__.py`
- `uri_v1/memory/uri_adapter/envelope.py`
- `uri_v1/memory/uri_adapter/links.py`

Modified governance only:

- `PROJECT_MEMORY.md`
- `URI_MILESTONE_TRACKER.md`
- `docs/governance/URI_ACTIVE_MILESTONE.md`
- `docs/governance/URI_STATE.yaml`
- `docs/plans/M36_STATE.md`

Evidence created under docs/plans/: M36_IMPLEMENTATION_REPORT.md, M36_QUALIFICATION_MATRIX.md, M36_INTEGRITY.json, M36_TELEMETRY.json, M36_AGGREGATES.json, M36_TEST_RESULTS.log/.xml, M36_FROZEN_REGRESSION.log/.xml, M36_BROAD_REGRESSION.log/.xml, M36_BASELINE_FAILURE_RECHECK.log/.xml, M36_GOVERNANCE_RESULTS.log/.xml. No supplied independent audit report was edited.

## Qualification and real-flow evidence

[Qualification matrix](M36_QUALIFICATION_MATRIX.md) maps Q-1..Q-12, Q-E2E/Q-DET/Q-LAT, Q-A2-1..11 and A3 A–G/A4 H1–H3 to concrete tests and paths. All implementation self-qualification checks pass; no independent ACCEPT is inferred.

Per full real-flow run: 45 expressions, 0 wrong CONFIRMED, 0 invented IDs, 0 TENTATIVE-wrong. Same-session skip 100%. 3221 maximum context bytes. Decisions identical across both runs.

F-A: S1 confirms real report.docx; its actual XML is read, summarized into an immutable real S11 ledger version, then recorder records linked derivative. F-B: S1 TENTATIVE spreadsheet and CONFIRMED script references, claimed byte inspection then independently invoked URI-owned byte verifier, S1 Change and explicit UI selection, real S7 event, complete correction pair, checkpoint persisted by task worker, forced process termination, fresh-process unknown-task discovery and exact context restoration, explicit resume. Each run records 22 S1 bindings, 1 S7 Change, 1 S11 result version and 16 Memory records. Actual valid .xlsx/.docx ZIP containers, executable Python text, .pdf objects/xref and .md files are generated in authorized temporary roots. The byte verifier establishes hashed input evidence only; it is not an Office/domain success verifier.

## Validation and failure classification

- M36: **91 passed, no skips**, final run 18.01 seconds. Final JUnit/log preserved (generated stack-trace line-end whitespace normalized for Git).
- Relevant tracked URI v1 / frozen M33.3 / governance: **1,002 passed, 58 skipped, 178 subtests passed**. Skips are disclosed in XML; not represented as exercised.
- Full tracked repository inventory (249 files): **3,260 passed, 11 failed, 65 skipped, 218 subtests passed**, 501.70 seconds. Three warnings are in the log.
- Clean managed worktree at starting HEAD: reran all 11 failure node IDs; **the identical 11 failed**, 14.55 seconds. Baseline recheck JUnit/log retained; temporary comparison worktree archival requested after processes completed. No new failure found. Baseline failures: capability-directory credential-filename exposure; M20 unavailable/failure/degraded-interpreter expectations (five tests); two M33.2 perception corpus hash mismatches; session/restart availability expectations (two tests); standing orchestrator newline-count boundary. Do not call the full repository green.
- Governance validator: **VALID**; final governance suite **37 passed**.
- Frozen anchors: **ok=True**, changed=[], 8 S4 and 24 LF anchors; RAR SHA-256 `4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95`. Complete frozen tracked source/tests/fixtures checked in boundary test and scoped Git diff, beyond pins alone.
- M36 scoped whitespace check: clean. Repository-wide diff has pre-existing SKILL.md trailing whitespace at lines 581/582; that file remains untouched.
- All **219** initial individual dirty/untracked files retain SHA-256 exactly. M36_INTEGRITY.json records count, failure identities and all implementation hashes. Unrelated M35/research/platform work excluded from commit.

## Performance and operational limits

Retrieval p50 10.4855 ms, p95 14.335 ms on Windows-11-10.0.26200-SP0, AMD64 Family 25 Model 33 Stepping 2, AuthenticAMD, Python 3.13.15. These are small local temporary-root observations collected while the final test/driver work could overlap; not a production benchmark or SLA. Separate load/fingerprint p50/p95: **UNMEASURED**. Full root scan/hash cost, shared lock contention and large histories remain practical limits; incomplete scan/budget fails closed and may ask for narrowing. No lock sharding or root-index optimization added.

Windows qualification actually executes junction and symlink assertions. Paths marked hidden/system/reparse or offline/recall may make scope incomplete/degraded; no cloud hydration. >64 MiB and unavailable hashes remain UNKNOWN and cannot establish certainty. Exact SHA-256 success/readback assumes OS/disk fsync guarantees; storage failure remains explicit.

Python zoneinfo requires installed IANA data on Windows. The initial environment lacked it; installed `tzdata==2026.4` into the qualification Python environment. No project dependency was changed. Without timezone data temporal requests fail closed as TIMEZONE_REQUIRED.

The trusted verifier registry must be restored by the URI bootstrap in each process before verdict reload, with the same supported type/version. Arbitrary trusted Python/process/filesystem compromise is outside this model/harness/user-string authority boundary; private evidence is not cryptographic protection against a compromised host. Core exposes no runtime verifier registration or network transport. Context caps protect size, do not promise exhaustive entire history; latest attested and checkpoint-linked outcomes are retained within the bounded package or whole package degrades.

No non-URI consumer exercised the package: cross_agent_portable=false. URI-Memory component is EXPERIMENTAL, not QUALIFIED_WITH_LIMITATIONS/DISTRIBUTABLE. No freeze pins are adopted here; observed implementation digests are audit inputs. Edge sufficiency is unverified; E-6 remains conditional on future OD-3 workspace/output representation. Harness/Office viability Arms A/B/C and avoided/delegated gain are not claimed. No production model/agent-loop or live UI acceptance, independent audit, release, push or next-milestone authorization is inferred.

## Governance and Git handoff

M36_STATE.md, URI_STATE.yaml, current milestone record, tracker and project memory all point to `M36_IMPLEMENTED_VERIFICATION_READY_FOR_INDEPENDENT_AUDIT`. Freeze gate stays open, closing_audit=REQUIRED_NOT_PERFORMED, integration_authorized=false, no INT-* event. Planning history retained additively.

A bounded implementation commit is created only after all final checks; its immutable identity is returned in the implementer's final response (this report belongs to that commit). Prior dirty work remains unstaged. Nothing pushed. Rollback is revert of the bounded M36 commit; no existing application imports depend on Memory. Qualification uses temporary data roots only.

## Exact recommended independent closing-audit prompt

> You are the independent closing auditor for URI M36 — URI-Memory Minimum in C:\Users\cheta\Development\Uri\_V1. Review the bounded M36 implementation commit identified by the handoff, against implementation starting HEAD 23f5cd9a5f1ac5d17d431c7a76a15533e5c570a4; frozen M33.3 baseline is 291c9daa48435200c4b56857d0e3bc630016e82a. Read the accepted M36 plan including §§17–19 (A2/A3/A4), original and A2 focused pre-audit reports, M36_STATE.md, URI_STATE.yaml, M36_IMPLEMENTATION_REPORT.md, M36_QUALIFICATION_MATRIX.md and recorded artifacts. Independently trace actual contracts/log/index/source/recorder/verifier/retrieval/context/adapter paths and real S1/S7/S11 driver; do not trust this implementer's report or test count. Re-run 91 M36 tests, the predeclared qualification driver, relevant frozen/regression/governance checks, frozen hash and whole-scope comparison, and scoped whitespace. Check Q-A2-1..11, A3 A–G, A4 H1–H3 and not budget.xlsx through actual BindingService.respond; require zero wrong CONFIRMED. Inspect complete collision evidence, trusted raw intake, immutable rounds, safe checked handles/junction/cap/recall behavior, exact read-back persistence and faults, causal state authority/forks, correction-pair crash/retry, bootstrap-only verifier receipts and protected negative verdicts, historical bindings and unknown-task forced-termination resume, task/user isolation and package bounds. Distinguish the 11 independently baseline-reproduced full-suite failures and disclosed skips from new failures. Preserve all unrelated dirt and frozen M33.3 files; no S13/Brain/UI/legacy/Office/Edge/Harness/S9/harness_run_ref scope expansion. Report concrete findings with file/line and evidence, acceptance-gate dispositions, preserved boundaries, limitations and independent ACCEPT/ACCEPT_WITH_DOCUMENTED_LIMITATIONS or required repairs. Do not silently promote/freeze, implement out-of-scope remediation, commit, push or initiate production integration; return the audit verdict for the authorized workflow's next action.

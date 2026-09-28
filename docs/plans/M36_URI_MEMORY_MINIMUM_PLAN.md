# M36 — URI-Memory Minimum (pre-Office demonstrator)

**Status:** `PLAN_A2_REPAIRED_AWAITING_PG_M1_FOCUSED_RECHECK`. PG-M1 verdict: `PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS`; A2 is ready for focused independent re-check, not fully accepted. Implementation is **not** authorized by this document.
**Date:** 2026-09-28.
**Author:** Claude Code (Opus 5.5), Architect / Pre-Auditor role. Not independent of this plan.
**Starting HEAD:** `291c9daa48435200c4b56857d0e3bc630016e82a` on `m35-uri-v1-parallel-architecture` (local = `origin`, 0/0).
**Component identity:** `URI-Memory` (`docs/governance/URI_STATE.yaml` → `reusable_components`, status `NOT_STARTED`). This plan does not change that status. Completing M36 would justify `EXPERIMENTAL` at most (see §12.4).
**Parent context:** M33.3 is `CLOSED_FROZEN` at `291c9da`. Its slice S9 (durable learned reference tie-break) was re-homed to URI-Memory/D4. S9 stays deferred under this plan (§3, decision D4-R1).
**State file:** `docs/plans/M36_STATE.md`.

Intended sequence (User, 2026-09-28): M33.3 CLOSED_FROZEN → **Memory minimum (this plan)** → Edge minimum → isolated URI Office vertical demonstrator → iterate from real evidence.

**A2 reading rule (2026-09-28):** §17 is the controlling repair specification for F-1…F-11 in `M36_PG_M1_INDEPENDENT_PREAUDIT_REPORT.md`. Draft wording retained below is historical wherever expressly superseded by §17. The original §15/§16 self-review claims are not evidence of current acceptance. No Memory implementation or PG-M2 work is authorized.

---

## 0. Acceptance criteria for this plan (defined first, per CLAUDE.md protocol)

This plan is acceptable only if all of the following hold. §15 records the self-review against them.

- **PA-1** Every claim about existing mechanisms cites a repository path, and states which checkout it means (`_V1 uri_core/`, `_V1 uri_v1/`, or the protected legacy `uri-agent` checkout).
- **PA-2** Reuse is checked before any new mechanism is proposed. Each new module names what it reuses, adapts, or why nothing fits.
- **PA-3** No frozen M33.3 artifact is modified. No hash-pinned file changes (`uri_v1/turn/rar_deterministic.py`, `uri_v1/turn/rar_contracts.py`, Batch A battery). No change to S1/S2/S3/S4/S7/S10/S11/S12 code or tests.
- **PA-4** No S13 production integration. No `/ask`, agent-loop, or `uri_core/` wiring. No INT-* event. No URI-RAR adoption.
- **PA-5** No shared-memory network, no central server, no Office demonstrator code.
- **PA-6** The frozen `uri_v1` → `uri_core` import ban (`tests/test_m33_3_s1_governance_and_parity.py`) is preserved.
- **PA-7** Memory never binds a reference. RAR, the D5 certainty-tier rule, and S1 clarification keep binding authority.
- **PA-8** D4-R1 is respected: durable history may feed candidates and factual recency; no learned weights.
- **PA-9** Each demonstrator Memory requirement (§5) maps to a component and a test gate, or is explicitly deferred with its demo consequence.
- **PA-10** An implementer can build the slice from this document without repeating the investigation.

---

## 1. Baseline (verified 2026-09-28)

| Item | Evidence |
|---|---|
| HEAD / branch | `291c9da`, `m35-uri-v1-parallel-architecture`; `git rev-list --left-right --count HEAD...origin/...` = `0 0` |
| Working tree | `SKILL.md` modified; about 157 untracked paths (M35 URIv1 research scripts, reports, tests, `uri_v1/{app,arn,context,edge,execution,intelligence,recovery,safety}` and 14 `uri_v1/turn/` research files, `docs/research/URI_HARNESS_STRATEGY/`, two governance registry files). None were created or modified by this planning task. |
| Worktrees | `_V1` and `uri-agent` (`master`, `e8e3b65`) are **one repository**; also two Codex audit worktrees and one preserved baseline. |
| Governance validator | `python scripts/governance/uri_state_validator.py` → `VALID`. |
| Frozen suites sampled | `tests/test_m33_3_s1_governance_and_parity.py`, `..._r_s11_result_versions.py`, `..._r_s7_evaluation_events.py`, `..._r_closing_audit.py`: **46 passed**. |
| Legacy memory suites sampled (`_V1 uri_core/`) | `test_user_memory.py`, `test_evidence_fact_integrity.py`, `test_file_store.py`, `test_experience_store.py`, `test_graph_store_crud.py`, `test_session_persistence.py`, `test_fact_manager_evidence.py`: **110 passed**. |
| M33.3 closure | `URI_STATE.yaml` `M33.3.status: CLOSED_FROZEN`, closure evidence `docs/plans/M33_3_R_INDEPENDENT_CLOSING_AUDIT_REPORT.md` (S9 row "EXCLUDED; URI-Memory/D4", S13 row "EXCLUDED; future INT-*"). |

---

## 2. Memory evidence recovered

"Legacy" below means `_V1 uri_core/` (tracked, live production backend). The protected `uri-agent` checkout is the same repository at an older commit; the older prototype `E:\Chetan\Uri Agent\uri_prototype` (named in `hermes_uri_inventory.json`) is **not accessible on this machine** (also recorded in `docs/research/URI_HARNESS_STRATEGY/00_INDEX.md`).

### 2.1 Implemented and live (`_V1 uri_core/core/`)

| Mechanism | Path | What it gives | Known limits |
|---|---|---|---|
| `Fact` + status lifecycle | `facts.py` | Statuses `CONFIRMED/VERIFIED/PROVISIONAL/HISTORICAL/SUPERSEDED/EXPIRED`; `evidence_ids`, `confidence`; `verify()` rejects model actors | No `STALE`; `EXPIRED` never set (M22 proposal §6) |
| Append-only supersession | `fact_manager.py`, `state.py` (`fact_history`) | Superseded values kept in order; second supersession never erases the first | Session-scoped only |
| `MemoryStore` (user memory) | `user_memory.py` | Per-user JSON, consent `user_provided / user_confirmed / pending_confirmation`; `is_eligible_for_personalization` gate; credential guard | `update()` overwrites in place, `delete()` hard-deletes: no history |
| `ExperienceStore` | `experience_store.py` | Task-outcome summaries (`actions, decisions, results, failures, corrections, learned, unresolved`) | Free-text summaries; no source hashes |
| `ConversationHistoryStore` | `conversation_history.py` | Durable per-session transcript | Transcript only; no references |
| `FileStore` | `file_store.py` | UUID `file_id`, session-scoped attachments, `to_reference()` bounded handle | Upload store, not a source-of-truth index of user folders |
| `EvidenceLedger` | `evidence_fact_integrity.py` | `EvidenceRecord(source_type, evidence_id, retrieved_at, source_reference, excerpt, metadata)`, per-user file store | Not linked to tasks/results |
| `GraphStore` / engine / ingest | `graph_store.py`, `graph_engine.py`, `graph_ingest.py` | Per-user SQLite; edge `status` ACTIVE/HISTORICAL/SUPERSEDED; history hidden unless `include_historical=True` | Ingestion dormant in production (registry FIND-MEM-001) |
| `GraphifyIndex` | `graphify_index.py` | System-level pointer index of capabilities/skills/workflows/memory | Install-wide, not per-task |
| Turn State precedence | `turn_state.py`; `docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md` §9 | Precedence: latest turn > recent turns > this turn's results > active session state > confirmed durable memory > graph | Legacy loop only |
| `MemorySettings` | `memory_settings.py` | Per-user presentation/budget preferences | No authority |

### 2.2 Implemented in `_V1 uri_v1/` (tracked, M33.3 frozen)

| Mechanism | Path | Relevance |
|---|---|---|
| Caller-scoped storage | `uri_v1/user_storage.py` | `user_scoped_path` (UUID-only), `locked_append`. Re-implements `uri_core` patterns because `uri_v1` may not import `uri_core`. **Direct reuse.** |
| Result versions (S11) | `uri_v1/results/version_ledger.py` | Append-only, content-addressed (SHA-256) versions with `GENERATED / USER_EDIT / REDO` origins, write-once blobs, fail-closed `edited_status`. **Derivative store reused as-is.** |
| Redo coordinator (S11) | `uri_v1/results/redo.py` | Redo after Change without overwriting user edits |
| Evaluation events (S7) | `uri_v1/evaluation/events.py`, `store.py`, `trace_context.py` | `CHANGE / FEEDBACK_* / EDIT_CORRECTION` events, ids only, durable ON/OFF, month-partitioned JSONL. **Correction signal source and durable-OFF precedent.** |
| Binding / clarification (S1) | `uri_v1/reference_clarification/` | `BindingService`, `ClarificationBundle` (multi-reference), `CandidateFact` with `source` locator slot; grounds only title/type/owner/recency (Plan A R4.1 F-4) |
| Session evidence adjunct (S1) | `uri_v1/reference_clarification/session_adjunct.py` | Session-local selections/clues/corrections; "may annotate or reorder ties but never bind" |
| RAR contracts | `uri_v1/turn/rar_contracts.py` (hash-pinned) | `RARCandidate(id, title, candidate_type, recency_rank, domain_tags, owner, is_attachment, exact_aliases, description)`, `RARQuery`, `RARDeterministicAnchor` |
| Active context (A2.3) | `uri_v1/turn/active_context.py` | Same-session working set: active artifacts/entities, prior operation, workflow summary |
| Clarification store | `uri_v1/reference_clarification/store.py` | **Process-local only** |

### 2.3 Frozen offline evidence (not a runtime module)

- `scripts/m33_3_s4_source_to_candidate.py` (S4, frozen): `SourceRecord(candidate_id, title, candidate_type, source_kind, locator, created_at, domain_tags, owner, is_attachment)`, immutable `EvidenceEnvelope`, projection to `RARQuery`, 16-ID / 16,384-byte budget, fail-closed over budget, no invented candidates. This is the only implemented instance of Plan B R2.2's "provenance-bearing evidence envelope". It is a script, not importable runtime code.

### 2.4 Planned or proposed, never implemented

| Item | Path | Status |
|---|---|---|
| Relevance-scoped retrieval ("M22.10") | `docs/plans/M22_MEMORY_CONTEXT_RETRIEVAL_ARCHITECTURE.md` | Proposal, never accepted |
| Passive memory candidates | `docs/plans/M28_PASSIVE_MEMORY_CANDIDATE_PIPELINE_PLAN.md`, `M28_STATE.md` | `ACCEPTED`, implementation not started |
| Reference Evidence Gateway | `docs/plans/M33_3_URI_BRAIN_ARCHITECTURE_PROPOSAL.md` R2.2–R2.3 | Conceptual; lists URI-Memory as a future provider |
| Memory Engine lifecycle | `docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` §14–15 | `Explore → Prototype → Benchmark → Tune → Cross-Agent Qualification → Freeze Contract → URI Integration`; reusable-core / thin-adapter shape |
| `KnowledgeDelta` | `docs/plans/M35_URIV1_A0_PARALLEL_SKELETON_REPORT.md` §4 | Deferred; `uri_v1/knowledge/`, `uri_v1/context/` are empty placeholders |
| Execution Capsule, verifier, state ownership | `docs/research/URI_HARNESS_STRATEGY/05_TARGET_ARCHITECTURE.md` §6, §8, §10 (untracked research) | "URI owns memory; harness state is cache"; D-C ruling deferred. Research only, not governance authority |
| Office exemplar E-P5 | `docs/research/URI_HARNESS_STRATEGY/08_EXPERIMENT_ROADMAP.md` | "make this script work with this spreadsheet", verified-not-claimed success |

### 2.5 User decisions that govern Memory

- **D4** (2026-09-26, `URI_STATE.yaml` `architecture_decisions`): durable cross-session learned reference evidence deferred to URI-Memory; no ad-hoc durable reference-memory store.
- **D4-R1** (2026-09-28, this session, direct User answer): **history yes, learning no.** Recorded durable task/outcome/correction history may feed cross-session reference resolution as grounded candidates and factual recency. Learned preference or tie-break weights, frequency-based preference, and repetition-based auto-promotion stay deferred (S9).
- **D3, D5** (unchanged): models never create binding authority; only certainty-tier RAR rules confirm.
- Consequence-aware binding rule (User, 2026-09-26): reversible actions (read, open, summarize, draft) may proceed on a visible TENTATIVE binding; consequential actions need confirmation.
- **Added 2026-09-28 after drafting (amendment A1, §16):** User rulings D-A (OD-1), OD-2, OD-3, OD-4, OD-5, requirement VG-1 and principle LF-1 on external execution harnesses. None changes the Memory boundary; §16 records how each bears on M36.

### 2.6 External research (research-before-build rule)

Checked 2026-09-28 against primary documentation. Adopt the principle, not the code.

| System | Finding | Use in M36 |
|---|---|---|
| Graphiti / Zep ([docs](https://help.getzep.com/graphiti/getting-started/overview)) | Bi-temporal edges; contradictions handled by invalidation, not deletion; episodes carry provenance | **Adopt principle**: append-only records, supersession by new record, `recorded_at` plus validity derived from supersession, trace/turn as episode |
| MCP reference memory server ([repo](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)) | Entities/relations/observations in a JSONL file; delete tools | **Adopt** JSONL persistence; **reject** destructive delete of history. Candidate future non-URI adapter for cross-agent qualification |
| Letta ([archival](https://docs.letta.com/guides/core-concepts/memory/archival-memory), [blocks](https://docs.letta.com/guides/agents/memory-blocks/)) | In-context blocks, recall (conversation), archival (queried on demand) | **Adopt tiering**: session tier always first; durable tier queried only on demand |
| Mem0 ([paper](https://arxiv.org/html/2504.19413v1)) | LLM chooses ADD/UPDATE/DELETE/NOOP | **Reject** for URI: a model may not delete or supersede memory (D3 analogue). Supersession is deterministic and user- or verifier-originated |

Not researched: embedding/vector retrieval engines. Semantic retrieval is deferred (§8), so this does not affect the plan.

---

## 3. Canonical current Memory state

| Question | Answer (evidence) |
|---|---|
| Decided | D4, D4-R1, D3, D5; Memory Engine lifecycle (A3 §15); reusable-core/thin-adapter shape (A3 §14); `uri_v1` never imports `uri_core` (frozen test); canonical precedence (agent-loop §9); consent gate for user facts (`user_memory.py`) |
| Implemented | Legacy `uri_core` stores (§2.1), live but mostly unwired for provenance-linked task memory; `uri_v1` S1/S7/S11 primitives (§2.2) |
| Only planned | M22.10 retrieval, M28 passive candidates, Reference Evidence Gateway, `KnowledgeDelta` |
| Experimental | S4 envelope (offline script); M35 URIv1 research modules (untracked) |
| Frozen | All M33.3 slices S1–S8, S10–S12 |
| Unresolved before this session | D4 scope once URI-Memory exists (resolved: D4-R1); URI-Memory architecture (`architecture_defined: false`) |
| Superseded | A0 reuse table's `SHARE` classification for `FileStore`/`ConversationHistoryStore` is superseded in practice by the frozen S1 import ban (see G-2) |

---

## 4. Conflicts and gaps

| ID | Finding | Effect on this plan |
|---|---|---|
| G-1 | `URI_STATE.yaml` says no code claims `URI-Memory`, yet `_V1 uri_core/` holds a large live memory estate | Not a contradiction of identity, but a duplication risk. M36 does not duplicate user-fact storage (§7.9) |
| G-2 | A0 report classifies `FileStore`/`ConversationHistoryStore` as `SHARE`, but frozen S1 test forbids any `uri_v1` import of `uri_core` | M36 lives in `uri_v1/memory/` and imports nothing from `uri_core`. Legacy data is not read in M36 (deferred to S13/INT) |
| G-3 | FIND-MEM-001: tested memory/graph with no live producer stayed empty | M36 qualification must produce records through real `uri_v1` flows, not hand-built fixtures (gate Q-E2E) |
| G-4 | `MemoryStore.update/delete` rewrite history | Legacy, out of scope; M36 is append-only |
| G-5 | `uri_v1` session state is process-local | Resume-later needs durable task records (§7.4) |
| G-6 | S4 envelope exists only in a frozen script | M36 re-implements the envelope shape in `uri_v1/memory/` with a lineage comment citing the S4 script; the script stays untouched |
| G-7 | No `uri_v1` registry of real files; S12 is fixture-backed | M36 adds an authorized-root source registry (§7.3) |
| G-8 | S1 `CandidateFact` grounds only title/type/owner/recency | Memory cannot show "last used in task X" in clarification without reopening S1. M36 encodes it as `recency_rank` only; richer display deferred |
| G-9 | A3 §14 forbids calling a component reusable before cross-agent qualification | M36 contract stays URI-internal; status at most `EXPERIMENTAL` |
| G-10 | **Historical draft claim, disproved by PG-M1 F-1; superseded by A2 §17.1.** Memory-sourced candidates carry no deterministic anchors unless produced by a qualified producer | Original claim: "A typed exact filename resolves at most TENTATIVE." Frozen S1 can confer CERTAINTY on a unique verbatim title in the supplied subset without an explicit anchor. Exact-name collision completeness must therefore be established before projection; merely omitting anchors is insufficient. |
| G-11 | Harness strategy research is untracked | Cited as research input only; Execution Capsule is not adopted by M36. M36's context package is shaped so a future capsule `context` field can consume it. *Update 2026-09-28 (A1):* harness role now governed by User ruling D-A (OD-1); the research stays untracked and non-authoritative (§16) |

---

## 5. Demonstrator Memory requirements

Flows: **F-A** "Find/open/summarize this document"; **F-B** "URI, make this script work with this spreadsheet" (two references, execution, verification, resume).

| # | Requirement | Needed by | M36 component | Gate |
|---|---|---|---|---|
| R1 | Identify and bind the file(s): memory supplies grounded candidates; RAR/S1 bind | F-A, F-B | Source registry + retrieval + envelope (§7.3, §7.5, §7.6) | Q-2, Q-3 |
| R2 | Recall recent task state in the same session | F-B | Session tier first (§7.5 step 1) | Q-4 |
| R3 | Recover older task/file context in a new session | F-A, F-B | Durable task records + recency (D4-R1) | Q-5 |
| R4 | Preserve source provenance | both | `SourceRef` with root, relative path, SHA-256, observed time | Q-6 |
| R5 | Distinguish original source from generated derivative | both | `DERIVATIVE` records pointing to S11 result versions with `derived_from` source hashes | Q-6 |
| R6 | Retain task outcome | F-B | `OUTCOME` records with verification status (verified vs claimed) | Q-7 |
| R7 | Record corrections | both | `CORRECTION` records (supersession), linked to S7 `CHANGE` event IDs | Q-8 |
| R8 | Resume work later | F-B | Task status + bound references + last outcome + next step, rebuilt after restart | Q-5, Q-9 |
| R9 | Stale/superseded context never silently wins | both | Staleness check against live source hash; superseded/tombstoned excluded from "current" | Q-10 |
| R10 | Compact grounded context package for reasoning/execution | both | `MemoryContextPackage` (§7.7), bounded, labelled | Q-11 |
| R11 | No leakage of unrelated private memory | both | Per-user paths; task-scoped package; no user-fact kind | Q-12 |

Deferred with demo consequence: semantic "the one about budgets" matching without title words (falls to clarification); Gmail/Drive as sources (demo uses local folders); cross-device sync (single machine).

---

## 6. Reusable mechanisms: decision per mechanism

| Mechanism | Decision | Reason |
|---|---|---|
| `uri_v1/user_storage.py` | **REUSE as-is**, with Memory-local append protocol | Path scoping and locking reused; `locked_append` does not repair torn tails. A2 §17.8 adds boundary recovery and read-back in `memory/log.py`, without changing the frozen helper. |
| `uri_v1/results/version_ledger.py` (S11) | **REUSE as-is** for derivative content | Content-addressed, append-only, per-user. Memory stores only `result_id`/`version`/SHA |
| `uri_v1/evaluation/` (S7) | **REUSE by reference** | Corrections cite `event_id`; `trace_id` via `trace_context.require_trace_id`; durable ON/OFF pattern mirrored |
| S7 store layout (month-partitioned JSONL, best-effort writes) | **ADAPT pattern** | Memory log differs: it must not silently drop writes (§7.10) |
| S4 `EvidenceEnvelope` | **RE-IMPLEMENT shape** in `uri_v1/memory/uri_adapter/envelope.py` with lineage comment | Script is frozen and not importable |
| `uri_v1/turn/rar_contracts.py` | **CONSUME read-only** | Projection target; hash-pinned |
| `uri_v1/reference_clarification/` (S1) | **CONSUME read-only** | `CandidateFact` `source` slot receives memory locators |
| Legacy `Fact` status model / `fact_history` | **ADAPT principle** (no import) | Status vocabulary and append-only supersession |
| Legacy `GraphStore` history-hidden-by-default | **ADAPT principle** | Default queries exclude superseded; explicit opt-in for history |
| Legacy consent gate (`is_eligible_for_personalization`) | **Not needed in M36** | M36 stores no user facts |
| Legacy `ExperienceStore`, `ConversationHistoryStore`, `FileStore`, `EvidenceLedger`, `GraphStore` data | **DEFER (S13/INT)** | Import ban; reading legacy data is production integration |
| Legacy `graphify_index.py`; repository `graphify-out/` | **Not used** | `graphify-out/` is development tooling, not URI runtime. `GraphifyIndex` is `uri_core` and install-wide. Graphify hints stay a future provider "never proof" (Plan A R2.7) |

---

## 7. Minimum Memory boundary (the M36 slice)

### 7.1 Package layout

Reusable core (agent-neutral; imports only stdlib and `uri_v1/user_storage.py`):

```
uri_v1/memory/
  __init__.py            public exports
  contracts.py           enums, SourceRef, MemoryRecord, payload schemas, validation
  log.py                 per-user append-only JSONL log, quarantine, durable ON/OFF
  index.py               derived in-memory view: current vs superseded vs tombstoned, staleness
  sources.py             authorized roots, scan, fingerprint
  recorder.py            typed write API (task, state, outcome, derivative, correction, forget)
  retrieval.py           session-first, bounded, deterministic candidate retrieval
  context_package.py     MemoryContextPackage builder with budgets
  telemetry.py           ids-only telemetry records
```

URI adapter (the only memory modules that may import RAR/S1/S7/S11):

```
uri_v1/memory/uri_adapter/
  __init__.py
  envelope.py            MemoryEvidenceEnvelope -> RARQuery projection + CandidateFact sources
  links.py               typed links to S11 ResultVersion and S7 EvaluationEvent ids
```

A new AST test enforces this split (§11, T-BOUNDARY).

### 7.2 Contracts (`contracts.py`)

**A2 supersession notice:** the draft provenance/authority table, TASK_STATE/OUTCOME/CORRECTION semantics and freshness vocabulary below are replaced or extended by §17.2, §17.3, §17.6 and §17.11. Their closed matrices govern; draft "any / MODEL_DERIVED" does not authorize arbitrary kinds.

Plain frozen dataclasses, `from __future__ import annotations`, closed enums, the style of `uri_v1/results/version_ledger.py`. `MEMORY_SCHEMA_VERSION = "m36.memory.v1"`.

```
RecordKind      = SOURCE_OBSERVED | TASK_OPENED | TASK_STATE | OUTCOME | DERIVATIVE | CORRECTION | TOMBSTONE
Provenance      = USER_PROVIDED | SOURCE_OBSERVED | EXECUTION_OUTCOME | VERIFIER_RESULT | MODEL_DERIVED | USER_CORRECTION
Authority       = AUTHORITATIVE_SOURCE | USER_ASSERTED | VERIFIED_OUTCOME | CLAIMED_OUTCOME | DERIVED_NON_AUTHORITATIVE
Scope           = PRIVATE | SHAREABLE          # SHAREABLE reserved; any write with SHAREABLE raises (fail closed)
TaskStatus      = OPEN | WAITING_USER | PAUSED | COMPLETED | FAILED | ABANDONED
VerificationStatus = VERIFIED | PARTIALLY_VERIFIED | UNVERIFIABLE | FAILED | CLAIMED_ONLY
BindingTier     = CONFIRMED | TENTATIVE        # copied from S1/D5 outcome; memory never computes it
Freshness       = CURRENT | STALE_SOURCE | SOURCE_MISSING | DERIVATIVE_STALE | UNKNOWN
```

`Authority` is derived deterministically from `(kind, provenance)` by one pure function; callers cannot set it. Table:

| kind / provenance | Authority |
|---|---|
| SOURCE_OBSERVED / SOURCE_OBSERVED | AUTHORITATIVE_SOURCE (the file itself is authoritative; memory holds a pointer) |
| TASK_* / USER_PROVIDED, CORRECTION / USER_CORRECTION | USER_ASSERTED |
| OUTCOME / VERIFIER_RESULT with `VERIFIED` | VERIFIED_OUTCOME |
| OUTCOME / EXECUTION_OUTCOME, or any status other than `VERIFIED` | CLAIMED_OUTCOME |
| any / MODEL_DERIVED (includes all DERIVATIVE records and model-written next-step notes) | DERIVED_NON_AUTHORITATIVE |

```
SourceRef:  source_id, root_id, relpath (POSIX, normalized, no '..'), media_type,
            content_sha256, size_bytes, mtime_ns, observed_at
MemoryRecord:
  record_id (uuid4 hex), schema_version, user_id, scope, kind, provenance, authority,
  recorded_at (UTC ISO), session_id?, trace_id?, task_id?,
  subject_ids: tuple[str,...]          # source_ids / result_ids this record is about
  source_refs: tuple[SourceRef,...]    # pointers observed at record time
  supersedes: tuple[str,...]           # record_ids this record replaces (never edits them)
  payload: kind-specific closed dict (below)
```

Payload schemas (validated; unknown keys rejected; every string bounded, 512 chars for labels, 2,000 for notes; credential-looking values rejected by a re-implemented check with a lineage comment citing `uri_core/core/security_guards.py`):

- `TASK_OPENED`: `objective_label`, `origin_turn_trace_id`.
- `TASK_STATE`: `status`, `references` (tuple of `{ref_key, source_id, content_sha256, binding_tier, binding_id?}`), `next_step?` (with its own provenance), `last_outcome_record_id?`.
- `OUTCOME`: `action_label`, `verification_status`, `verifier_id?`, `inputs` (source_id@sha), `outputs` (source_id@sha or result_id@version), `exit_code?`, `evidence_ids` (S7/S11 ids, ids only).
- `DERIVATIVE`: `result_id`, `result_version`, `content_sha256` (from S11), `derived_from` (source_id@sha tuple), `derivative_kind` (`summary`, `modified_script`, `output_file`, `other`).
- `CORRECTION`: `target` (`record_id` or `{task_id, ref_key}`), `wrong_source_id?`, `right_source_id?`, `s7_event_id?`, `note?`.
- `TOMBSTONE`: `target_record_ids`, `reason` (`USER_FORGET`).

No record stores document or email body text. Derivative text lives in the S11 blob store.

### 7.3 Sources: files as durable memory (`sources.py`)

**A2 supersession notice:** scan/path containment, hash-cap handling and source eligibility below are replaced by §17.1, §17.3 and §17.7. "Skip symlinks" and a string prefix check are not sufficient on Windows.

- The user registers **authorized roots** (local folders) explicitly. `root_id` = uuid4 hex. Roots live in a small per-user `memory/sources.json` (schema-versioned, written atomically with `os.replace`), not in the record log. Removing a root is allowed; records that cite it stay in the log and read `SOURCE_MISSING`. Nothing outside a registered root is ever scanned or referenced.
- `source_id` = `sha256(root_id + "\0" + normalized_relpath)[:32]`. Stable across sessions while the file stays at the same path. Rename or move produces a new `source_id`; the old one reads `SOURCE_MISSING` (move detection by hash is deferred).
- `scan(root_id, *, max_files, max_depth, extensions)` is bounded, deterministic (sorted), skips symlinks and hidden/system files, and never follows paths outside the root (resolved-path prefix check).
- `fingerprint(source_id)` reads the file and returns a fresh `SourceRef` (SHA-256, size, mtime). Hashing is lazy: done when a source becomes a candidate or is used in a task, not for the whole root. Cap per-file hashing at a configured size (default 64 MiB); above it `content_sha256 = None` and freshness `UNKNOWN`.
- A `SOURCE_OBSERVED` record is appended only when a source is actually used (bound, read, or produced), not for every scanned file. This avoids duplicating the file system into memory (principle 4).

### 7.4 Log and index (`log.py`, `index.py`)

**A2 supersession notice:** append success, quarantine, currentness and TASK_STATE selection below are replaced by §17.2, §17.8 and §17.11. Latest timestamp alone never determines task currentness; successful append alone never establishes persistence.

- Storage: `user_scoped_path(user_id, "memory", root)` → `memory/log-YYYY-MM.jsonl`, one JSON object per line, written through `locked_append`, `fsync` before returning success.
- **Write failures are not swallowed** (differs from S7's best-effort policy): `append()` returns `WriteResult(persisted: bool, reason)`. The caller must surface `persisted=False` (for example, "outcome not saved"). Tests enforce that a failed write never reports success.
- Durable OFF (per-user `settings.json`, same shape as S7 `set_durable_enabled`): writes return `persisted=False, reason=DURABLE_OFF`; session tier keeps working.
- Read path: `index.load(user_id)` streams all partitions, validates each line; malformed lines go to `memory/quarantine.jsonl` (copied, never deleted from the log) and are counted in telemetry. Unknown `schema_version` → the record is quarantined, not interpreted.
- Derived view (rebuilt on load; kept in process with an mtime check for reload):
  - `current(kind, ...)`: records not superseded and not tombstoned.
  - `history(record_id)`: full supersession chain, oldest first.
  - `task(task_id)`: latest `TASK_STATE` by `recorded_at` then log order; conflicting concurrent states (two non-superseded states with the same parent) are returned as `CONFLICT`, never auto-merged.
- Supersession: a new record with `supersedes=(old_id,)`. The old record stays in the log. The index marks it superseded. A superseded record can never be superseded "back" silently; restoring requires a new record that supersedes the correction.
- Forget: `TOMBSTONE` hides targets from all non-history reads. Physical purge exists only as `reset(user_id)` (deletes the user's memory directory, mirroring S7 `reset`). Selective physical purge (log compaction) is deferred.

### 7.5 Retrieval path (`retrieval.py`) — session-first

**A2 supersession notice:** the numbered draft retrieval algorithm and ranking below are replaced by §17.1, §17.3, §17.5, §17.9 and §17.10. In particular, changed live sources are rediscovered, temporal/task filters are defined, exact names require collision completeness, and clarification snapshots cannot be re-ranked.

Input `MemoryQuery(user_id, session_id, reference_expression, type_hint?, task_id?, turn_attachment_source_ids, session_working_set, max_candidates=16, max_bytes=16384)`. `session_working_set` is supplied by the caller (from `ActiveContext` or the demonstrator session); memory does not own session state.

1. **Session tier.** Candidates = current-turn attachments ∪ session working set. If the caller reports an in-session CONFIRMED binding for this `ref_key`, durable retrieval is **skipped** and telemetry records `SKIPPED_SESSION_CONFIRMED`.
2. **Task tier** (when `task_id` given): sources referenced by the task's current `TASK_STATE`, plus its outputs.
3. **Durable history tier** (D4-R1): sources appearing in current (non-superseded, non-tombstoned) `TASK_STATE`/`OUTCOME`/`DERIVATIVE` records, filtered deterministically by `type_hint` and case-folded token overlap between `reference_expression` and title/relpath stem. Ordered by last-used time. No learned weights, no counts, no model call.
4. **Registry tier**: bounded lexical filename match inside authorized roots when tiers 1–3 give no candidate.
5. Freshness check for every candidate (re-fingerprint only candidates, not the root). `STALE_SOURCE` / `SOURCE_MISSING` candidates are **excluded from the RAR candidate set** and listed in the context package's `stale` section, so a stale reference can prompt a visible question instead of silently binding.
6. Budget: stop at 16 candidates or 16,384 canonical bytes. If a tier would be cut mid-way, return `BUDGET_EXCEEDED` for the whole query (fail closed, S4 precedent). The caller then clarifies or narrows.

Order is tier order, then last-used time. `recency_rank` = position in that order (0 = most recent), which is the only way durable history influences RAR (factual recency, D4-R1).

### 7.6 Interaction with RAR / ARN / S1 (`uri_adapter/envelope.py`)

**A2 supersession notice:** attachment anchor production is governed by §17.4; candidate eligibility by §17.1/§17.3; binding capture and source revalidation by §17.9/§17.10. The draft "one attachment matching the type hint" rule is withdrawn. RAR/ARN/S1 remain read-only consumers.

- `MemoryEvidenceEnvelope`: immutable; `candidates` (tuple of `{source_id, SourceRef, tier, last_used_at, provenance_locator}`), `authorized_ids`, `current_turn_attachment_ids`, `authorization_basis = "memory_authorized_roots"`, `stale`, `telemetry_ref`.
- `project(envelope, reference_expression, local_evidence) -> RARQuery`: `RARCandidate(id=source_id, title=basename, candidate_type=media class, recency_rank, is_attachment, owner=None, exact_aliases=(), domain_tags=())`. `deterministic_anchor` carries only `current_attachment_id` when exactly one current-turn attachment matches the type hint. No other anchors (G-10).
- `candidate_fact_sources(envelope) -> dict[source_id, dict[axis, locator]]` supplies `CandidateFact.source` values (`memory:<record_id>` or `file:<root_id>/<relpath>@<sha12>`).
- **ARN in `uri_v1`** means RAR plus S1 clarification/attribute narrowing (`uri_v1/reference_clarification/attribute_narrowing.py`). ARN.1 in `uri_core/core/arn/` is not reachable (import ban). Memory feeds candidates; RAR and S1 decide. Memory never calls RAR.
- After binding, the demonstrator calls `recorder.task_state(...)` with the bound `source_id`, content hash, and the `BindingTier` returned by S1. Memory copies the tier; it never computes one.

### 7.7 Context package (`context_package.py`)

`MemoryContextPackage` (frozen, JSON-serializable, ≤ 8 KiB default):

```
task:        {task_id, objective_label, status, next_step{text, provenance}} | None
references:  [{ref_key, source_id, display_name, content_sha256, binding_tier, freshness}]
recent_outcomes (≤3): [{action_label, verification_status, authority, recorded_at}]
derivatives (≤3):     [{result_id, version, derived_from, freshness}]
corrections (≤3):     [{target, right_source_id, recorded_at}]
stale:       [{source_id, display_name, freshness}]
conflicts:   [{task_id, record_ids}]
provenance_legend: fixed text for each Authority value
degraded:    None | reason
```

Only records for the current task and its bound sources appear. No other task's content, no user facts. Every item carries its authority. `CLAIMED_OUTCOME` and `DERIVED_NON_AUTHORITATIVE` are labelled as such. The package is the input a future Execution Capsule `context` field would take (G-11); M36 does not build the capsule.

### 7.8 Execution and outcome

**A2 supersession notice:** caller-provided provenance and `verifier_id` are not authority. §17.6 replaces the draft verifier-admission rule; §17.3 and §17.11 govern stale/superseded outcome and derivative views.

- `recorder.outcome(...)` accepts `verification_status=VERIFIED` only with provenance `VERIFIER_RESULT` and a `verifier_id`. Anything a model or harness claims is recorded as `CLAIMED_ONLY` with provenance `EXECUTION_OUTCOME`.
- Produced files inside an authorized root are fingerprinted and recorded as `SOURCE_OBSERVED` plus `DERIVATIVE` (with `derived_from` input hashes). Produced text (for example a summary) is written to the S11 ledger by the caller; memory records `DERIVATIVE` with the S11 `result_id`/`version`/SHA.
- `DERIVATIVE_STALE`: at read time, if any `derived_from` source hash differs from the live source hash, the derivative is marked stale in the package.

### 7.9 Privacy and authority

**A2 supersession notice:** the final draft generic supersession paragraph is replaced by the closed, kind-specific matrix in §17.2 and URI-owned verifier boundary in §17.6. Typed trusted entry points derive provenance; it is not a caller obligation that an untrusted model can satisfy by declaring a string.

- Per-user storage through `user_scoped_path` (UUID-only). Cross-user reads are impossible by path construction; a test proves it.
- Only `Scope.PRIVATE` is writable. `SHAREABLE` exists so records are forward-compatible with a future shared-knowledge network (uuid record IDs, content hashes, provenance, append-only log are all replication-friendly). No network code, no server.
- No user-fact kind: user preferences stay in legacy `MemoryStore` until an INT event unifies them (avoids duplication, G-1).
- Memory has no authority over execution. It is never imported by any gate. A test asserts `uri_v1/memory` is not imported by `uri_v1/reference_clarification/` and does not import `uri_v1/turn/rar_deterministic.py`.
- A model can only reach memory writes through the recorder with provenance `MODEL_DERIVED`, which can never supersede a `USER_ASSERTED`, `AUTHORITATIVE_SOURCE`, or `VERIFIED_OUTCOME` record (recorder rejects it). Only `USER_CORRECTION` or `VERIFIER_RESULT` records may supersede those.

### 7.10 Failure and fallback

**A2 supersession notice:** source/hash failures follow §17.1/§17.3/§17.7, malformed storage follows §17.8, and task conflict/correction follows §17.2/§17.11. The historical table below must be read with those stricter rules.

| Failure | Behaviour |
|---|---|
| Log unreadable / directory missing | Retrieval returns session tier only, `degraded=STORE_UNAVAILABLE`; never invents history |
| Malformed line / unknown schema | Quarantined copy, counted, skipped |
| Write failure / durable OFF | `persisted=False` returned; caller must show it |
| Source root missing | Root marked unavailable; its sources `SOURCE_MISSING` |
| Hash cap exceeded | Freshness `UNKNOWN`; never treated as `CURRENT` for derivative checks |
| Budget exceeded | `BUDGET_EXCEEDED`, no partial candidate set |
| Conflicting task states | `CONFLICT` surfaced in package; no automatic choice |

### 7.11 Telemetry (`telemetry.py`)

Per query and per write, ids and enums only: `trace_id`, tier counts, skip reason, candidates returned, stale/missing/superseded suppressed, budget outcome, quarantine count, `persisted`, latency (µs) for load, retrieval, fingerprint. Written to `memory/telemetry-YYYY-MM.jsonl` best-effort (telemetry loss must not fail a write). No titles, paths, or text. Qualification aggregates go to `docs/plans/M36_TELEMETRY.json` / `M36_AGGREGATES.json`.

---

## 8. Explicit deferred scope

- S9 learned tie-breaking, frequency preference, repetition-based promotion (D4-R1).
- Semantic/embedding retrieval and "the one about budgets" matching without lexical overlap.
- Deterministic anchor production for memory candidates (exact-title/exact-ID); needs S4-grade qualification.
- Move/rename detection by content hash.
- Gmail, Drive, web, and other non-folder sources.
- Reading legacy `uri_core` stores; unifying user facts; M28 passive candidates.
- Shared/institutional memory, peer-to-peer sync, authority federation.
- Log compaction and selective physical purge.
- Graphify hints as a memory provider.
- Execution Capsule, verifiers, harness integration, Office demonstrator.
- Richer S1 clarification display ("last used in task X"), which would reopen frozen S1.
- `/ask`, agent loop, `uri_core` wiring (S13/INT).
- Cross-agent qualification (MCP adapter) required before any "reusable" claim.

---

## 9. Implementation plan: waves and lanes

Risk: **high** for L4 (feeds reference resolution); **medium** for L1–L3. Per the User's milestone-execution rule: lanes self-qualify, then integration, one independent audit, bounded repair, freeze.

| Wave | Lane | Scope | Depends on | Files |
|---|---|---|---|---|
| W0 | L0 Contracts | §7.2 enums, dataclasses, validation, authority derivation | — | `uri_v1/memory/contracts.py`, `__init__.py` |
| W1 | L1 Log + index | §7.4, §7.10 rows 1–3 | L0 | `log.py`, `index.py` |
| W1 | L2 Sources | §7.3 | L0 | `sources.py` |
| W1 | L3 Recorder + links | §7.8, §7.9 supersession rules; S7/S11 id links | L0 | `recorder.py`, `uri_adapter/links.py` |
| W2 | L4 Retrieval + envelope + package | §7.5–§7.7, telemetry | L1, L2, L3 | `retrieval.py`, `uri_adapter/envelope.py`, `context_package.py`, `telemetry.py` |
| W3 | L5 Qualification | §11 battery, E2E replay, determinism | L4 | `tests/test_m36_memory_*.py`, `scripts/m36_memory_qualification.py`, `fixtures/m36_memory/` |

W1 lanes are independent (separate files, only L0 shared). Do not run L5 latency measurements concurrently with other local-model benchmarks on the same machine.

No migrations: new storage only. No existing file is modified except governance files at closure (§12).

---

## 10. Workers

Per standing roles: Claude plans and audits; implementation is routed (Codex preferred for L1/L3/L4, Gemma acceptable for L0/L2 boilerplate and focused tests). If the User later assigns otherwise, follow the User. The independent closing audit must be by a different model/session than the implementer.

---

## 11. Tests and qualification gates

**A2 qualification rule:** §17.12 adds mandatory objective cases for every F-1…F-11 repair. It replaces the draft stale-source exclusion test and strengthens Q-3/Q-5/Q-6/Q-7/Q-8/Q-9/Q-10. Original gates remain mandatory with the corrected pass criteria in §17.12; no new implementation tests are written by this planning repair.

Unit/lane tests (`tests/test_m36_memory_<lane>.py`):

- **T-BOUNDARY**: AST checks: no `uri_core` import anywhere in `uri_v1/memory`; core modules import only stdlib and `uri_v1.user_storage`; only `uri_adapter/` imports `uri_v1.turn.rar_contracts`, `uri_v1.reference_clarification`, `uri_v1.results`, `uri_v1.evaluation`; nothing imports `rar_deterministic`; no network/model libraries (`ollama`, `openai`, `anthropic`, `requests`, `httpx`, `socket`).
- **T-FROZEN**: re-run frozen hash assertions (existing S1 governance test) unchanged and passing.
- Contracts: closed enums; unknown keys rejected; `SHAREABLE` write rejected; authority not caller-settable; bounds and credential guard.
- Log: append/fsync; failed write → `persisted=False`; durable OFF; quarantine of malformed and unknown-schema lines; restart reload equals pre-restart view.
- Index: supersession chain keeps both records; double supersession keeps full history; tombstone hides; `CONFLICT` surfaced; `MODEL_DERIVED` cannot supersede `USER_ASSERTED`/`VERIFIED_OUTCOME`/`AUTHORITATIVE_SOURCE`.
- Sources: no traversal outside root (`..`, absolute paths, symlinks, junctions on Windows); stable `source_id`; hash cap; missing root.
- Retrieval: tier order; session-confirmed skip; stale excluded from candidates and listed; budget fail-closed; deterministic output for identical input.
- Envelope: projection yields valid `RARQuery`; no invented IDs; only attachment anchor; `CandidateFact` sources populated.

Qualification battery (`scripts/m36_memory_qualification.py`, predeclared before the first run; thresholds frozen in `fixtures/m36_memory/threshold_gate.json`):

| Gate | Scenario (real files in a temp authorized root: `.docx`, `.xlsx`, `.py`, `.pdf`, `.md`) | Pass |
|---|---|---|
| Q-1 Frozen integrity | Hash pins, full M33.3 frozen suites | 100% pass, no new failures vs baseline |
| Q-2 Grounded candidates | 40+ reference expressions across F-A/F-B shapes | 0 invented IDs; 0 candidates outside authorized roots |
| Q-3 No wrong confident binding | Memory → envelope → real `rar_deterministic` → S1 | 0 CONFIRMED bindings to a wrong source; TENTATIVE-wrong rate reported |
| Q-4 Same-session recall | Follow-up turns ("now open it", "the other one") | Session tier answers without durable read in ≥ 95% predeclared cases; telemetry proves skip |
| Q-5 Cross-session recall | New process, new session: "the spreadsheet from yesterday's task" | Correct source in candidate set 100%; top recency 100% where unambiguous by history |
| Q-6 Provenance | Every package item | 100% carry source hash + authority; derivatives link to S11 version and input hashes |
| Q-7 Outcome honesty | Verifier-verified vs harness-claimed outcomes | 0 `CLAIMED_ONLY` shown as `VERIFIED` |
| Q-8 Corrections | User "no, the other file" → S7 `CHANGE` → `CORRECTION` | Old record retained; new current; package shows corrected reference |
| Q-9 Resume | Kill process mid-task; reload | Task status, references, last outcome, next step restored exactly |
| Q-10 Stale never wins | Edit/delete a source after use | 0 stale sources in RAR candidate set; 100% listed as stale |
| Q-11 Package bounds | All scenarios | ≤ 8 KiB; tier and authority labels present |
| Q-12 Isolation | Two users, two tasks | 0 cross-user records; 0 unrelated-task records in package |
| Q-E2E No-fixture production | Records produced only by recorder calls driven by real S1 `BindingService`, S11 ledger, S7 store flows in a driver script | 100% of package content traceable to those calls (FIND-MEM-001) |
| Q-DET Determinism | Two full runs | Identical decisions and telemetry except timestamps/latency |
| Q-LAT Latency (reported, not gated) | p50/p95 load, retrieval, fingerprint on this machine | Reported with hardware metadata; `UNMEASURED` stated if not measured |

Regression: full tracked `uri_v1` suites, S1–S12 suites, governance validator `VALID`, `git diff --check` clean.

---

## 12. Governance and freeze strategy

1. This plan and `M36_STATE.md` are registered in `URI_STATE.yaml` (product milestone `M36`, planning status only) and decision `D4-R1` is recorded. Done by this planning task.
2. **Gate PG-M1**: independent pre-audit of this plan by another model/session. Required because L4 touches reference-resolution inputs (high risk).
3. **Gate PG-M2**: explicit User implementation authorization (the User's instruction for this session limits Claude to planning).
4. Freeze criteria: all lanes self-qualified; Q-1…Q-12, Q-E2E, Q-DET pass; independent closing audit `ACCEPT` or `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`; bounded repairs requalified; hash pins recorded for `uri_v1/memory/contracts.py` and `uri_adapter/envelope.py`; `URI-Memory` component status → `EXPERIMENTAL` (not `QUALIFIED_WITH_LIMITATIONS`, per A3 §14 portability rule).
5. No INT-* event. No legacy file edited. History preserved additively.

## 13. Rollback and recovery

- All new code lives under `uri_v1/memory/`, new tests, new script, new fixtures. Rollback = revert the M36 commits; no other module depends on memory until the demonstrator.
- Data: memory lives under `uri_workspace/users/<uuid>/memory/`. Qualification uses temporary roots only. `reset(user_id)` removes it.
- Schema evolution: `schema_version` on every record; unknown versions quarantined, never misread. A v2 must ship a reader for v1.
- Interrupted implementation: follow `ORCHESTRATION.md` §3.1 `WAITING_FOR_MODEL` recovery; verify partial lanes against the real diff before resuming.

## 14. Demonstrator-readiness exit criteria

M36 is demonstrator-ready when:
- **E-1** F-A can run end to end on real files: resolve → read → summarize → record derivative → recall in a new session, with provenance and freshness.
- **E-2** F-B can record two bound references, a claimed then verified outcome, a user correction, a pause, and a resume in a new process with exact state.
- **E-3 (A2 correction, §17.3/§17.11):** missing or unsafe sources never enter the RAR candidate set. Edited live sources remain rediscoverable with fresh/degraded identity; stale or superseded historical claims never appear as current grounding or current task references.
- **E-4** Gates in §11 pass and the independent audit closes.
- **E-5** The Edge minimum milestone can consume `MemoryContextPackage` without a Memory contract change (checked at Edge-minimum planning).

## 15. Self-review against §0 (draft → repair → re-check)

**Historical self-review, superseded as a current acceptance claim by PG-M1 and §17.13.** In particular, item 3 and "all satisfied" below missed F-1; PA-10 also had F-2/F-11 gaps. These original claims are retained only as audit history.

First-draft defects found and repaired before publishing:
1. Draft said memory would "reuse FileStore". Violates PA-6 (import ban). Repaired: authorized-root registry in `uri_v1`; legacy FileStore deferred (G-2).
2. Draft let retrieval rank by "times used". Violates PA-8 / D4-R1 (frequency is learning). Repaired: last-used time only.
3. Draft had memory produce exact-title anchors. Risks PA-7 (a CONFIRMED path without S4-grade qualification). Repaired: attachment anchor only (G-10).
4. Draft used S7's best-effort write policy for memory. Silent loss would break R6/R8. Repaired: `persisted` flag and mandatory surfacing (§7.4).
5. Draft planned to show "last used in task X" in clarification. Would reopen frozen S1 (PA-3). Repaired: recency rank only (G-8).
6. Draft proposed a user-fact kind. Duplicates legacy `MemoryStore` (PA-2). Repaired: removed; deferred.

Re-check: PA-1 (paths labelled `_V1 uri_core/` / `uri_v1/`), PA-2 (§6), PA-3/PA-4/PA-5/PA-6 (§7.1, §8, T-BOUNDARY, T-FROZEN), PA-7 (§7.6, §7.9), PA-8 (§7.5), PA-9 (§5 table), PA-10 (§7, §9, §11) all satisfied.

**Unverified, disclosed:**
- Real hashing/scan latency on large folders: unmeasured; affects only Q-LAT (not a gate).
- Windows junction/symlink traversal behaviour: to be proven by T-sources tests; affects the security gate if it fails.
- Whether the Edge minimum will need fields beyond `MemoryContextPackage`: unknown until Edge planning (E-5).
- The inaccessible older prototype (`E:\...\uri_prototype`) may hold further mechanisms; its absence does not change the verdict because the accessible legacy estate already covers the needed principles.

---

## 16. Amendment A1 (2026-09-28): external-harness rulings and PG-M1 readiness

**A2 supersession notice:** A1 decisions remain binding. A1's claims of already enforced verifier authority (§16.1), E-6 already being met (§16.4), stale-file exclusion (§16.5 item 6), readiness (§16.6), and completeness of self-review (§16.7) are historical and superseded by §17.3, §17.6 and §17.14. E-6 remains conditional on the later OD-3 output representation; Edge sufficiency remains unverified until an Edge plan exists. The auditor accepted §16.2 deferral; its in-M36 fallback is not selected.

**Nature:** additive. Sections 0–15 above are the plan as drafted at `1f3ec48`. They are not rewritten, except for two one-line pointers (§2.5 last bullet, G-11 row), each marked "A1". This amendment does **not** change the Memory boundary, the package layout, the contracts, the waves, or the gates.

**Inputs:**
- `docs/plans/PAPERCLIP_URI_ARCHITECTURE_RECONNAISSANCE.md` (§18 Memory implications; §24 decision addendum). Paperclip is prior art only.
- User rulings of 2026-09-28, registered in `docs/governance/URI_STATE.yaml` → `architecture_decisions`: `D-A` (OD-1), `OD-2`, `OD-3`, `OD-4`, `OD-5`, `VG-1`, `LF-1`.
- `docs/plans/URI_EXTERNAL_HARNESS_VIABILITY_GATE.md`.

### 16.1 Effect of each ruling on M36

| Ruling | Effect on M36 | Change needed now? |
|---|---|---|
| D-A (OD-1): Claude Code / Codex may be execution harnesses; not the Brain; harness never verifies itself; never canonical Memory; result `CLAIMED_ONLY` until a URI verifier says otherwise | Already enforced by §7.8 (`VERIFIED` only with `VERIFIER_RESULT` + `verifier_id`; harness claims recorded as `CLAIMED_ONLY` / `EXECUTION_OUTCOME`) and §7.9 (only `USER_CORRECTION` / `VERIFIER_RESULT` may supersede `VERIFIED_OUTCOME`). Gate Q-7 tests it. | No |
| OD-2: Brain is provider/transport-neutral; `BrainProvider` separate from `ProviderTransport/AuthMode` | M36 has no provider or model dependency (T-BOUNDARY forbids model/network libraries in `uri_v1/memory`). Memory records no Brain transport. | No |
| OD-3: workspace default `COPY_IN_COPY_OUT`; `DIRECT_ORIGINAL` only by explicit per-task choice | Memory records sources by authorized root, relpath and SHA-256 (§7.3), so both the originals and a scratch copy can be referenced. A scratch workspace is **not** an authorized root by default. Whether the future harness milestone registers it as a temporary root, or reports results only through `DERIVATIVE` + S11, is a Harness Execution minimum decision. Input hashes (`OUTCOME.inputs`, `DERIVATIVE.derived_from`) already allow stale-derivative detection (§7.8). | No |
| OD-4: restrictive default harness permissions, per-run elevation | No Memory effect. Elevation approvals belong to the approval layer, not Memory. | No |
| OD-5: harness contract in `uri_v1/execution/`; no `uri_core` import; no shared abstraction layer yet | Compatible: M36 lives in `uri_v1/memory/` and keeps the import ban (PA-6). M36 does not import `uri_v1/execution/`; any reverse dependency is a future decision. | No |
| VG-1: viability gate (Arms A/B/C; avoidance vs delegation advantage) | Memory is one of the Arm B layers whose overhead must be measurable. M36 telemetry (§7.11) already records ids-only latency and candidate counts per query, which is enough to attribute Memory overhead later. | No |
| LF-1: local first, escalate minimally | Memory retrieval is local and deterministic (§7.5). No change. | No |

**Conclusion: no structural change to M36 is required.**

### 16.2 `harness_run_ref`: decision **DEFERRED (name and constraints reserved)**

**Decision:** do not add a `harness_run_ref` field to the M36 v1 schema. Reserve the name and its constraints for a later, schema-versioned addition.

**Why deferral is safe and minimal:**
1. M36 can already record everything a harness run means for Memory without it:
   - the claimed outcome as `OUTCOME` / `EXECUTION_OUTCOME` / `CLAIMED_ONLY`
   - the verifier's result as a superseding `OUTCOME` / `VERIFIER_RESULT` / `VERIFIED` with `verifier_id`
   - inputs as `source_id@sha`, and outputs as source hashes or S11 `result_id@version`
   - `DERIVATIVE.derived_from` input hashes
   - `trace_id` linking to S7
2. No harness-run record exists yet to point at. `uri_v1/execution/` holds only a placeholder, and the Harness Execution minimum is not planned. A reference field with no real target cannot be tested in M36 without fixture-only records, which gate Q-E2E forbids.
3. §13 already defines the upgrade path: every record carries `schema_version`, unknown versions are quarantined rather than misread, and "a v2 must ship a reader for v1". Adding an optional field in `m36.memory.v2` is therefore backward-compatible.

**Reserved constraints** (binding on whichever future plan adds it):
- Name `harness_run_ref`, allowed only on `OUTCOME` and `DERIVATIVE` payloads, optional.
- Value: an opaque, bounded identifier of a URI-owned harness-run lineage record (in `uri_v1/execution/`). It is **not** a harness session id and **not** a transcript pointer.
- **Lineage, not retrievable memory:**
  - It never contributes to retrieval, ranking, candidate generation, `recency_rank`, or `MemoryContextPackage` content beyond an opaque link.
  - It is never projected into `RARQuery` or `CandidateFact`.
- **Non-authoritative:** it cannot change `Authority` or `VerificationStatus`. Only a `VERIFIER_RESULT` record produces `VERIFIED`.
- **Loss-tolerant:** a missing, expired or unresolvable referenced run record must leave every Memory record valid and readable. URI knowledge lives in Memory records and S11 content, never in a harness run or harness session.
- Harness transcripts and harness session ids are never stored in Memory records.

The v1 closed payload schemas do not contain this name. Unknown keys stay rejected in v1 (§7.2).

**If PG-M1 concludes otherwise:** if the independent auditor finds that deferral would force an incompatible change later, the smallest acceptable alternative inside M36 is to add the reserved field as optional and always absent in M36 flows, with a validation test. The auditor should state which option it accepts.

### 16.3 Implications recorded for future Edge planning (not an Edge design)

For the Edge minimum plan (the sequence item after M36; no plan file exists yet):
- Qualified local completion is a first-class source of URI value (VG-1 Arm C, G1 avoidance advantage).
- Deterministic and local mechanisms should run before external escalation where appropriate (LF-1).
- Edge should contribute to harness avoidance only where it is genuinely qualified, and must not be forced to handle work beyond its demonstrated capability.
- The viability benchmark must measure how much work avoids the external harness.
- Frozen S6 routing semantics (`uri_core/core/edge/routing_policy.py`) are unchanged. External-harness escalation is a separate, later routing concern.
- M36 exit criterion E-5 (Edge can consume `MemoryContextPackage` without a Memory contract change) is unchanged.

### 16.4 Demonstrator-readiness addition

- **E-6:** a future Harness Execution minimum can record a harness-claimed outcome and a later verifier result for F-B using only M36 v1 record kinds (a claimed `OUTCOME`, then a verified `OUTCOME` superseding it; `DERIVATIVE` with `derived_from`). `harness_run_ref` may be added later under §16.2 without changing the meaning of any v1 record.

E-6 is already met by the §7.8 design. It is stated explicitly so that PG-M1 checks it. It adds no new gate and no code.

### 16.5 Brief for the independent PG-M1 pre-audit

PG-M1 must be run by a different model/session than this plan's author (Claude Code, Opus 5.5). It must inspect the repository directly rather than trust this plan. Required determinations:
1. Is the recovered Memory state (§2, §3) accurate against the repository?
2. Is the minimum boundary (§7, §8) genuinely minimal for the demonstrator (§5)?
3. Does the design preserve frozen M33.3 boundaries (PA-3, PA-4, PA-6, T-FROZEN, hash anchors in `scripts/m33_3_r_anchors.py`)?
4. Are provenance, authority and verification semantics correct (§7.2, §7.8, §7.9), including that harness claims can never become `VERIFIED` without `VERIFIER_RESULT`?
5. Is cross-session recovery sufficient (R3, R8; Q-5, Q-9)?
6. Is it impossible for stale files to silently become candidates (§7.5 step 5; Q-10)?
7. Are corrections and supersession safe (§7.4, §7.9; Q-8)?
8. Is authorized-folder scanning bounded and safe, including Windows symlink and junction traversal (§7.3)?
9. Are privacy boundaries sufficient (§7.9; Q-12)?
10. Is the minimum sufficient for the future Edge minimum (E-5), the future Harness Execution minimum (E-6, §16.2) and the Office demonstrator (§5, §14)?
11. Does the plan avoid prematurely implementing shared or distributed memory (`SHAREABLE` fails closed; §8)?
12. If `harness_run_ref` is needed, is it designed as lineage rather than retrievable semantic Memory (§16.2), and is deferral acceptable?

Verdict vocabulary: `PG_M1_ACCEPTED`, `PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS` (listing each repair), or `PG_M1_REJECTED` (with reasons). PG-M1 does not authorize implementation. PG-M2 (explicit User authorization) is still required.

### 16.6 Readiness marker

`M36_READY_FOR_INDEPENDENT_PG_M1_PREAUDIT` as of amendment A1. Status stays `PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT`. Implementation is not authorized.

### 16.7 Self-review of A1

Checked against §0:

| Criterion | Result |
|---|---|
| PA-3 | No frozen file touched |
| PA-5 | No harness, Edge or demonstrator code |
| PA-6 | No new imports proposed |
| PA-7 | `harness_run_ref` is excluded from any binding path |
| PA-8 | No learning introduced |
| PA-9 | E-6 maps to the existing Q-7 |

One defect found in the first A1 draft and repaired: it added `harness_run_ref` to the v1 schema immediately. That conflicted with the minimality goal and with Q-E2E, because no real target record exists. It is now "deferred, reserved", with a stated fallback for the auditor.

Unverified: whether the Harness Execution minimum will register scratch workspaces as temporary authorized roots (§16.1, OD-3 row). That decision is left to that plan and does not affect M36 acceptance.

---

## 17. Amendment A2 (2026-09-28): PG-M1 bounded planning repairs

**Status:** PLAN_A2_REPAIRED_AWAITING_PG_M1_FOCUSED_RECHECK.
**Repair implementer:** Codex, bounded planning-repair role authorized by the User.
**Planning baseline:** e26d98c5b6827946c3e546663758a94bf1be7033, branch m35-uri-v1-parallel-architecture.
**Frozen baseline:** 291c9daa48435200c4b56857d0e3bc630016e82a.
**Input verdict:** PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS, report [M36_PG_M1_INDEPENDENT_PREAUDIT_REPORT.md](M36_PG_M1_INDEPENDENT_PREAUDIT_REPORT.md), §4 F-1…F-11 and §6 R-1…R-11. The report is preserved unchanged.

This is an additive text/specification repair within the existing §7.1 modules. Where A2 differs from §0–§16, A2 governs; the in-place notices above identify superseded draft rules. No Memory, Edge, harness, Office, S13, INT-*, M31 or frozen M33.3 implementation is changed or authorized. D-A, OD-2…OD-5, VG-1, LF-1, D3/D5 and D4-R1 retain their accepted meaning. The remaining low-severity PG-M1 findings F-12…F-19 are not silently declared repaired; the scope here is the eleven required repairs (with historical acceptance claims corrected and frozen scope checked).

### 17.1 F-1 — exact-name completeness before Memory-to-S1 projection

**Interpretation:** frozen S1 can grade one exact verbatim title as CERTAINTY within the supplied candidate set (authority.py:35–43). That set does not establish uniqueness across the searched authorized scope. No change to S1 is needed or permitted.

For an unqualified basename/title request the relevant scope is **all currently registered roots for this user**, plus authorized current-turn attachments and session sources, not just recent history, one tier, one folder, a type-filtered subset or the first matching root. A user may explicitly narrow the searched scope to a named authorized folder/root; the scope must be recorded and shown as such, never inferred from recency or a model hint. "Globally unique" below means within this declared authorized scope, not the entire machine.

Before project() can expose any candidate whose title or frozen RAR stem normalization exactly matches the stripped/casefolded reference expression:

1. Enumerate the entire declared scope for title/basename **and stem** collisions, irrespective of task, recency, type, history status or hash freshness. Use the frozen resolver's lexical matching semantics by lineage in the adapter; no import of rar_deterministic into Memory.
2. Build a deterministic collision-completeness receipt in the immutable envelope: scope root IDs, scan/authorization snapshot, matching source IDs, completion status and failure reason. It is query-local evidence, never a binding grant. Only COMPLETE receipts may pass the exact-name projection precondition.
3. Include **every live matching source** in the projected candidate set, even if absent from history or initially removed by a lexical/type/task filter. Multiple live matches remain ambiguous; last-used rank cannot remove a collision. Changed live sources are refreshed under §17.3.
4. A stale historic locator, inaccessible directory/file, unscanned depth, excluded hidden/system/reparse branch or size/file-count/byte/time bound must not silently make a surviving match unique. A proved-missing historical file is not live; an unverifiable historic match or an excluded branch in the declared scope makes the receipt INCOMPLETE unless absence of matching names can be independently established. Merely filtering it out is not such proof.
5. On INCOMPLETE, unavailable scope, source-identity uncertainty, or inability to include all matches within 16 candidates/16,384 bytes, return no exact-name RARQuery: BUDGET_EXCEEDED or degraded=COLLISION_SCOPE_INCOMPLETE. The caller requests scope/file clarification. A completeness flag alone cannot downgrade frozen S1, so a partial exact-title query must **not** be sent to it. Generic tentative resolution is permissible only on a subsequent non-exact expression through the unchanged S1 rules, or after explicit user clarification resolves the scope.
6. Immediately before final binding/use, revalidate the receipt and selected live source (§17.9). Changed scope membership or an expired receipt requires a new query/ambiguity round.

Only a collision-checked match is eligible for exact-title certainty. Memory still produces no new exact-title/ID anchor. The session-confirmed retrieval optimization may skip the durable history log, but cannot skip live identity or exact-name completeness checks when forming a new query.

### 17.2 F-2 — controlled task-state domain and closed supersession rules

**Interpretation:** generic provenance supersession either blocks ordinary progress or permits a latest-timestamp MODEL_DERIVED bypass. Task currentness is a validated transition chain.

Keep TaskStatus = OPEN, WAITING_USER, PAUSED, COMPLETED, FAILED, ABANDONED. Add URI_RECORDED provenance and RUNTIME_RECORDED authority for deterministic URI observations, plus VERIFIER_ATTESTED authority for negative/partial verifier verdicts (§17.6). They do not confer execution or binding authority.

All write APIs are typed. Authenticated URI callers supply trusted user-input evidence to a user method, URI-owned runtime observations to a runtime method, or a registered verifier receipt to the internal verifier method. Model/harness request dictionaries cannot select provenance/authority. A validated model proposal can cause URI to act, but the model's claim alone is never a state transition.

Closed-schema A2 extensions to §7.2: TASK_STATE carries opening_record_id, transition_evidence_ids and correction_record_id?; CORRECTION carries prior_task_state_record_id, old/new SourceRefs, new_binding_id/tier and correction_operation_id; the paired TASK_STATE carries that same operation ID. OUTCOME verifier payloads carry verifier_type/version, invocation_id, assessed_outcome_record_id, acceptance_evidence_ref/digest and attestation_ref. TASK_OPENED may carry explicit_user_labels only from actual user input. SourceRef.identity_status and the query/envelope receipt/snapshot fields are as defined below. Unknown keys remain rejected. Each transition evidence ID must resolve to the trusted user/runtime/verifier event asserted by the typed caller; a model-supplied trace string alone is not evidence.

Authority derivation is pure over the validated kind/provenance plus verification_status where applicable; validation of the trusted entry path/receipt precedes it. Loader applies the same matrices. Extend the context package's fixed provenance legend and item labels for RUNTIME_RECORDED, VERIFIER_ATTESTED, explicit identity degradation and HISTORICAL_BINDING; these labels never become execution authority.

| From | To | Required actor/evidence; stored provenance |
|---|---|---|
| No task | OPEN | User task request validated by URI; TASK_OPENED / USER_PROVIDED and initial TASK_STATE / URI_RECORDED linked to its origin trace |
| OPEN | PAUSED | Explicit user pause (USER_PROVIDED), or URI-observed durable interruption checkpoint (URI_RECORDED) |
| OPEN | WAITING_USER | URI actually emitted a clarification/required-input request, trace-linked (URI_RECORDED) |
| WAITING_USER | PAUSED | Explicit user pause or URI interruption checkpoint, same evidence rule as OPEN |
| WAITING_USER or PAUSED | OPEN | Explicit user resume/input accepted by URI, with a runtime resume trace (URI_RECORDED); loading storage alone is not a resume |
| OPEN, WAITING_USER or PAUSED | COMPLETED | Explicit user declaration (USER_PROVIDED, visibly user-asserted completion, not VERIFIED), or URI_RECORDED transition linked to a valid registered VERIFIER_RESULT / VERIFIED outcome covering the task's current references/acceptance evidence |
| OPEN, WAITING_USER or PAUSED | FAILED | URI-observed execution failure (URI_RECORDED, not a verifier success), registered verifier failure via a URI-recorded transition, or explicit user declaration (USER_PROVIDED) |
| OPEN, WAITING_USER or PAUSED | ABANDONED | Explicit user cancellation only (USER_PROVIDED) |
| Any existing state | Same state | Validated source binding, outcome or next-step checkpoint through URI_RECORDED, or user correction; no implicit reference replacement |
| COMPLETED, FAILED or ABANDONED | Any different state | Normal regression rejected. Only explicit USER_CORRECTION of an earlier incorrect state with reason and target head may replace it; redoing completed work normally opens a new task |
| Any | Any | MODEL_DERIVED / EXECUTION_OUTCOME cannot create TASK_STATE or make a state current; they may propose to URI |

Initial TASK_STATE must have no prior head and cite TASK_OPENED. Every later state must supersede exactly the current TASK_STATE head of the same task and user; the caller passes expected_head_record_id. Compare that head and validate under the per-user write lock immediately before append. A mismatched expected head returns CONFLICT without writing. Invalid transitions return INVALID_TRANSITION without changing current state. No last-timestamp override.

The per-user guard is a stable Memory-local lock file, not the current monthly partition: use locked_append on that guard once, then open/read/append the relevant partition(s) separately while it is held. Do not nest locked_append (its thread lock is not reentrant). All Memory writers, root-registration changes and correction pairs use this same guard. This serializes expected-head checks even across a month boundary and leaves user_storage.py unchanged.

Allowed (kind, provenance) and supersession matrix; any unlisted pair/edge is rejected on write and load:

| Kind / admitted provenance | Authority | Permitted supersession |
|---|---|---|
| SOURCE_OBSERVED / SOURCE_OBSERVED | AUTHORITATIVE_SOURCE for the observed pointer; freshness separate | None; latest **validated** observation per source_id is current metadata by log order, not a task head |
| TASK_OPENED / USER_PROVIDED | USER_ASSERTED | None; one validated opening per task |
| TASK_STATE / URI_RECORDED, USER_PROVIDED, USER_CORRECTION | RUNTIME_RECORDED or USER_ASSERTED respectively | Previous same-task TASK_STATE head only, governed by the transition table |
| OUTCOME / EXECUTION_OUTCOME | CLAIMED_OUTCOME | None; each attempt is a new claim and cannot hide a verifier verdict |
| OUTCOME / VERIFIER_RESULT | VERIFIED_OUTCOME or VERIFIER_ATTESTED | Claimed OUTCOME it assesses; a prior verifier verdict only for the same assessed attempt/evidence chain through the URI verifier entry point (§17.6) |
| DERIVATIVE / MODEL_DERIVED | DERIVED_NON_AUTHORITATIVE | None; versions remain historical; current usability is derived from input/ref lineage and S11 version |
| CORRECTION / USER_CORRECTION | USER_ASSERTED | Earlier compatible CORRECTION for the same task/ref or same target, or correction target as specified in §17.11; never a verifier verdict or source observation |
| TOMBSTONE / USER_PROVIDED | USER_ASSERTED hide instruction, no change to target authority | None; hide-only semantics of §7.4 remain |

MODEL_DERIVED next_step text is only a separately labelled subfield of a URI-created checkpoint and cannot set status/references/last_outcome. Supersession targets must exist earlier in canonical partition/log order, be valid, same-user and same-task where applicable, have compatible kind/ref/attempt and be current where required. Forward references, cycles, cross-user/task replacements and forged authority are rejected. Loader re-derives authority, validates evidence/transition/supersession, and quarantines mismatches; a fork is CONFLICT, never auto-merged. Restart reconstructs the validated head exactly; no automatic completion/resume. This is minimal history/resume state, with no scheduler, executable workflow, dependencies or automatic work dispatch.

### 17.3 F-3 — rediscovery, freshness and degraded identity

**Interpretation:** old content at a stable path is stale evidence, but the edited live file at that path is still a source. The draft candidate exclusion conflated these.

The identity remains root_id plus canonical relpath (§17.7); SourceRef gains explicit identity_status = HASH_VERIFIED, HASH_UNAVAILABLE_SIZE_CAP, HASH_UNAVAILABLE_POLICY, SOURCE_MISSING or UNSAFE_IDENTITY. content_sha256 is null only for an explicitly degraded/missing status. SOURCE_CHANGED is a comparison to an item's recorded hash, not a blanket exclusion. Freshness of **each** historical reference/outcome/derivative is assessed against the hash it recorded, never merely against the latest SOURCE_OBSERVED.

Retrieval order: discover authorized live locators from session/task/history; refresh those locators from the registry **before** eligibility exclusion; fingerprint live sources if possible; then evaluate historical item freshness. If no live eligible candidate survives, run registry lexical discovery and repeat refresh. Exact-name requests run the complete collision lookup regardless of tier (§17.1).

| Observation | Candidate and history behaviour |
|---|---|
| Same canonical source exists, hash changed | Fresh SourceRef remains a usable discovery candidate subject to S1/clarification. Historical ref/outcome claims at the old hash are STALE_SOURCE; derivatives are DERIVATIVE_STALE. Do not silently update their stored hashes or represent the old outcome as current |
| Source proved missing / root removed | SOURCE_MISSING; excluded as live candidate, preserved in stale/history context |
| Temporarily inaccessible source/root | Unavailable, excluded from live binding; exact-name completeness fails closed rather than declaring it missing |
| File > configured hash cap (default 64 MiB) | HASH_UNAVAILABLE_SIZE_CAP, explicit package/telemetry reason and UNKNOWN freshness; compare recorded size_bytes/mtime_ns only to detect change, never to prove unchanged |
| Offline/recall-on-access or hashing forbidden by policy | HASH_UNAVAILABLE_POLICY; no automatic hydration, UNKNOWN freshness |
| Identity/containment cannot be verified or changes during fingerprint | UNSAFE_IDENTITY; no candidate projection/use |

For degraded hash identity, a locator may be displayed to ask for clarification and an explicitly approved reversible read/open of the live path may proceed as visibly degraded/TENTATIVE, after containment and metadata recheck. **No exact-title or attachment certainty projection** of that source; no consequential execution/copy-in/write-back based on that identity until a hash is obtained under an explicitly permitted cap/policy. No VERIFIED outcome/current derivative is derived from size/mtime alone. If frozen S1 could confer certainty, withhold projection and clarify outside that query (§17.1). Unknown old hashes never compare equal by virtue of both being null.

### 17.4 F-4 — deterministic attachment evidence and per-reference scope

**Interpretation:** S4 counts all current-turn attachments, not only attachments surviving a type filter, and its attachment anchor is turn-scoped. Applying that anchor to both slots in F-B needs a stricter M36 guard.

The controlling rule is: current_attachment_id may be emitted only when **the entire turn contains exactly one current-turn attachment**, its authorization/live hash identity is verified, and no anchor/explicit ID/title conflicts exist. For a single-reference turn, this follows the S4-qualified count rule. For a multiple-reference turn, add a conservative per-slot guard: the raw user-authored reference span must contain a deterministic explicit type word matching the attachment's extension-derived class. No such word, ambiguous class, different class, or missing raw span means no attachment anchor for that slot. If multiple slots qualify for the same attachment while the user requests distinct files, suppress anchors and clarify. This narrowing is independently qualified in Q-A2-4; it is not a claim that frozen S4 already tested M36 multi-slot behaviour.

Closed M36 type map: .xlsx/.xls/.xlsm/.csv/.ods → spreadsheet; .py → script; .docx/.doc/.pdf/.md/.txt/.odt → document; other extensions → unknown. Explicit span words: spreadsheet/workbook → spreadsheet; script → script; document → document. Casefold whole words only. More than one class in a span is ambiguous. Vocabulary expansion requires later qualification.

| Type source | M36 authority/use |
|---|---|
| Filename extension, read from the authorized canonical filename | Deterministic candidate class for the guard; not a claim about internal format validity |
| MIME metadata from a URI-controlled attachment ingestion path | Independent consistency check only, with recorded provenance; matching MIME cannot turn multiple attachments into one |
| Deterministic URI inspection, if actually available | Consistency evidence; no inspection module is added here. Unknown result supplies no positive anchor |
| Explicit user assertion | User clue for narrowing/clarification; cannot override conflicting extension/MIME/inspection silently |
| Model/decoder type_hint | Untrusted proposal; never an anchor enabling fact, never a completeness scope/filter; derive trusted type words again from the raw span |

Known disagreement between extension, trusted MIME or deterministic inspection suppresses the anchor and triggers clarification. Missing extension/unknown class suppresses the multi-slot anchor; misleading or missing type hints never manufacture a deterministic match. is_attachment and current-turn membership must come from the URI-owned attachment manifest, not model flags. No frozen S4 or S1 file is changed.

### 17.5 F-5 — deterministic task-relative cross-session retrieval

**Interpretation:** "spreadsheet from yesterday's task" has no necessary filename token overlap. Resolve structured task/time predicates before source lexical filtering.

Use existing index.py/retrieval.py, rebuilt from validated log records, for task_id, exact user-provided objective_label/title tokens, optional explicit user labels (bounded; not inferred preferences), opened_at, last_state_at, last-used timestamp, current status, current ref_key → source_id links, source media class and typed outcome/output links. Only validated current task heads/current reference relationships supply a task's current files; historical corrected links remain available only on an explicit history query.

MemoryQuery adds a query-time now_utc, user timezone, optional structured task selector/status/source-class filters and raw user span/type-hint provenance. The model may propose these selectors; URI validates them against the raw request and the closed supported grammar. Unsupported/freeform temporal language returns clarification rather than invented dates or semantic search.

Supported temporal predicates: "today", "yesterday", "last week". "Yesterday" is the previous local calendar date at query time, [local midnight, next local midnight); today is the current such interval; last week is the previous ISO Monday–Sunday calendar week. Convert boundaries to UTC using the supplied valid IANA timezone, with daylight-saving boundaries respected. Missing/invalid timezone or unresolved date ambiguity requires clarification. Snapshot now/timezone for repeatability.

A "task from yesterday" qualifies when its validated TASK_OPENED timestamp lies in that interval; merely being touched yesterday does not silently select an older task. Requests expressly saying "last updated/used yesterday" instead filter the corresponding validated timestamp. For "spreadsheet from yesterday's task", discover all matching tasks, then current linked references and recorded output sources of class spreadsheet; deduplicate source IDs while retaining task lineage. One qualifying source is eligible subject to §17.1/§17.3. Multiple tasks or files are surfaced for task/file clarification; recency orders options but does not guess a task.

Durable tier-3 rule: after validated task/time/status/source-class filters, normalize word-final possessive 's/’s away (so "yesterday's" becomes "yesterday"), then derive substantive tokens by casefolded whole-word lexical tokenization. Exclude the closed stopword set (the, a, an, from, of, in, on, my, task, tasks, file, files, this, that, yesterday, today, last, week, resume, continue, paused) and the type words in §17.4. If substantive tokens remain, require lexical overlap with the explicit task labels for task discovery, and title/relpath stem for a non-task file search. If none remain, use structured class/time/task filters only. Do not require a file name to overlap the label of a task that already explicitly links it.

Query/index traversal is bounded. Apply filters before the projection budget. All remaining matches are deterministically ordered by tier, descending validated last-used time, then stable source_id (tasks by last_state_at then task_id). If a matching result tier exceeds the budget, whole-query BUDGET_EXCEEDED with no partial projection; user narrows date/label/root. Do not take top-N and imply completeness. At least 20 unrelated historical tasks must not prevent recall of the one in the selected window. No embeddings, learned preference/frequency weights or model ranking.

### 17.6 F-6 — URI-owned verifier admission and verdict authority

**Interpretation:** VERIFIER_RESULT plus an arbitrary verifier_id string is forgeable. Registration must establish trusted execution identity, not just a naming convention.

Within contracts.py/recorder.py (no new module), define a closed URI-owned verifier registration table populated only by trusted application bootstrap/code, never by Memory records, harness/model/user parameters, tools or a public registration API. Each entry has verifier_id, verifier_type, version and the allowed URI-controlled producer/callable. A namespace such as uri.verifier.* is descriptive only; matching it is insufficient.

Only the URI-owned invocation/receipt path may call the internal verifier writer using a process-local opaque registration capability unavailable to normal callers and non-serializable. Receipt fields are constructed from the trusted invocation: registry identity/type/version, invocation/trace ID, assessed_outcome_record_id, exact input/output hashes, acceptance-evidence reference/digest and nonempty evidence_ids. Caller-supplied verifier_id/provenance/capability claims are rejected, including a copied legitimate ID. This boundary protects against normal model/harness/user data callers, not arbitrary malicious Python already running inside URI's trusted process. Trusted-process compromise is outside the M36 threat boundary.

Source-root registration must reject overlap with URI's private Memory/attestation storage; it cannot expose that store as an authorized editable source or harness workspace. Registry/attestation mutations have no model, harness or user-data API.

Validate the registration capability and actual producer, receipt linkage, same user/task/attempt, trace syntax, verdict and exact assessed inputs/outputs before deriving authority. Persist URI-issued attestation evidence under the user-scoped store owned by the trusted recorder, outside every scanned/harness-writable root; normal caller APIs can neither write nor register attestations. A URI-issued opaque receipt ID resolves to the exact verdict/evidence digest in that protected attestation store. Persist/read-back the attestation before appending its outcome; an orphaned attestation grants no current outcome. Loader validates the receipt against the registry/version and exact attestation content, never trusts serialized authority or an ID alone. Unsupported verifier/version or absent/invalid/mismatched receipt is quarantined/non-authoritative and cannot produce VERIFIED. This receipt integrity lives in existing log/index paths; it does not implement a domain verifier. M36 does not claim integrity against arbitrary filesystem edits to URI's protected storage by an attacker outside the normal-caller boundary.

| Provenance admitted through its typed path | Allowed verification_status | Authority / supersession |
|---|---|---|
| EXECUTION_OUTCOME (harness, model, unverified execution claim) | CLAIMED_ONLY, FAILED (claimed failure) | CLAIMED_OUTCOME; cannot replace any verifier verdict |
| VERIFIER_RESULT (registered URI invocation only) | VERIFIED | VERIFIED_OUTCOME; linked assessment may supersede its claimed outcome |
| VERIFIER_RESULT (registered URI invocation only) | PARTIALLY_VERIFIED, FAILED, UNVERIFIABLE | VERIFIER_ATTESTED, visibly a verifier verdict rather than a claim; same protection as VERIFIED |
| USER_PROVIDED, USER_CORRECTION, URI_RECORDED, MODEL_DERIVED, SOURCE_OBSERVED on OUTCOME | None | Rejected; typed claim method maps any unverified success proposal to EXECUTION_OUTCOME / CLAIMED_ONLY |

Every verdict including negative/partial/unverifiable ones is protected from a later harness claim. A later attempt is distinct; it cannot silently remove the earlier verdict. Only a registered URI verifier may replace its verdict with another linked assessment of that same attempt, preserving history. A user can correct task intent or declare completion, but cannot self-issue VERIFIED or hide a verifier failure. M36 qualification uses a URI-owned deterministic test verifier against actual hashed temp-file evidence; no fake harness-run field or Office verifier is introduced.

### 17.7 F-7 — Windows traversal and canonical identity

**Interpretation:** on this machine Python 3.13.15 traverses junctions with os.walk(followlinks=False); Path.is_symlink() is false for them. Those checks alone cannot enforce root containment.

Use bounded, sorted os.scandir traversal. Reject a registered root that is itself a symlink/junction/reparse point; establish its real canonical path once. For every directory/file entry, inspect without following: is_symlink(), platform is_junction() (where available), and Windows FILE_ATTRIBUTE_REPARSE_POINT. Never descend or hash a symlink, junction, mount/reparse point; unknown/unreadable classification fails closed. The collision scan records excluded branches as incomplete under §17.1.

Resolve(strict=True) and normalize case using os.path.normcase on both root and each traversed directory/file, then perform a path-component is_relative_to containment check. Never use a string prefix (root2 is not inside root). Derive relpath from the resolved on-disk name before source_id generation. Reject absolute/UNC/device-prefixed or drive-qualified relative paths, "..", alternate-data-stream ":", trailing dot/space components and Windows reserved device names (including names with extensions); do not accept alternate spellings as independent identities.

Recheck canonical containment, reparse attributes and size/mtime before fingerprint and use. Hash from an opened handle whose identity/real path is checked against the authorized source, then check attributes/stat/identity again; concurrent replacement/reparse substitution or inability to establish safe handle identity fails closed. A pre-open Path.resolve check alone is insufficient for a race. These safety checks are in sources.py; no frozen helper changes. Offline/recall-on-data-access flags are not hydrated or hashed, and produce HASH_UNAVAILABLE_POLICY (§17.3).

Qualification requires ordinary folders, a real Windows junction to an outside folder (creation through native Windows tooling), containment escapes and path alias tricks. Where symlink creation is unavailable, record a skip with its exact reason, not a passing assertion; junction coverage cannot be replaced by a symlink-only test.

### 17.8 F-8 — recovery-safe append and truthful persistence

**Interpretation:** a successful append/fsync can concatenate a new JSON record onto an unterminated fragment and render both unreadable. Memory-local framing and read-back are mandatory.

Keep monthly JSONL and frozen locked_append. In log.py, while holding the stable per-user guard through that helper (§17.2), append to a separately opened binary partition stream:

1. Inspect the existing partition through a separate read handle (binary append streams are not readable), validate its final physical line and detect missing newline/malformed JSON. If it is nonempty and lacks a newline, append a separator newline **before** the new record. Even valid JSON without a terminating newline is first separated. Never truncate/overwrite original evidence.
2. Preserve corrupt fragments/earlier invalid lines as original bytes plus an audit quarantine copy identified by partition, byte offset and fragment hash; deduplicate quarantine on reload. A valid unterminated tail is recoverable by separation, not treated as a fresh unvalidated record.
3. Reload/revalidate the repaired tail under the guard before checking the new record's expected head and authority (a recovered prior valid record may change that head). Serialize one canonical JSON object and terminating newline, flush and fsync the partition before unlock. Recover separators are flushed with the record. If a new partition is created, require platform-supported durable creation semantics; if that guarantee cannot be established, surface failure/degradation rather than assert it.
4. Reopen/read the exact new record at the recorded boundary, validate its ID, schema, payload, authority/evidence and hash against the intended bytes. Set persisted=True only after this read-back succeeds. On write, flush, fsync or read/validation failure return persisted=False and a precise reason. An uncertain result is not a permission to blindly replay.

Startup/load streams partitions in canonical order and validates complete lines independently. Malformed/torn lines are detected, quarantined and surfaced as degraded with counts/opaque recovery IDs; later valid records are still parsed. A trailing incomplete record is never accepted as a current state. Recover next append by inserting the newline under lock; no database/compaction is introduced.

WriteResult adds record_ids and per-record persistence/recovery evidence. Retrying an uncertain write uses the same record ID and exact payload: if an identical validated record exists return its confirmed status; if bytes differ reject ID_CONFLICT. A correction pair uses §17.11; absence of its state record never reports logical success. Tests must exercise crash/fault injection at write/newline/flush and read-back failures, not merely a syscall exception.

### 17.9 F-9 — stable clarification snapshots and revalidation at use

**Interpretation:** recency is in frozen candidate_fingerprint; recorder writes during the two-reference F-B turn can invalidate a rendered choice if Memory re-queries and re-ranks it.

Create an immutable turn retrieval snapshot before the first S1 clarification is rendered. It records scope/receipt, SourceRefs/hashes, IDs, ordering, recency_rank, candidate fields, locators, query time/filters and the projected queries for each reference slot. Each clarification round retains the exact candidate scope/query/ID mapping that produced its question. No recorder update, other task activity, new retrieval or newly uploaded source may mutate these beneath an open round; reuse the snapshot as current_query when answering frozen S1.

Recency-only changes are applied on the next turn/snapshot, never within the current turn. A fresh round may narrow a prior snapshot through explicit user clues under S1; it may not silently reorder the surviving IDs. Material source content/identity, authorization or collision membership change invalidates the affected old round. The caller discards it and renders a new ambiguity round from a fresh snapshot; it never reuses an old clickable option number with new meaning.

Before final selection/binding, independently revalidate the chosen source and completeness receipt. If its hash/path/authorization changed, do not commit a task binding from the old snapshot; refresh and ask through a new round. Before any read/execution/copy-in, the consumer must call sources.verify_source(source_id, expected_sha, scope_receipt) and recheck safe identity/live hash. Reversible use of a changed source requires visible fresh/degraded confirmation under §17.3; consequential use is blocked until a fresh S1/user binding and hash exist. Hash changes after binding never inherit its old certainty. The helper is a live-identity check, not a Memory binding authority.

### 17.10 F-10 — paused-task discovery and restart authority

**Interpretation:** restoring a known task_id is not discovering a paused task, and persisted CONFIRMED is a historical fact rather than new-session execution authority.

Add index.open_tasks(user_id, status_filter?, time_window?, label_tokens?, source_class?) returning bounded summaries from validated current heads: task_id, objective_label/explicit labels, opened_at, last_state_at, status and linked source IDs/classes. Default states OPEN/WAITING_USER/PAUSED; "resume/continue the paused…" explicitly filters PAUSED. For an unqualified "resume", search unfinished states only; COMPLETED/FAILED/ABANDONED never outrank them or automatically reopen.

Use §17.5 deterministic exact IDs, whole-word explicit labels, local time window and linked source class. "Resume yesterday's spreadsheet task" filters unfinished tasks opened yesterday with a current spreadsheet link; "continue the paused budget task" filters PAUSED with explicit label token budget. The model cannot invent a label or choose between matches. One match is offered/restored following user intent; multiple matches require task clarification; zero matches returns NO_MATCH and asks for a task identifier/narrowing clue without selecting a completed task. Over-budget returns a narrowing request, not an implicit recency winner.

New-process Q-9 starts with no task_id or session working set, discovers through open_tasks, and reconstructs only its validated current head. Restored references, binding IDs/tiers and their timestamps remain labelled HISTORICAL_BINDING (separate from the copied BindingTier value). Reversible use can proceed visibly TENTATIVE after live source checks; consequential action requires fresh S1 rebinding or explicit user confirmation against a current snapshot/hash. A resume event creates PAUSED/WAITING_USER → OPEN under §17.2 after URI validates the user request; loading alone does not. History/pending next-step text is context, never an executable continuation command.

### 17.11 F-11 — append-only correction of current task references

**Interpretation:** a correction about A→B must change the validated current ref for T, not merely add a disconnected note while task(T) still returns A.

The typed user-correction call accepts task_id, ref_key, expected_head_record_id and URI-validated user-input provenance/trace. B must be resolved through a fresh S1 binding/user clarification and live identity checks; the correction does not grant binding authority itself. Reject an arbitrary/model replacement, cross-task target, missing ref_key or stale head without changing the current view.

For a status-only correction of an earlier incorrect task state (§17.2), the same paired protocol targets the prior TASK_STATE record_id and stores the explicit reason in CORRECTION.note; source/binding replacement fields are absent, references are copied unchanged, and only the corrected status changes. This exception does not let a source correction change status without a separate explicit user instruction.

Within one serialized recorder call, prepare two immutable records with a shared correction operation ID:

1. CORRECTION / USER_CORRECTION targets {task_id, ref_key, prior_task_state_record_id}; records wrong_source_id=A, right_source_id=B, old/new hashes and new binding evidence. It supersedes the prior correction for the same slot if present, preserving its full chain; the first correction has no prior correction to supersede.
2. TASK_STATE / USER_CORRECTION supersedes exactly the prior TASK_STATE head and cites correction_record_id. Copy unchanged task fields/status and other slots, replacing only that slot with B's validated reference. Status correction, if requested, follows the explicit §17.2 exception.

Write correction then state under the same per-user lock, with §17.8 boundary/fsync/read-back guarantees and per-record persistence statuses. A correction is effective only when both valid records/links exist. If interrupted between them, retain the first as PENDING_CORRECTION, surface recovery/degradation and keep the old head; do not claim success or silently substitute B. Idempotent retry/recovery with the same operation/record IDs writes only the missing state, after checking the expected head; a changed head returns CONFLICT. Loader never promotes an orphaned correction or a state without its complete correction pair.

task(T), open_tasks and current-reference retrieval derive B from the validated head. A's historical relationship remains in the log/history, but is suppressed as the current source for T (including task-relative outcome/derivative retrieval). A may remain a live source for another task or an explicit independent filesystem query. Derivatives/outcomes whose input lineage depends on T's old A reference become SUPERSEDED_REFERENCE context for T; if bytes also changed, mark DERIVATIVE_STALE/STALE_SOURCE. They must never appear as fresh derivatives of B. Repeated A→B→C corrections retain every relationship while only C is current. S7 event links are supporting IDs; the correction payload/trace and state linkage are self-sufficient if an event is unavailable.

### 17.12 Mandatory A2 qualification mapping

These are **future implementation gates**, not tests claimed to have run in this text-only task. Extend the existing §11 battery/lane tests; every required finding has an objective case and pass condition.

| Finding / gate | Required cases | Objective pass |
|---|---|---|
| F-1 → Q-A2-1 / Q-3 | Two budget.xlsx files in different folders with only one in history; same basename across roots; stem collisions; filtered/inaccessible/stale/excluded second match; truncated scan/budget | Complete live collisions exposed; incomplete receipts yield no exact-title query; 0 wrong CONFIRMED |
| F-2 → Q-A2-2 / Q-9 | OPEN→PAUSED→OPEN; OPEN/PAUSED→COMPLETED by user or registered verifier evidence; each allowed edge; normal terminal regression; explicit state correction; MODEL_DERIVED task-state attempt; concurrent expected-head mismatch including month rollover; illegal load supersession/cycle/user/kind | Valid chains restore identical heads; invalid writes do not change state; invalid serialized authority quarantined; no model-current state |
| F-3 → Q-A2-3 / Q-5/Q-6/Q-10 | Spreadsheet edited between sessions; old derivative/outcome hashes; missing file; >64 MiB file unchanged metadata and changed metadata; null hash comparisons | Edited live path rediscovered with refreshed SourceRef; old claims stale; missing excluded; cap explicit/degraded, never CURRENT/VERIFIED by null or metadata |
| F-4 → Q-A2-4 / Q-3 | Two total attachments but only one type match; single attachment with script+spreadsheet slots; conflicting explicit span classes; absent/misleading model type hint; extension/MIME/inspection disagreement; missing extension | No unqualified anchor; only correct per-slot deterministic guard anchors; 0 wrong CONFIRMED; frozen S4 untouched |
| F-5 → Q-A2-5 / Q-5 | New process, yesterday spreadsheet query, no file-name overlap; 20+ unrelated tasks; boundary midnight/timezone cases; multiple tasks/files; overflow | All qualifying current sources returned when within bounds; ambiguity/narrowing when needed; no guessed date/task, no semantic retrieval |
| F-6 → Q-A2-6 / Q-7 | Harness self-verifies; model writes VERIFIED; unknown ID; copied registered ID without capability/receipt; user string impersonation; registered deterministic verifier with real temp-file evidence; verifier negative followed by harness success; reload tampered authority/receipt | All impersonations rejected; only URI registered evidence yields VERIFIED; negative/partial verdicts protected and labelled VERIFIER_ATTESTED |
| F-7 → Q-A2-7 / Q-2 | Ordinary folder; symlink when possible; real Windows junction; mount/reparse/unknown classification; outside-root escape; root-prefix sibling; trailing dot/space/device/ADS aliases; replacement during hash | 0 outside-root candidates/reads; rejected/unclassifiable paths fail closed; symlink skip explicit; junction assertion actually executes |
| F-8 → Q-A2-8 / log/Q-9 | Clean append; torn tail; truncated JSON; crash/fault between write/newline/flush; fsync/read-back failure; next append; corrupt earlier entry; repeated reload/retry | Every persisted=True record independently reloads/validates; later valid entry never disappears; original corruption retained, quarantine deduplicated; uncertain write not called persisted |
| F-9 → Q-A2-9 / Q-3/Q-DET | Two-reference F-B with recency update after question render and script binding before spreadsheet selection; source mutation/new collision while question open; edit after binding before use | Old clickable IDs/order/fingerprints stay stable for recency-only change; material changes trigger new round/block stale use; no wrong confirmed binding |
| F-10 → Q-A2-10 / Q-9 | New process without task_id: one paused match; multiple; none; completed newer than paused; budget and timezone narrowing; persisted CONFIRMED then source edit | Deterministic discovery/clarification; completed never silently resumed; exact state restored with historical binding label; consequential resume rebinds |
| F-11 → Q-A2-11 / Q-8 | A→B, B→C; restart; stale expected head; model correction; crash after first pair record; retry after uncertain read-back; A-dependent derivatives | Full append-only history; only valid complete pair changes current ref; corrected source/package is B then C; old derivatives never masquerade as B/C; partial pair visible/pending |

Corrected existing gates:

- Q-5: correct current live source(s) included in 100% of bounded, supported deterministic cases; edited-source rediscovery required. "Top recency 100%" is meaningful only for unambiguous cases; multi-match must clarify.
- Q-6: 100% of items carry authority and either a verified source hash or explicit degraded/missing identity reason; never a silently null "verified" hash.
- Q-9: restore after discovery without pre-known task_id, including pause/resume/correction chains and historical binding authority.
- Q-10: 0 missing/unsafe candidates; 100% of stale historical content labelled/suppressed from current grounding; edited live candidates are allowed with refreshed identity.
- The draft unit test "stale excluded" means stale **claims/derivatives**, not all changed live sources. The draft envelope test "only attachment anchor" must include the §17.4 deterministic guard and §17.1 completeness precondition.

Retain 0 wrong CONFIRMED binding (Q-3), 0 private leakage (Q-12), deterministic repeatability (Q-DET), process-restart resume, frozen integrity (Q-1/T-FROZEN) and Q-E2E real S1/S7/S11 recorder-driven evidence, not hand-built-only success fixtures. Negative fault fixtures are allowed for rejection/recovery tests. Qualification uses a real URI-owned deterministic test verifier and actual hashed temp-file artifacts; it does not add a future Office verifier or fake harness-run lineage. Full M33.3 code/test/fixture scope must also be compared to the frozen baseline, since hash anchors alone cover fewer than all slices.

### 17.13 Focused self-review and contradiction disposition

Self-review performed after drafting A2; this is an implementer's consistency review, **not independent PG-M1 acceptance**.

| Check | Result / controlling text |
|---|---|
| F-1 preserves S1 | Withhold incomplete exact-title queries upstream, include all collisions; §17.1 changes Memory assembly only |
| F-2 bounded semantics | Six existing statuses, validated head/evidence chain, no scheduler/workflow executor; §17.2 |
| F-3 rediscovery vs stale claims | Registry refresh precedes exclusion; per-item recorded hashes stay historical; §17.3 |
| F-6 arbitrary callers | Typed paths + bootstrap registration capability + linked receipt validation, no caller ID authority; §17.6 |
| F-7 junction containment | Reparse/junction checks on every entry and safe handle identity; §17.7 |
| F-8 readable persistence | Framed append, fsync and exact record read-back; §17.8 |
| F-9 stable IDs | Immutable turn/round queries, revalidation separate from recency re-ranking; §17.9 |
| F-10 discovery | Structured open_tasks and new-process unknown-task gate; §17.10 |
| F-11 correction history | Complete paired append with recovery and validated head; §17.11 |

Contradiction search disposition: G-10 corrected with original claim retained as history; §6 locked_append reuse qualified; §7.2–§7.6, §7.8–§7.10 and §11 carry explicit controlling-A2 notices; E-3 corrected; §15 "all satisfied" and anchor-only reasoning marked historical; A1 §16.1 verifier enforcement, §16.4 "E-6 already met", §16.5 stale exclusion, §16.6 readiness and §16.7 self-review superseded explicitly. No normative "latest state wins", generic verifier-id sufficiency, whole-source stale exclusion, one-type-matching-attachment anchor or raw-syscall persistence guarantee remains operative.

During self-review, the initial A2 drafting choices were tightened in place: incomplete exact-name evidence withholds projection (a flag cannot downgrade S1); copied registered verifier IDs require trusted invocation evidence; clarification snapshots distinguish recency changes from actual source/scope changes; correction-pair crashes leave a visible pending operation rather than falsely current B. These are safety semantics within the already chosen modules.

### 17.14 Boundary, limitations and handoff

Memory boundary unchanged: core plus thin URI adapter, per-user append-only local history, session-first deterministic retrieval, sources/derivatives distinct, history yes/learning no, Memory never binds, SHAREABLE fail-closed. No new module, semantic retrieval, domain verifier, general workflow engine or production integration.

harness_run_ref remains **DEFERRED**, with §16.2 reserved name/constraints unchanged: lineage only, non-authoritative, no retrieval/ranking/transcript/harness-session content, harmless loss, later additive schema with v1 reader. PG-M1 accepted this deferral; no empty/fake harness fixtures are added.

Edge-minimum sufficiency is **unverified**, not a defect: no Edge plan exists. E-5 is a future Edge-planning check. E-6 is a minimum Memory interface claim for typed claims/registered verifier results, derivatives and source hashes, **conditional** on future OD-3 workspace/output representation. Harness/Office end-to-end sufficiency and actual hashing/scan latency remain future evidence; this repair neither pre-designs Edge nor declares a demonstrator ready. Low findings F-12…F-18 remain advisory/unresolved unless addressed by a later explicitly scoped task; F-19's overstatements are corrected as history, without claiming an independent re-audit. All Q-A2 gates still require future implementation and real execution.

Governance records the audit verdict, F-1…F-11 repair mapping, A2 readiness and **PG-M2 blocked pending focused PG-M1 re-check**. PG-M1 is not fully accepted. Stop here; do not request PG-M2.

**Recommended focused PG-M1 re-check prompt:**

> You are the independent focused PG-M1 re-checker for URI M36 Amendment A2 in C:\Users\cheta\Development\Uri\_V1 on branch m35-uri-v1-parallel-architecture. Planning baseline e26d98c5b6827946c3e546663758a94bf1be7033; frozen M33.3 baseline 291c9daa48435200c4b56857d0e3bc630016e82a. Read M36_URI_MEMORY_MINIMUM_PLAN.md §17 and its in-place supersession notices, M36_STATE.md, URI_STATE.yaml, and the unchanged M36_PG_M1_INDEPENDENT_PREAUDIT_REPORT.md §4/§6. Independently inspect the cited frozen S1/S4/RAR/storage code as needed. Re-check only required F-1…F-11 / R-1…R-11 for presence, consistency, buildability and objective Q-A2-1…Q-A2-11 coverage. Confirm exact-name completeness cannot create false certainty; authorized task heads cannot be model/timestamp-selected; edited sources remain discoverable with stale claims separated; anchors use deterministic per-slot evidence; temporal and paused-task discovery are achievable without semantic retrieval; only registered URI invocations attest verifier results; junction/reparse escape fails closed; persisted=True requires parseable read-back; clarification IDs remain stable; and paired corrections retain history and recover safely. Verify no frozen/code/test changes, Memory boundary or accepted D-A/OD-2…OD-5/VG-1/LF-1 changes. Preserve harness_run_ref deferral and disclose Edge sufficiency as unverified. Do not implement, repeat the full PG-M1 audit, begin/request PG-M2, commit or push. Return each finding's determination, any concrete remaining bounded defect, and a focused verdict: PG_M1_ACCEPTED if all required repairs hold, PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS if concrete required defects remain, or PG_M1_REJECTED with reasons. Report actual checks and limitations; do not trust the repairer's self-review.

**Readiness:** M36_A2_READY_FOR_PG_M1_FOCUSED_RECHECK.

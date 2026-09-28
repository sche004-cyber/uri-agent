# M36 — URI-Memory Minimum (pre-Office demonstrator)

**Status:** `PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT`. Implementation is **not** authorized by this document.
**Date:** 2026-09-28.
**Author:** Claude Code (Opus 5.5), Architect / Pre-Auditor role. Not independent of this plan.
**Starting HEAD:** `291c9daa48435200c4b56857d0e3bc630016e82a` on `m35-uri-v1-parallel-architecture` (local = `origin`, 0/0).
**Component identity:** `URI-Memory` (`docs/governance/URI_STATE.yaml` → `reusable_components`, status `NOT_STARTED`). This plan does not change that status. Completing M36 would justify `EXPERIMENTAL` at most (see §12.4).
**Parent context:** M33.3 is `CLOSED_FROZEN` at `291c9da`. Its slice S9 (durable learned reference tie-break) was re-homed to URI-Memory/D4. S9 stays deferred under this plan (§3, decision D4-R1).
**State file:** `docs/plans/M36_STATE.md`.

Intended sequence (User, 2026-09-28): M33.3 CLOSED_FROZEN → **Memory minimum (this plan)** → Edge minimum → isolated URI Office vertical demonstrator → iterate from real evidence.

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
| G-10 | Memory-sourced candidates carry no deterministic anchors unless produced by a qualified producer | M36 passes only `current_attachment_id` through. A typed exact filename resolves at most TENTATIVE. Acceptable for reversible demo actions; anchor production deferred (§8) |
| G-11 | Harness strategy research is untracked | Cited as research input only; Execution Capsule is not adopted by M36. M36's context package is shaped so a future capsule `context` field can consume it |

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
| `uri_v1/user_storage.py` | **REUSE as-is** | Path scoping and locked append already qualified |
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

- The user registers **authorized roots** (local folders) explicitly. `root_id` = uuid4 hex. Roots live in a small per-user `memory/sources.json` (schema-versioned, written atomically with `os.replace`), not in the record log. Removing a root is allowed; records that cite it stay in the log and read `SOURCE_MISSING`. Nothing outside a registered root is ever scanned or referenced.
- `source_id` = `sha256(root_id + "\0" + normalized_relpath)[:32]`. Stable across sessions while the file stays at the same path. Rename or move produces a new `source_id`; the old one reads `SOURCE_MISSING` (move detection by hash is deferred).
- `scan(root_id, *, max_files, max_depth, extensions)` is bounded, deterministic (sorted), skips symlinks and hidden/system files, and never follows paths outside the root (resolved-path prefix check).
- `fingerprint(source_id)` reads the file and returns a fresh `SourceRef` (SHA-256, size, mtime). Hashing is lazy: done when a source becomes a candidate or is used in a task, not for the whole root. Cap per-file hashing at a configured size (default 64 MiB); above it `content_sha256 = None` and freshness `UNKNOWN`.
- A `SOURCE_OBSERVED` record is appended only when a source is actually used (bound, read, or produced), not for every scanned file. This avoids duplicating the file system into memory (principle 4).

### 7.4 Log and index (`log.py`, `index.py`)

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

Input `MemoryQuery(user_id, session_id, reference_expression, type_hint?, task_id?, turn_attachment_source_ids, session_working_set, max_candidates=16, max_bytes=16384)`. `session_working_set` is supplied by the caller (from `ActiveContext` or the demonstrator session); memory does not own session state.

1. **Session tier.** Candidates = current-turn attachments ∪ session working set. If the caller reports an in-session CONFIRMED binding for this `ref_key`, durable retrieval is **skipped** and telemetry records `SKIPPED_SESSION_CONFIRMED`.
2. **Task tier** (when `task_id` given): sources referenced by the task's current `TASK_STATE`, plus its outputs.
3. **Durable history tier** (D4-R1): sources appearing in current (non-superseded, non-tombstoned) `TASK_STATE`/`OUTCOME`/`DERIVATIVE` records, filtered deterministically by `type_hint` and case-folded token overlap between `reference_expression` and title/relpath stem. Ordered by last-used time. No learned weights, no counts, no model call.
4. **Registry tier**: bounded lexical filename match inside authorized roots when tiers 1–3 give no candidate.
5. Freshness check for every candidate (re-fingerprint only candidates, not the root). `STALE_SOURCE` / `SOURCE_MISSING` candidates are **excluded from the RAR candidate set** and listed in the context package's `stale` section, so a stale reference can prompt a visible question instead of silently binding.
6. Budget: stop at 16 candidates or 16,384 canonical bytes. If a tier would be cut mid-way, return `BUDGET_EXCEEDED` for the whole query (fail closed, S4 precedent). The caller then clarifies or narrows.

Order is tier order, then last-used time. `recency_rank` = position in that order (0 = most recent), which is the only way durable history influences RAR (factual recency, D4-R1).

### 7.6 Interaction with RAR / ARN / S1 (`uri_adapter/envelope.py`)

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

- `recorder.outcome(...)` accepts `verification_status=VERIFIED` only with provenance `VERIFIER_RESULT` and a `verifier_id`. Anything a model or harness claims is recorded as `CLAIMED_ONLY` with provenance `EXECUTION_OUTCOME`.
- Produced files inside an authorized root are fingerprinted and recorded as `SOURCE_OBSERVED` plus `DERIVATIVE` (with `derived_from` input hashes). Produced text (for example a summary) is written to the S11 ledger by the caller; memory records `DERIVATIVE` with the S11 `result_id`/`version`/SHA.
- `DERIVATIVE_STALE`: at read time, if any `derived_from` source hash differs from the live source hash, the derivative is marked stale in the package.

### 7.9 Privacy and authority

- Per-user storage through `user_scoped_path` (UUID-only). Cross-user reads are impossible by path construction; a test proves it.
- Only `Scope.PRIVATE` is writable. `SHAREABLE` exists so records are forward-compatible with a future shared-knowledge network (uuid record IDs, content hashes, provenance, append-only log are all replication-friendly). No network code, no server.
- No user-fact kind: user preferences stay in legacy `MemoryStore` until an INT event unifies them (avoids duplication, G-1).
- Memory has no authority over execution. It is never imported by any gate. A test asserts `uri_v1/memory` is not imported by `uri_v1/reference_clarification/` and does not import `uri_v1/turn/rar_deterministic.py`.
- A model can only reach memory writes through the recorder with provenance `MODEL_DERIVED`, which can never supersede a `USER_ASSERTED`, `AUTHORITATIVE_SOURCE`, or `VERIFIED_OUTCOME` record (recorder rejects it). Only `USER_CORRECTION` or `VERIFIER_RESULT` records may supersede those.

### 7.10 Failure and fallback

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
- **E-3** Stale and superseded context is visibly flagged and never enters the RAR candidate set.
- **E-4** Gates in §11 pass and the independent audit closes.
- **E-5** The Edge minimum milestone can consume `MemoryContextPackage` without a Memory contract change (checked at Edge-minimum planning).

## 15. Self-review against §0 (draft → repair → re-check)

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

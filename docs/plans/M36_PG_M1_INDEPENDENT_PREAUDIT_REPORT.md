# M36 PG-M1 — Independent Pre-Audit of the URI-Memory Minimum Plan

**Verdict: `PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS`** (11 required repairs, R-1 to R-11, listed in §6).
PG-M1 does not authorize implementation. PG-M2 (explicit User implementation authorization) is still required, and it should be given only after the required repairs are applied to the plan and re-checked (§6.3).

| Field | Value |
|---|---|
| Date | 2026-09-28 |
| Auditor | Claude Code (Opus 5.5), fresh session, PG-M1 independent pre-auditor role |
| Independence | Different **session** from the plan author. **Same model family** (the author is also Claude Code / Opus 5.5). The plan (§12 item 2, §16.5) requires "another model/session", so session independence is enough. I did not trust the plan's claims: every determination below is based on repository files I read or commands I ran in this session. The User may still want a cross-model second opinion. |
| Worktree / branch | `C:\Users\cheta\Development\Uri\_V1`, `m35-uri-v1-parallel-architecture` |
| HEAD audited | `e26d98c5b6827946c3e546663758a94bf1be7033` (plan drafted at `1f3ec48`; amendment A1 = plan §16) |
| Frozen baseline | M33.3 `CLOSED_FROZEN` at `291c9daa48435200c4b56857d0e3bc630016e82a` |
| Plan audited | `docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md` (590 lines) and `docs/plans/M36_STATE.md` |
| Files written | This report only. No plan, governance, state, frozen or code file was modified. Nothing was committed or pushed. Scratch experiments ran only in the session scratchpad and were cleaned up. |

"Plan L<n>" means line *n* of `docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md` at `e26d98c`. Other `path:line` references are to files at the same HEAD. `uri_core/` and `uri_v1/` always mean the `_V1` checkout.

---

## 1. Acceptance criteria (defined before the audit)

The plan passes PG-M1 only if every criterion holds, or if every failure can be fixed by a bounded plan-text repair that changes neither the Memory boundary nor any frozen artifact.

| ID | Criterion |
|---|---|
| AC-1 | **Evidence accuracy.** The recovered state (plan §2, §3) matches the repository. No claim that a later design step relies on is false. |
| AC-2 | **Minimality.** Every M36 component is needed by at least one requirement R1–R11 or by a safety invariant. Nothing is built "for later" except fail-closed reservations. |
| AC-3 | **Frozen integrity.** The design modifies no frozen M33.3 artifact, keeps the `uri_v1` → `uri_core` import ban, adds no S13/INT-*/`/ask` wiring, and the proposed tests would detect a violation. |
| AC-4 | **Authority.** No path lets a model or harness claim become `VERIFIED` without a `VERIFIER_RESULT` record. Authority cannot be set by the caller. Supersession rules have no contradiction and no bypass. |
| AC-5 | **Binding safety (PA-7, D3, D5).** Memory-supplied candidates cannot produce a `CONFIRMED` binding that the frozen S1/D5 rules would not produce on the complete authorized scope. No model output can create a certainty anchor. |
| AC-6 | **Freshness.** A missing file never becomes a RAR candidate. Stale memory content is never presented as current. The freshness rules still let the demonstrator re-find a file the user legitimately edited. |
| AC-7 | **Recovery.** A new process with no in-memory state can find a paused task and restore its status, references, last outcome and next step exactly. It must be clear what authority the restored bindings carry. |
| AC-8 | **Durability honesty.** A write reported as `persisted=True` is readable after restart. |
| AC-9 | **Scan safety.** Folder scanning cannot leave an authorized root through `..`, absolute paths, symlinks, **Windows junctions** or other reparse points. Path identity is canonical. |
| AC-10 | **Privacy.** Only per-user storage. No cross-user reads. The context package is task-scoped. Controls and "forget" semantics are specified. |
| AC-11 | **Forward sufficiency.** The minimum supports the Edge minimum (E-5), the Harness Execution minimum (E-6, §16.2) and flows F-A/F-B without a v1 contract break. |
| AC-12 | **No premature sharing.** `SHAREABLE` fails closed. No network or distributed code. |
| AC-13 | **`harness_run_ref`.** Whichever option is chosen, it is lineage only: never retrievable, ranked, projected or authoritative. |
| AC-14 | **Buildability (PA-10).** An implementer can build each lane without re-deciding semantics that affect safety. |

---

## 2. Evidence base (commands run and files read in this session)

Only completed, observed results are used as positive evidence.

| # | Check | Observed result |
|---|---|---|
| E1 | `git log --oneline -3` | `e26d98c`, `1f3ec48`, `291c9da`, as the brief states |
| E2 | `git diff --name-only 291c9da HEAD` | Only 5 files: `URI_STATE.yaml`, `M36_STATE.md`, M36 plan, Paperclip reconnaissance, viability gate. No code or frozen file changed since the frozen baseline. |
| E3 | `python scripts/m33_3_r_anchors.py` | `{'ok': True, 'changed': [], 's4_anchor_count': 8, 'frozen_lf_anchor_count': 24, ...}` |
| E4 | `python scripts/governance/uri_state_validator.py` | `VALID` |
| E5 | `pytest tests/test_m33_3_s1_governance_and_parity.py tests/test_m33_3_r_s11_result_versions.py tests/test_m33_3_r_s7_evaluation_events.py tests/test_m33_3_r_closing_audit.py` | `46 passed` (matches plan §1) |
| E6 | `pytest test_user_memory.py test_evidence_fact_integrity.py test_file_store.py test_experience_store.py test_graph_store_crud.py test_session_persistence.py test_fact_manager_evidence.py` (repository root) | `110 passed` (matches plan §1; the plan does not say these tests are at the repository root, not under `tests/`) |
| E7 | `git status --porcelain` | 157 untracked paths, of which 14 are in `uri_v1/turn/` (matches plan §1) |
| E8 | Scratch script: frozen RAR + S1 `classify_authority` on a memory-shaped query | Subset `{budget.xlsx, notes.md}`, expression `budget.xlsx` → `RESOLVED EXACT_TITLE … CERTAINTY`. Same query with a second `budget.xlsx` → `AMBIGUOUS … HEURISTIC`. Expression `budget` (stem only) → `RESOLVED EXACT_TITLE … HEURISTIC`. See F-1. |
| E9 | Scratch script: real `uri_v1.user_storage.locked_append` after a torn last line | A fully written and `fsync`ed record `r3` was parsed as part of one malformed line: `malformed: ['{"record_id":"r2","trunc{"record_id": "r3"}']`. See F-8. |
| E10 | Scratch experiment: Windows junction (`mklink /J`, no admin needed), Python 3.13.15 | `os.path.islink` = False; `Path.is_symlink()` = False; `os.path.isjunction` = True; `os.walk(root, followlinks=False)` **descended into the junction** and listed the outside file; `Path.rglob` also descended; `resolve().is_relative_to(root)` = False (caught). Also `root/"A.TXT"` and `root/"a.txt."` both resolve to the existing `a.txt`. See F-7. |

Code read in full or in the relevant part: `uri_v1/user_storage.py`; `uri_v1/results/version_ledger.py`; `uri_v1/evaluation/{events,store,trace_context}.py`; `uri_v1/reference_clarification/{facts,session_adjunct,store,authority,bundle,attribute_narrowing,fingerprints}.py` and `binding.py:25-140`; `uri_v1/turn/rar_contracts.py:75-160`; `uri_v1/turn/rar_deterministic.py:235-400, 640-760`; `scripts/m33_3_s4_source_to_candidate.py`; `scripts/m33_3_r_anchors.py`; `tests/test_m33_3_s1_governance_and_parity.py`; `uri_core/core/user_memory.py:311-380`; greps of `uri_core/core/{facts,fact_manager,state,graph_store,graph_engine,evidence_fact_integrity,file_store,experience_store,security_guards}.py`. Documents: the M36 plan and state; `URI_STATE.yaml` (M36 entry, D3, D4, D4-R1, D5, D-A, OD-2…OD-5, VG-1, LF-1, `URI-Memory` component); Paperclip reconnaissance §18–§21 and §24; the viability gate (its Memory mentions).

---

## 3. Determinations 1–12

### D1. Is the recovered Memory state (plan §2–§3) accurate?

**Mostly accurate. One load-bearing claim is false (F-1). Two minor labelling gaps.**

Confirmed against code:
- `uri_core/core/facts.py:7-12` has the six statuses the plan lists. `verify()` rejects model-like actors (`facts.py:48`, `:141-165`).
- `user_memory.py` `update()` overwrites the entry in place and `delete()` removes it (`user_memory.py:311-377`). The consent vocabulary is at `:63-65`, and `is_eligible_for_personalization` is at `:139`.
- `fact_history` is append-only, but only per session (`fact_manager.py:58-60`, `state.py:36`).
- `graph_store.py:52` has the `ACTIVE/HISTORICAL/SUPERSEDED` statuses. The `include_historical` opt-in is in `graph_engine.py:12`.
- `uri_v1/user_storage.py` re-implements `user_scoped_path` (UUID-only) and `locked_append`.
- The S11 ledger is append-only, content-addressed and write-once for blobs (`version_ledger.py:82-161`).
- S7 events hold ids and closed vocabulary only. They support durable ON/OFF, and unreadable settings fail closed (`store.py:39-49`).
- The S1 clarification store is process-local (`reference_clarification/store.py:1`, `:79-89`). `CandidateFact` grounds only title, type, owner and recency (`facts.py:9-24`).
- The S4 envelope matches the plan's description, including the 16-candidate / 16,384-byte fail-closed caps (`m33_3_s4_source_to_candidate.py:17-18`, `:97-116`).
- The §2.4 documents exist. `M28_STATE.md` says `Status: ACCEPTED`. A3 §14 is at line 428 and A3 §15 at line 466.

Inaccurate or incomplete:
- **G-10 (plan L146) is false.** It says "A typed exact filename resolves at most TENTATIVE". Frozen RAR Level 2 (`rar_deterministic.py:355-372`) resolves `EXACT_TITLE` when the expression equals a candidate title and that title is unique. Frozen S1 `classify_authority` (`authority.py:35-43`) grades that result `CERTAINTY` without any anchor. This is D5's "equivalent unique verbatim-title anchor". It was reproduced in E8. The plan's safety reasoning for L4 depends on this claim (see F-1).
- The plan cites `docs/plans/M35_URIV1_A0_PARALLEL_SKELETON_REPORT.md` (G-2, §2.4) without saying that the file is **untracked**. PA-1 asks for this kind of labelling. Low severity.
- The legacy test files cited in §1 are at the repository root, not under `tests/`. This is cosmetic.

### D2. Is the minimum boundary (plan §7–§8) genuinely minimal for R1–R11?

**Yes, with one small reservation.** Each module maps to a requirement:
- `sources.py` → R1 (first-time find, tier 4).
- `log`/`index` → R3, R7, R8.
- `recorder` → R6, R7.
- `retrieval` → R1–R3, R9.
- `context_package` → R10.
- `telemetry` → the VG-1 overhead attribution.
- `uri_adapter/envelope` → R1 projection.
- `uri_adapter/links` → R5, R7.

The deferrals in §8 are appropriate: semantic retrieval, anchors, move detection, legacy stores, sharing, compaction, graphify, capsule, S1 display and cross-agent adapter are all deferred. The `Scope.SHAREABLE` reservation is carried but is inert and fails closed, so it is acceptable. The reservation: minimality does not excuse the missing semantics found in F-2, F-3, F-5, F-10 and F-11. Those are gaps in the chosen components, not extra components.

### D3. Does the design preserve frozen M33.3 boundaries?

**Yes by design. The proposed enforcement is incomplete (F-12).**
- All new code is under `uri_v1/memory/`, plus new tests, scripts and fixtures (plan L394-395).
- The frozen import-ban test walks **every** `uri_v1/**/*.py` (`test_m33_3_s1_governance_and_parity.py:43-49`), so `uri_v1/memory` is covered automatically.
- The hash pins for `rar_deterministic.py`, `rar_contracts.py` and the Batch A battery (`:33-42`), and the 24 LF anchors plus 8 S4 anchors (E3), are untouched. E2 confirms no code changed after `291c9da`.
- PA-4 is respected: there is no `/ask`, agent-loop or `uri_core` wiring. Q-E2E drives S1, S7 and S11 only from a driver script.

The gap: PA-3 also forbids changes to S5, S7, S8, S10, S11 and S12 code. `scripts/m33_3_r_anchors.py:21-48` pins no S7 (`uri_v1/evaluation/*`) or S11 (`uri_v1/results/*`) file. T-FROZEN (plan L410) only "re-run[s] frozen hash assertions". An implementer could therefore change `version_ledger.py` or `evaluation/store.py` to suit Memory, and T-FROZEN would still pass. See F-12.

### D4. Are provenance, authority and verification semantics correct? Can a harness or model claim reach `VERIFIED` without a `VERIFIER_RESULT` record?

**By construction, no.** `VERIFIED_OUTCOME` requires `OUTCOME` with provenance `VERIFIER_RESULT` and status `VERIFIED` (plan L243). The recorder accepts `VERIFIED` only with `VERIFIER_RESULT` plus a `verifier_id` (L332). Authority is derived, not caller-set (L237).

**There are three weaknesses, so AC-4 is not yet met:**
1. **Provenance and `verifier_id` are caller-asserted and unconstrained.** Any code path, including a future harness adapter, can call `recorder.outcome(provenance=VERIFIER_RESULT, verifier_id="claude-code", …)`. D-A says a harness "does not decide that its own result is verified". The legacy code already had a guard for this, `_looks_like_model_actor` (`facts.py:48`), and the plan does not adapt it (F-6).
2. **The provenance × status matrix is incomplete.** A `VERIFIER_RESULT` with `FAILED`, `PARTIALLY_VERIFIED` or `UNVERIFIABLE` maps to `CLAIMED_OUTCOME` (L244). A verifier's negative verdict is therefore labelled "claimed". It is also unprotected, so a later harness `EXECUTION_OUTCOME` could supersede it and hide the failure from the current view (F-6).
3. **The supersession rule contradicts task progression** (F-2). This is an authority defect, not a verification defect, but it sits under the same AC-4.

### D5. Is cross-session recovery sufficient (R3, R8; Q-5, Q-9)?

**Not yet.**
- The log, index and `task(task_id)` design restores state by `task_id` (L287), and Q-9 tests a kill-and-reload.
- **Task discovery:** no read API finds a paused task in a new session. The only one named is `current(kind, …)`, and Q-9 lets the test know the `task_id` in advance (F-10).
- **Authority of restored bindings:** on resume, a restored `binding_tier=CONFIRMED` is a historical fact recorded at `recorded_at`. The plan does not say whether a consequential action may rely on it. If it may, Memory becomes a cross-session binding authority, which conflicts with PA-7 and D4-R1 ("Memory never binds") (F-10).
- **Q-5 as specified cannot pass by the specified algorithm.** Its example "the spreadsheet from yesterday's task" shares no token with a typical filename, and tier 3 filters by "type_hint and … token overlap" (L297). No temporal vocabulary is handled. Tier 3 also grows with history until it hits `BUDGET_EXCEEDED` for the whole query (L300) (F-5).

### D6. Can a stale or missing file silently become a RAR candidate (§7.5 step 5; Q-10)?

**Missing files: no. Changed files: the rule over-excludes. Very large files: silently admitted. There is also an unaddressed time-of-check/time-of-use gap.**
- `SOURCE_MISSING` is excluded and listed (L299). This is correct.
- **Over-exclusion.** `STALE_SOURCE` is excluded from the candidate set as well (L299). The plan never defines the baseline hash for "stale": the latest `SOURCE_OBSERVED`, or the hash in the task's `TASK_STATE` reference. Tier 4 runs only when tiers 1–3 return nothing *before* the freshness filter (L298-299). So a file the user edited after its last use is removed and cannot be re-found in that query. Office files change between sessions all the time. This breaks R3/R8 for F-A and F-B, and it conflicts with Q-5 whenever a history file has been edited. Binding safety does not need this exclusion: a binding to the *current* file with a fresh hash is correct. Staleness should apply to the *memory content* about the old bytes (derivatives, outcomes, reference hashes) (F-3).
- **Silent admission of `UNKNOWN`.** Files above the 64 MiB hash cap get freshness `UNKNOWN` (L275). Step 5 excludes only `STALE_SOURCE` and `SOURCE_MISSING`, so a changed large file is admitted with no signal (F-3).
- **Time-of-check/time-of-use gap.** S1's freshness check compares `candidate_fingerprint`, which is built from RARCandidate fields only and contains no content hash (`fingerprints.py:17-20`). A file edited between retrieval and read would go unnoticed unless the consumer checks the bound hash when it uses the file. The plan does not require that check (F-9).

### D7. Are corrections and supersession safe, including `MODEL_DERIVED` limits (§7.4, §7.9; Q-8)?

**Not yet safe or complete.**
- The plan says only `USER_CORRECTION` or `VERIFIER_RESULT` may supersede `USER_ASSERTED`, `AUTHORITATIVE_SOURCE` or `VERIFIED_OUTCOME` (L342). Read literally, a routine `TASK_STATE` update with provenance `USER_PROVIDED` (authority `USER_ASSERTED`) cannot supersede the previous `TASK_STATE`, and a fresh `SOURCE_OBSERVED` cannot supersede the old observation of the same file. So task status cannot progress (OPEN → PAUSED → COMPLETED).
- The index then selects the "latest `TASK_STATE` by `recorded_at`" (L287), whether or not the new record supersedes anything. So an implementer who avoids the deadlock with "latest wins" also lets a **non-superseding `MODEL_DERIVED` `TASK_STATE` become current**. The `MODEL_DERIVED` limit is enforced only on the `supersedes` field, so this bypasses it.
- "Two non-superseded states with the same parent" (L287) uses a "parent" that no schema defines.
- The Provenance enum has no value for records that URI writes deterministically, such as a `TASK_STATE` after an S1 binding. Such records are forced into `USER_PROVIDED` (overclaim) or `MODEL_DERIVED` (underclaim).
- The plan does not specify that `supersedes` targets must already exist, must precede the new record in log order, must belong to the same user and must have a compatible kind. Without that, cycles and cross-task supersession are not excluded. The plan also does not say that the loader re-derives authority from `(kind, provenance)` and rejects illegal supersession on read.
- How a `CORRECTION` targeting `{task_id, ref_key}` changes the task's current reference is undefined. Q-8 expects "package shows corrected reference", but `task()` returns the latest `TASK_STATE`, which still names the wrong source (F-11).

See F-2 and F-11.

### D8. Is authorized-folder scanning bounded and safe (Windows symlinks, junctions, normalization)?

**The scan is bounded (`max_files`, `max_depth`, `extensions`). The traversal rule as written is unsafe on this machine's Python.**
- E10 observed that on Python 3.13.15 a junction is **not** a symlink to `islink` or `is_symlink`, and that `os.walk(..., followlinks=False)` and `rglob` both descend into it.
- So "skips symlinks" (L274), implemented in the obvious way, traverses junctions. A per-file `resolve().is_relative_to(root)` check does catch the escape (E10). But the plan says "resolved-path prefix check", and a string-prefix check has the classic `C:\root` vs `C:\root2` hole.
- Path identity is undefined. On NTFS, `A.TXT` and `a.txt.` open the same file (E10), so `source_id = sha256(root_id, normalized_relpath)` (L273) can give two ids for one file unless the relpath comes from the resolved on-disk name.
- The plan does not mention alternate data streams (`name:stream`), reserved device names, `\\?\` and UNC forms, or cloud placeholders. Hashing a OneDrive online-only file triggers a download.
- The plan tests junctions (L414), which is good, but the design text must say how they are excluded (F-7).

### D9. Are privacy boundaries sufficient (§7.9; Q-12)?

**The core is sound, with specification gaps.**
- Per-user UUID paths come from `user_scoped_path` (`user_storage.py:27-30`).
- The package is task-scoped (L328), and there is no user-fact kind.
- Telemetry holds ids and enums only (L358).
- `SHAREABLE` fails closed.

Gaps:
1. The **default** of the Memory durable switch is not stated (S7 defaults ON, `store.py:43`). The plan does not say whether the S7 "durable learning" OFF switch also stops Memory history, or how unreadable settings behave.
2. `TOMBSTONE` "forget" hides data but never erases it. Physical removal exists only as a whole-user `reset` (L289). This is weaker than the S7 precedent, which has selective physical `delete_event` (`store.py:107-124`). It is acceptable for a minimum only if the product surface tells the user that data is hidden, not erased (F-13).

Candidate titles from other tasks do reach the same user's clarification. That is intended by R3 and is not a leak.

### D10. Is the minimum sufficient for the Edge minimum (E-5), the Harness Execution minimum (E-6, §16.2) and the Office demonstrator (§5, §14)?

- **E-5: cannot be verified** because no Edge-minimum plan exists. This is disclosed and does not affect the verdict. `MemoryContextPackage` has no `schema_version` (L316-326), which makes later additive evolution harder to detect (F-14, low).
- **E-6: met, conditionally.** Under the OD-3 default (`COPY_IN_COPY_OUT`), harness outputs sit in a scratch workspace that is neither an authorized root nor an S11 result. They become representable only if the future harness milestone stores them as S11 blobs (S11 accepts arbitrary bytes, `version_ledger.py:134-144`) or registers a temporary root. §16.1 leaves this open, which is acceptable. But "E-6 is already met" (L551) holds only under that condition. The verifier-identity gap (F-6) also bears on E-6.
- **Office demonstrator: not yet sufficient.** F-1 (a wrong `CONFIRMED` on a typed filename), F-3 (edited files drop out), F-4 (the attachment anchor in the two-reference F-B turn), F-5 (Q-5 temporal recall), F-9 (clarification rounds broken by recency re-ranking) and F-10 (resume discovery) all affect F-A or F-B directly.

### D11. Does the plan avoid premature shared or distributed memory?

**Yes.** `SHAREABLE` writes raise (L230, L339, L412). There is no network code, and T-BOUNDARY forbids `socket`, `requests`, `httpx` and model SDKs (L409). §8 defers sharing, sync and federation. The forward-compatible choices (uuid ids, hashes, append-only log) add no distributed mechanism.

### D12. `harness_run_ref`: deferral with reserved constraints, or the in-M36 optional field?

**Deferral (plan §16.2) is accepted. The in-M36 fallback is not required.** Reasons, checked against the repository:
1. `uri_v1/execution/` holds only an untracked `__init__.py` (observed). A field with no real target could be exercised only by fixture records, which Q-E2E forbids.
2. Every harness fact Memory needs is already representable: claim, verifier result, input and output hashes, S11 links and `trace_id`.
3. The schema-version upgrade path does not break v1. v1 rejects unknown keys (L260). Unknown versions are quarantined, not misread (L283). v2 must ship a v1 reader (L454).

The reserved constraints are correct lineage semantics: never retrieved, ranked, projected or packaged beyond an opaque link; never authoritative; loss-tolerant; no transcripts or session ids (L524-531). This matches Paperclip §18 and §20 invariant (iv). One advisory note: Paperclip §20's `HarnessRunRecord.verification{verifier_id,status}` must not become a second source of `VERIFIED`. The future harness plan must make the Memory `VERIFIER_RESULT` record the only verification authority. This is not an M36 repair.

---

## 4. Findings (ranked by severity)

### High

**F-1: A typed exact filename can produce a wrong `CONFIRMED` binding through the bounded memory candidate subset. G-10 is factually false.**
- *Evidence:* `rar_deterministic.py:355-372` (Level 2); `authority.py:35-43` (a unique verbatim title → `CERTAINTY` with no anchor); D5 in `URI_STATE.yaml` ("…or an equivalent unique verbatim-title anchor"); E8 reproduction.
- *Scenario:* `root/2025/budget.xlsx` was used last month and `root/2026/budget.xlsx` was created this week. The user types "budget.xlsx". Tier 3 returns the 2025 file, and tier 4 is skipped because tiers 1–3 are non-empty (L298). RAR resolves `EXACT_TITLE`, S1 grades it `CERTAINTY`, and the result is `CONFIRMED` to the 2025 file with no confirmation, even for consequential actions. Uniqueness was judged only over Memory's subset, not over the authorized scope.
- *Effect:* violates AC-5 and threatens Q-3 ("0 CONFIRMED bindings to a wrong source"). The frozen code behaves as designed. The defect is in Memory's candidate assembly.

**F-2: The supersession rule contradicts task-state progression, and "latest `TASK_STATE` wins" is a `MODEL_DERIVED` bypass.**
- *Evidence:* plan L342 vs L287; the authority table L239-245; no provenance for URI-deterministic writes (L228).
- *Effect:* the implementer must choose between an R8 deadlock and an authority bypass. Supersession target validation, cycle exclusion and authority re-derivation on load are also unspecified. Fails AC-4 and AC-14.

**F-3: The `STALE_SOURCE` candidate exclusion is too broad, the freshness baseline is undefined, and `UNKNOWN` is silently admitted.**
- *Evidence:* plan L275, L298-299, L334, L352.
- *Effect:* files the user edited after last use cannot be re-found (the F-A/F-B resume case, and Q-5 vs Q-10). Large changed files are admitted with no signal. Fails AC-6 in both directions.

### Medium

**F-4: The attachment anchor rule differs from the S4-qualified rule, and the source of the type hint is unspecified.**
- *Evidence:* plan L307 ("exactly one current-turn attachment matches the type hint") vs S4 `m33_3_s4_source_to_candidate.py:135-138` ("exactly one turn attachment", turn-scoped). `target_type_hint` has no production producer in `uri_v1`. It is caller-supplied (grep: only RAR consumers and research scripts).
- *Effect:* with two or more attachments, the plan's rule emits a certainty anchor (`CURRENT_ATTACHMENT` → `CERTAINTY`, `authority.py:33`) in a configuration S4 never qualified. If the type hint comes from a model decoder, a model output gates a `CONFIRMED` binding, which D3 forbids. Under S4's plain rule instead, a one-attachment, two-reference F-B turn would anchor both references to the attachment. Either way the rule needs precise, qualified wording.

**F-5: The tier-3 filter cannot satisfy Q-5 as written, and history growth leads to whole-query `BUDGET_EXCEEDED`.**
- *Evidence:* plan L297, L300, L430.
- *Effect:* R3 is not demonstrably achievable. An ambiguous "and" in the filter (type hint AND token overlap?) leaves safety-relevant ranking to the implementer.

**F-6: Verifier identity is unconstrained, the provenance × status matrix is incomplete, and verifier-negative verdicts are labelled "claimed" and can be superseded by harness claims.**
- *Evidence:* plan L243-244, L332; legacy precedent `facts.py:48`, `:161-165`; D-A.

**F-7: The Windows traversal and path-identity rules are unsafe as written.**
- *Evidence:* E10; plan L273-275.

**F-8: A torn last line makes a later persisted record unreadable, so `persisted=True` can be false.**
- *Evidence:* `user_storage.py:35-46` (opens `ab`, appends at end, no separator check); E9 reproduction; plan L280-283 (the "failed write never reports success" test covers only the write that fails).

**F-9: Recency re-ranking inside a clarification round, and hash re-verification when a file is used.**
- *Evidence:* `candidate_fingerprint` includes `recency_rank` (`fingerprints.py:17-20`). `BindingService._fresh` rejects a candidate whose fingerprint changed (`binding.py:89-92`, `:117-118`). Memory `recency_rank` is positional and driven by last-used time (plan L302).
- *Scenario:* in a two-reference F-B turn, binding the script first triggers `recorder.task_state` (L310) and updates last-used. The caller re-queries Memory to build `current_query` for the spreadsheet answer. Ranks shift, and S1 rejects with "candidate stale or absent". Separately, nothing requires the consumer to check the bound `content_sha256` when it reads or executes the file.

**F-10: Resume lacks task discovery, and the authority of restored bindings is unspecified.**
- *Evidence:* plan L284-287 (read API), L310, L433 (Q-9).

**F-11: How `CORRECTION` affects `TASK_STATE` is undefined.**
- *Evidence:* plan L265, L287, L429. Fails AC-14.

### Low

**F-12: T-FROZEN does not detect changes to S5–S12 code.**
- *Evidence:* `scripts/m33_3_r_anchors.py:21-48` has no S7 or S11 entries. Plan L410.

**F-13: The Memory durable-switch default and its relation to the S7 durable-learning switch are unspecified, and "forget" means hide, not erase.**
- *Evidence:* `evaluation/store.py:39-49`, `:107-124`; plan L282, L289.

**F-14: `MemoryContextPackage` has no `schema_version`** (plan L316-326).

**F-15: The mapping from S1 `BindingState` (13 values, `rar_clarification_contract.py:30-43`) to Memory `BindingTier` is undefined.** States such as `REJECTED`, `EXPIRED` and `CHANGE_PENDING` must never be recorded as bound.

**F-16: `trace_id` validation conflicts with T-BOUNDARY.** Plan §6 L179 reuses `trace_context.require_trace_id`, but core modules may import only stdlib and `user_storage` (L409). The 32-hex rule needs a re-implementation in `contracts.py` with a lineage comment.

**F-17: Quarantine is re-copied on every load** (L283), so the quarantine file grows on each reload. It needs de-duplication by partition and line hash.

**F-18: Minor gaps.**
- Re-registering a removed root gives it a new `root_id`, which orphans all its history as `SOURCE_MISSING` (L272-273). This should be disclosed.
- `DERIVATIVE` does not flag that the S11 head moved after a user edit (`version_ledger.py:200-206`). The package may show an older version as current.
- The `s7_event_id` link can dangle after S7 `delete_event` or when S7 durable is OFF. `CORRECTION` must stay self-sufficient, which its payload already allows.
- The mapping from media class to `candidate_type` / type-hint vocabulary is unstated.

**F-19: The self-reviews overstate completeness.** §15 L476 says "PA-1 … PA-10 all satisfied". F-1 contradicts the PA-7 reasoning, F-2/F-11 contradict PA-10, and the untracked A0 citation is a PA-1 gap. §16.4 L551 says "E-6 is already met" without the OD-3 condition. §16.7 found no issue with G-10. These are the defects the self-reviews missed.

---

## 5. Unsupported assumptions in the plan

1. "A typed exact filename resolves at most TENTATIVE" (G-10). **Disproved** (E8).
2. "Skips symlinks … resolved-path prefix check" is enough on Windows. **Disproved as written** (E10).
3. "`locked_append` + `fsync`" makes `persisted=True` trustworthy. **Disproved** for torn-tail recovery (E9).
4. "A model can only reach memory writes through the recorder with provenance `MODEL_DERIVED`" (L342). This is an **unenforced caller obligation**: provenance is self-declared. It is acceptable only if restated as a caller contract with typed recorder methods and a test double that tries to misuse them.
5. "Session tier answers without durable read in ≥95%" (Q-4) and "correct source 100%" (Q-5) assume tier semantics that are not fully specified (F-5).
6. "E-6 already met" assumes an OD-3 output representation that the harness plan has not decided (D10).

---

## 6. Required bounded repairs (plan amendment A2, text only; no boundary change)

Each repair changes plan text and gates only. None adds a module, touches a frozen artifact, or widens M36's scope.

| ID | Fixes | Required change |
|---|---|---|
| **R-1** | F-1 | Correct G-10 (keep the original as history). Add **exact-name completeness** to §7.5: if the casefolded reference expression equals the title or stem of any assembled candidate, retrieval must add **every** file in all authorized roots with the same basename or stem before projection. If that lookup is truncated, unavailable or over budget, return `BUDGET_EXCEEDED` / `degraded` and never a partial set. Add Q-3 fixtures: the same basename in two folders with only one in history; the same basename across two roots; a truncated scan. Gate: 0 wrong `CONFIRMED`. |
| **R-2** | F-2 | (a) Define the task head as the head of a supersession chain. Every new `TASK_STATE` must supersede the current head (the caller passes the expected head id; a mismatch returns `CONFLICT` and is not written). "Latest by `recorded_at`" must not select a non-superseding record. (b) Add a provenance value for URI-deterministic records (for example `URI_RECORDED`) with its own authority, and give a closed **supersession matrix** (who may supersede whom, per kind), under which routine task progression is legal and `MODEL_DERIVED` can never set `status`, `references` or an outcome. Model text is allowed only as `next_step` with its own provenance. (c) State the observation rule: the latest `SOURCE_OBSERVED` per `source_id` is current, with no supersession needed. (d) Supersession targets must exist earlier in the log, belong to the same user and have a compatible kind. The loader re-derives authority from `(kind, provenance)` and quarantines mismatches and illegal supersessions. Add tests for each rule. |
| **R-3** | F-3 | Separate **candidate eligibility** from **content freshness**. `SOURCE_MISSING` is excluded. A file whose content changed at the same path is **admitted with its fresh `SourceRef`**, and every Memory item tied to its old hash (reference hashes, outcomes, derivatives) is labelled stale in the package. Define the baseline hash for each item. Run tier 4 after freshness filtering when it leaves the set empty. For `UNKNOWN` (above the hash cap), compare `size_bytes` and `mtime_ns` and treat any difference as changed. `UNKNOWN` is never `CURRENT` for derivative or outcome claims. Reword Q-10 as "0 missing sources in the candidate set; 100% of stale memory content labelled", and add a Q-5 case where the file was edited between sessions. |
| **R-4** | F-4 | Specify the anchor rule exactly. Emit `current_attachment_id` only when (i) the turn has exactly one current-turn attachment (the S4-qualified rule), **and** (ii) for a turn with more than one reference slot, the reference span contains a type word taken **deterministically** from the span text whose class equals the attachment's extension-derived class. A type hint from a model decoder never enables an anchor (D3). Any other configuration gets no anchor. Add Q-3 fixtures for two attachments, and for one attachment with two references (F-B). |
| **R-5** | F-5 | Define tier 3 precisely: if the expression has substantive tokens (not stopwords, type words or temporal words), require token overlap; otherwise apply the type filter only. Either add a closed, deterministic temporal vocabulary ("today", "yesterday", "last week") over `recorded_at` in the user's local timezone, or explicitly defer temporal words and rewrite the Q-5 example. Specify what happens when tier 3 exceeds the budget: either deterministic top-N by last-used with a `truncated` flag that disables R-1 completeness claims (so it fails closed), or whole-query failure. Justify the choice. Add a Q-5 fixture with at least 20 historical tasks. |
| **R-6** | F-6 | Keep a closed registry of URI-owned verifier ids (for example the `uri.verifier.<name>` pattern). The recorder rejects any other id and rejects model- or harness-looking ids (adapting `facts.py:48`, with a lineage comment). Add a full provenance × `verification_status` matrix: `EXECUTION_OUTCOME` may carry only `CLAIMED_ONLY` or a claimed failure. Every `VERIFIER_RESULT` verdict (including `FAILED`, `PARTIAL` and `UNVERIFIABLE`) gets a verifier authority that `EXECUTION_OUTCOME` cannot supersede. A `VERIFIER_RESULT` must cite the claimed outcome it assesses and include non-empty `evidence_ids`. Add a Q-7 negative test: a harness writes `VERIFIER_RESULT` with its own id and is rejected. |
| **R-7** | F-7 | Specify traversal with `os.scandir`. Never descend an entry that is `is_symlink()`, `is_junction()` or has `FILE_ATTRIBUTE_REPARSE_POINT` set. Check containment per file with `Path.resolve(strict=True).is_relative_to(resolved_root)` after `os.path.normcase`, never a string prefix, and re-check at `fingerprint()` time. Derive the relpath from the resolved on-disk name. Reject `:`, trailing dot or space, reserved device names, and `\\?\` / UNC relpaths. Do not hash files marked offline or recall-on-data-access; mark them `UNKNOWN`. Tests use real junctions (`mklink /J` needs no admin). Symlink tests skip with a stated reason, never a silent pass. |
| **R-8** | F-8 | Inside the lock and before writing, if the partition file is non-empty and does not end in `\n`, write `\n` first. Flush and `fsync` before releasing the lock. Add a test: torn tail → append → reload → the new record is intact and only the fragment is quarantined. |
| **R-9** | F-9 | Retrieval for one turn is a **turn-stable snapshot**: the envelope and query built at turn start are reused for every clarification round in that turn, and `recorder` writes in the current turn do not change that turn's `recency_rank`. Record `content_sha256` at binding. Require the consumer (the demonstrator and the future harness copy-in) to verify it when the file is read or executed, and provide a `verify_source(source_id, sha)` helper. Add an F-B fixture with two references, clarification and an interleaved recorder write. |
| **R-10** | F-10 | Add an `open_tasks(user_id)` read API (status `OPEN`/`WAITING_USER`/`PAUSED`, ordered by last update). Q-9 must start from a new process that does **not** know the `task_id`. State that restored `binding_tier` is historical. Before any consequential action on resume, the reference must be re-bound through S1 on a fresh query or confirmed by the user. Reversible actions may proceed as a visible `TENTATIVE` (consequence-aware binding rule). |
| **R-11** | F-11 | Define correction semantics: a `CORRECTION` targeting `{task_id, ref_key}` must be written together with a new `TASK_STATE` that supersedes the head with the corrected reference, in one recorder call that writes both records in order and reports `persisted` for both. Q-8 checks both records and the package. |

### 6.2 Recommended (low severity, not blocking)

- F-12: Add T-FROZEN-SCOPE: `git diff --name-only 291c9da..HEAD` may contain only `uri_v1/memory/**`, `tests/test_m36_*`, `scripts/m36_*`, `fixtures/m36_memory/**`, `docs/plans/M36_*` and the governance files at closure.
- F-13: State the Memory durable default and whether S7's durable OFF also governs Memory history. Unreadable settings fail closed. Surface "forget = hidden, not erased".
- F-14: Add `schema_version` to `MemoryContextPackage`.
- F-15: Give a closed map from S1 `BindingState` to `BindingTier`, and reject non-bound states.
- F-16: Re-implement trace-id validation in `contracts.py` with a lineage comment.
- F-17: De-duplicate quarantine copies.
- F-18: Disclose root re-registration orphaning. Flag a moved S11 head in `derivatives`. State the media-class vocabulary.
- F-19: When the plan is repaired, record the corrected self-review claims additively, keeping the originals.

### 6.3 Re-check protocol for the repairs

The repairs are plan-text changes. After the author applies them (as amendment A2, additive, keeping §0–§16 history), a focused re-check of R-1 to R-11 only (not a full PG-M1 re-run) should confirm each repair is present and consistent before PG-M2 is requested. If the author disputes a repair, the User decides. This matters most for R-3 (a design change in freshness semantics) and R-5 (temporal recall scope).

---

## 7. Self-review of this report against §1

First draft, then defects found and repaired:
1. The draft rated F-3 Medium. Re-checked: L298-299 excludes a changed file before tier 4 can run, and F-B write-back or user edits make that the normal case. **Repaired:** raised to High.
2. The draft stated F-1 from reading the code only. **Repaired:** reproduced with the frozen RAR and S1 functions (E8) before relying on it.
3. The draft assumed `os.walk(followlinks=False)` skips junctions. **Repaired:** tested (E10). It does not, on this machine's Python 3.13.15.
4. The draft called the torn-line risk theoretical. **Repaired:** reproduced with the real `locked_append` (E9).
5. The draft treated D4 as fully passed. **Repaired:** separated "`VERIFIED` requires a `VERIFIER_RESULT` record" (holds) from "a `VERIFIER_RESULT` record cannot be forged by a harness" (does not hold, F-6).
6. The draft claimed the plan's legacy test paths were wrong. **Repaired:** found them at the repository root and ran them (E6, 110 passed). Downgraded to cosmetic.
7. I checked whether any repair changes the Memory boundary, adds a module or touches a frozen file. None does, so the verdict is `ACCEPTED_WITH_BOUNDED_REPAIRS` rather than `REJECTED`. The architecture (`uri_v1/memory` core plus adapter, append-only log, session-first retrieval, Memory never binds, `SHAREABLE` fail-closed, `harness_run_ref` deferred) is sound.

Re-check: AC-1 (D1), AC-2 (D2), AC-3 (D3, F-12), AC-4 (D4, D7, F-2, F-6), AC-5 (F-1, F-4), AC-6 (F-3, F-9), AC-7 (F-10), AC-8 (F-8), AC-9 (F-7), AC-10 (D9, F-13), AC-11 (D10), AC-12 (D11), AC-13 (D12) and AC-14 (F-2, F-11) each have a determination and, where the criterion fails, a mapped repair.

---

## 8. Could not verify (and effect on the verdict)

| Item | What is missing | Effect |
|---|---|---|
| E-5 Edge consumption | No Edge-minimum plan exists | None on this verdict; the plan itself defers it to Edge planning |
| Symlink traversal | I tested junctions only; creating a symlink needs admin or Developer Mode | None: R-7 covers symlinks by rule and requires a test that skips with a stated reason |
| OneDrive / cloud placeholder hydration | Not tested on this machine | None: R-7 excludes such files from hashing by attribute |
| Real scan and hash latency | Not measured | None: Q-LAT is reported, not gated |
| Older prototype `E:\...\uri_prototype` | Not accessible (as the plan states) | None: the accessible legacy code covers the principles used |
| Untracked research (`docs/research/URI_HARNESS_STRATEGY/05_*`, `08_*`) | Existence confirmed; not read in full | None: the plan uses it as non-authoritative input only |
| Full `uri_core` memory modules | Read at the cited lines, not end to end | Low: the plan re-implements principles and imports none of them (import ban) |
| Cross-model independence | Auditor and author are the same model family | Disclosed; meets the plan's "model/session" rule through session independence |

---

## 9. Verdict

**`PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS`**

Required repairs: **R-1** (exact-name completeness; correct G-10), **R-2** (task supersession chain and matrix; provenance for URI-recorded records; supersession validation on load), **R-3** (separate candidate eligibility from content freshness; `UNKNOWN` handling), **R-4** (S4-qualified attachment anchor; only a deterministic type hint may enable it), **R-5** (tier-3 filter, temporal scope and budget behaviour), **R-6** (verifier registry; provenance × status matrix; protect verifier verdicts), **R-7** (Windows junction, reparse-point and path-identity rules), **R-8** (torn-tail-safe append), **R-9** (turn-stable retrieval snapshot; check the bound hash when the file is used), **R-10** (`open_tasks`; restored bindings are historical, re-bind before consequential actions), **R-11** (correction writes a superseding `TASK_STATE`).

`harness_run_ref`: **deferral accepted** as specified in plan §16.2. It is correctly designed as lineage, not retrievable Memory.

This verdict does not authorize implementation. PG-M2 (explicit User authorization) is still required, after the repairs are applied and re-checked (§6.3).

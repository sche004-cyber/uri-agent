# M35 URIv1 — A2.8K: Level-5 Evidence Sufficiency & Attachment Ordering — Diagnostic Qualification (PLAN)

**Status:** `PLAN_READY_FOR_USER_APPROVAL`

This plan is **not** auto-accepted. The User reserved approval explicitly. §8 lists four semantic decisions only the User can make, and the diagnostic battery cannot be frozen until they are answered.

- **Author:** Claude (Architect / Pre-Auditor)
- **Date:** 2026-09-24
- **Predecessor:** A2.8J (COMPLETE; closure commit `247265f7`, pushed). See `docs/plans/M35_URIV1_A2_8J_STATE.md` and `docs/plans/M35_URIV1_A2_8J_BOUNDED_REAUDIT.md`.

---

## 0. Central question

> Under exactly what evidence conditions should Level 5 be permitted to convert recency into a confident reference binding, and when should Level 5.5 attachment-ambiguity handling take precedence?

A2.8K is a **diagnostic qualification**. Its product is evidence about which deterministic rule answers the central question, or proof that none of the candidates does. It does not produce a production change. A Level-5 gate is one hypothesis among several and is not presumed to be the answer.

---

## 1. Evidence base (recovered from the repository during planning, not assumed)

### 1.1 How the baseline Level 5 and Level 5.5 behave

Source: `uri_v1/turn/rar_deterministic.py`, lines 564–741. These facts were verified by reading the code.

**Level 5 triggers.** Level 5 is entered when `recency_hint` or a span token matches one of `revised`, `previous`, `earlier`, `latest`, or `current`.

**How each hint picks a candidate.** Every rule works over the *current (possibly type-narrowed) pool*, using `recency_rank` values that were computed over the *whole supplied pool*:

| Hint | Candidates considered | Resolves when |
|---|---|---|
| `revised` | candidates with a `revised` tag or title token | exactly one exists |
| `previous` | `rank == 1` | exactly one exists |
| `earlier` | `rank > 0` | exactly one exists |
| `latest` / `current` | `rank == 0` | exactly one exists, and some rank > 0 is present |

**Evidence Level 5 never consults.**

- **Span substantive tokens.** Level 5 does not check that the span's own descriptive words agree with the chosen candidate.
- **Evidence that could restrict the ordering domain.** Ordering always runs over the full current pool.
- **What the rank clock measures.** Ranks come from `created_at` in the harness, not from discussion order or attachment order.
- **Attachment semantics.** Level 5 ignores attachment wording entirely.

**Precedence.** Level 5 runs before Level 5.5. An explicit attachment reference that also carries a recency hint is therefore settled by recency and never reaches Level 5.5's ambiguity handling.

**What `is_attachment` means in the harness.** The harness sets `RARCandidate.is_attachment` to "is a file-reference object" (`build_candidate`: `representation == "file_reference_shape"`). It does **not** mean "attached in the current turn". The corpus carries `conversation_context.turn_attachments`, but no RAR contract field transports it. The only turn-level field is the singular `RARDeterministicAnchor.current_attachment_id` at Level 1.

**Production exposure today.** At the one real call site `recency_rank` is always 0 (A2.8I). So the ordinal branches are masked in production. What remains live is the `revised` branch and `latest/current` returning AMBIGUOUS with `INSUFFICIENT_METADATA`. A2.8K therefore qualifies Level 5 *ahead of* any recency wiring, which remains out of scope.

### 1.2 Failure-class inventory

Surface: baseline RAR, oracle span, oracle hint, oracle `created_at` ranks. This is the Probe A condition applied to every reference at C1/C2, 168 rows.

Overall: 73 correct, 47 missed, 38 correct abstentions, 10 incorrect confident bindings (ICBs).

**33 rows are decided at Level 5 or 5.5.** Of those, 14 are correct, 9 are ICBs, 2 are missed resolutions, and 8 are correct abstentions. 9 of the 10 ICBs come from Level 5. The remaining ICB is NB-H-06 at Level 4a/4b, which is out of scope here.

The 9 Level-5 ICBs fall into four causal classes:

| Class | Mechanism | Rows (baseline ICB) | Corpus author's rationale (verbatim intent) |
|---|---|---|---|
| **A. Attachment-set ambiguity overridden by recency** | An explicit attachment reference with ≥2 turn attachments. Level 5 `latest` picks rank 0 from a `created_at` clock that is 1 s apart (C-04), or that reflects the original upload rather than this turn (C-05). Level 5.5 would have returned AMBIGUOUS. | NB-C-04 C1/C2, NB-C-05 C1/C2 | "Binding to either single photo is a wrong confident binding"; "Recency among the attachments must not be used to pick one" |
| **B. Absent entity** | The span names something that is not in the pool (`contract`/`Jonas`, `template`). Level 5 binds whatever is "earlier". | NB-J-02 C1, NB-J-04 C1 | Referent is missing; expected UNKNOWN |
| **C. Ordering domain ignores the span's constraint** | "the latest board minutes": the newest *pool* item is an October agenda, not minutes. The ordering should run over the minutes only. | NB-D-01 C2 | "A recency rule that ignores the 'minutes' constraint picks the wrong object" |
| **D. Relative anchor / wrong clock** | "the one before that" / "the one I uploaded before it" is relative to an antecedent (last-discussed item, or another reference). Level 5 uses the global `created_at` rank instead. | NB-D-02 C2, NB-L-09:r2 C2 | "In C2 the September agenda sits between the two minutes files in time"; "Binding the budget as the 'previous roster' is the failure to watch" |

Related non-ICB evidence:

- **NB-C-06** ("The first attachment"): Level 5.5 returns AMBIGUOUS, which is correct.
- **NB-C-07** ("first thing this morning"): two uploads 50 s apart. Level 5 returns AMBIGUOUS, which is correct. The author notes that strict-earliest binding would be "acceptable, but a human would likely ask".
- **Correct Level-5 bindings at risk from any gate (14 rows):** NB-C-02 C2 ("this"), NB-D-01 C1, NB-D-02 C1, NB-D-03 C1, NB-D-04 C1, NB-D-05 C1, NB-D-06 C1 and C2, NB-D-07 C1, NB-H-01 C2, NB-L-03 C2, NB-L-04 C1 and C2, NB-L-06 C1.
  - Several are correct only by coincidence of pool composition. Example: NB-D-02 C1 is correct only because nothing sits between the two minutes files in C1.

AUDITOR INTERPRETATION: the shared root is not simply "zero substantive evidence". Level 5 treats *one global ordering* (`created_at` over the whole pool) as the reference frame for every temporal expression. The correct frame is sometimes different:

- the current turn's attachment set (Class A);
- the subset compatible with the span's own description (Classes B and C);
- a relation to an antecedent (Class D).

The zero-substantive-evidence observation from A2.8J is one symptom of this. It explains Class A only, and only partly: NB-C-02 C2 "this" has zero substantive evidence and is *correct*.

### 1.3 Hint provenance

Probe A hints are **oracle hints**: the harness maps ground-truth `temporal_meaning` through `TEMPORAL_MEANING_TO_RECENCY_HINT`. Notable mappings: `last_discussed → same`, `one_before_last_discussed → previous`, `earliest → earlier`.

On the real path, D1RQ derives `recency_hint` from the whole *clause* (`_recency_hint_for_text`). For example, NB-H-06's hint `earlier` comes from "last week", outside the span.

No prior batch has measured the realistic combination: D1RQ spans, D1RQ hints, and real ranks. A2.8K adds it as a measurement surface (§4, surface S-B).

---

## 2. Competing hypotheses

Each hypothesis is a single, isolated, deterministic change that can be toggled independently. None changes baseline RAR, RAR-SAFE, or the RAR contracts.

| ID | Hypothesis | Rule (implementation-level intent) | Target classes | Predicted risk |
|---|---|---|---|---|
| **H0** | Baseline | `resolve_rar_deterministic_extended` unchanged | — | reference point |
| **H1** | Level-5 evidence floor | A Level-5 ordinal binding is committed only if the span carries ≥1 substantive token. Excluded when counting: STOPWORDS, PRONOUNS, GENERIC_TYPE_WORDS, the target type word, and baseline RAR's own temporal/revision/attachment vocabulary (the A2.8J R3(a)-derived set; no new words). On failure, fall through; never abstain in place. | A | Loses correct zero-evidence bindings (e.g. NB-C-02 C2 "this", NB-L-03 C2 "the spreadsheet") |
| **H2** | Attachment-ambiguity precedence | When the span carries explicit attachment semantics (baseline Level-5.5 trigger set, unchanged), Level 5.5's attachment-set evaluation runs **before** Level 5's ordinal selection. Cascade order is otherwise unchanged. | A | Only affects attachment-worded spans; depends on what `is_attachment` means (§1.1) |
| **H3** | Evidence-compatible ordering domain | Level 5 computes its ordinal relation only over candidates compatible with the span's substantive tokens: every substantive token must appear in the candidate's title, tags, or aliases. Ordering *within* that subset is preserved. An empty subset means Level 5 does not bind and falls through. No substantive tokens means the domain is the current pool, i.e. baseline behaviour. | C, and incidentally B | Brittle lexical matching (abbreviations such as St/Street, which A2.8K does not repair). Overlaps with S2's absent-entity outcome on Class B (see scope note) |
| **H4** | Combination H1 + H2 + H3 | All three toggles together | A, B, C | Measures interaction effects; not presumed best |

**Scope note on H3 vs S2.** S2, found unsupported in A2.8J, *vetoed* a Level-5 binding when the span contradicted it, and it inherited Level 6's all-or-nothing absent-entity rule. H3 does not veto a winner. It changes *which set* the ordinal relation is computed over, so "latest X" means the latest *X*. H3 will affect Class B rows as a by-product; A2.8K reports that effect but does not target Class B. The narrow S2 misdirected-entity experiment and any S2 redesign remain out of scope (§6). If you consider H3 too close to S2, it can be dropped without affecting H1 or H2 (see §8, Q4).

### Diagnostic-only oracle probes (measurement aids, never adoption candidates)

| ID | Probe | Purpose |
|---|---|---|
| **DX-1** | Turn-attachment tie oracle. Candidates listed in the case's `turn_attachments` share one rank (same attach event). The harness passes this only to a diagnostic variant; no contract change. | Separates "Class A is caused by the rank clock" from "Class A is caused by precedence". If DX-1 alone fixes Class A, the real problem is that RAR lacks turn-attachment membership. That is a **contract/architecture question to escalate to the User**, not to solve inside A2.8K. |
| **DX-2** | Relative-anchor tagging. Rows whose ground-truth span is antecedent-relative ("before that / it", "the one before") are tagged in the analysis. No mechanism is added. | Quantifies Class D. Fixing it needs antecedent/session tracking, which is excluded (session state is frozen out of RAR experiments since A2.8J). A2.8K only measures and reports it. |

---

## 3. Deliverables (to be built after User approval)

**New files only.** No existing file is modified.

1. **`uri_v1/turn/rar_l5_experimental.py`**
   - One entry point, `resolve_rar_l5_experimental(query, *, h1: bool, h2: bool, h3: bool, dx1_tie_ids: frozenset = frozenset())`.
   - It is a fork of **baseline** `resolve_rar_deterministic_extended`, not of RAR-SAFE, so no S1/S2/S3 behaviour leaks in.
   - With all flags off it must be decision-identical to baseline on every surface. This is a mandatory equivalence test.
   - It reuses baseline helpers by import. No case IDs, no benchmark-specific vocabulary.
2. **`scripts/m35_a2_8k_l5_battery.py`**: runs every surface in §4 for H0–H4 plus DX-1, and writes telemetry and aggregates.
3. **`uri_v1/turn/rar_l5_diagnostic_fixtures.py`**: the frozen synthetic minimal-pair battery (S-D, §5). It is authored and hash-recorded **before** any hypothesis code exists (§7 step order).
4. **`tests/test_m35_uriv1_a2_8k_l5_experimental.py`**:
   - flag-off equivalence to baseline across all surfaces;
   - one mechanism test per hypothesis, written from the frozen semantics, not from observed output;
   - DX-1 isolation (no effect when `dx1_tie_ids` is empty).
5. Evidence outputs:
   - `docs/plans/M35_URIV1_A2_8K_TELEMETRY.json`, with a `variant` field (`H0`…`H4`, `DX1`) and a `surface` field (`S-A`…`S-D`);
   - `docs/plans/M35_URIV1_A2_8K_AGGREGATES.json`;
   - `docs/plans/M35_URIV1_A2_8K_EXECUTION_REPORT.md`;
   - `docs/plans/M35_URIV1_A2_8K_STATE.md` (the state file already exists at plan stage).

---

## 4. Measurement surfaces

| Surface | Spans | Hints | Ranks | Rows | Purpose |
|---|---|---|---|---|---|
| **S-A** Production-shaped | D1RQ | D1RQ | all 0 (`oracle_recency=False`) | natural corpus, C1/C2/C3 | Regression guard: every hypothesis must leave S-A decision-identical to H0 (Level 5 is inert there), unless a difference is individually explained |
| **S-B** Realistic hints, real ranks | D1RQ | D1RQ (clause-level) | `created_at` (`oracle_recency=True`) | natural corpus, C1/C2 | New: the condition recency wiring would actually create |
| **S-C** Oracle (Probe A generalised) | ground truth | oracle mapping | `created_at` | all 168 C1/C2 reference rows | Comparable with the A2.8J Probe A lineage |
| **S-D** Frozen minimal pairs | authored | authored | authored | §5 | Isolates each class with controlled pools |
| **S-E** Existing RAR tests | — | — | — | the five A2.5 RAR test files | Baseline must still pass 75/48. Each variant is swapped in (no test edited), and every conflict is classified as intended, regression, or test assumption challenged |

Integrity checks on every run:

- SHA-256 of `rar_deterministic.py`, `rar_contracts.py`, D1RQ, the corpus, `rar_safe_experimental.py`, and the S-D fixture file must be unchanged, checked pre- and post-run.
- Two independent runs must be decision-identical (latency excluded).

---

## 5. Frozen diagnostic battery S-D (design; items authored only after §8 answers)

Minimal pairs: each pair differs in exactly one evidence dimension. The target is 6–8 items per class. **Expected outcomes are fixed from the §8 semantics before any hypothesis code exists.**

- **A. Attachment set**
  - Pool sizes: 1, 2, and 3 attachments.
  - Timestamps: near-tie (≤60 s) and far-apart.
  - Wording: with and without an attachment word ("the attachment" vs "the file").
  - Hint: with and without a recency hint.
  - A version where one of the attachments is lexically named ("the attached invoice").
  - Expected semantics per Q1/Q2.
- **B. Absent entity**
  - "the earlier X" where X is absent from the pool, alongside a twin where X is present.
- **C. Ordering domain**
  - "the latest X" where the newest pool item is not X, alongside a twin where it is.
  - One pair uses an abbreviation mismatch (St/Street) and is labelled as a *known limitation* item, so H3's brittleness is measured rather than hidden.
- **D. Relative anchor**
  - "the one before that" and "the one before it", each with an intervening item in time.
  - Expected outcome per Q3.
- **N. Negative controls**
  - Correct Level-5 bindings every hypothesis must preserve: "the latest invoice" among invoices, "the revised draft" with one revised candidate, "the current version".

The fixture file's SHA-256 is recorded in STATE when it is frozen. Any later change reopens the plan.

---

## 6. Frozen scope

**In scope:** everything in §2–§5.

**Out of scope (User-directed):**

- S1 phrase-head refinement
- S2 redesign
- the narrow S2 misdirected-entity experiment
- S3 promotion
- New F / Level-6 scoring
- unrelated URI architecture

**Also out of scope (carried from A2.8J):**

- recency wiring into production
- T2 detection
- session state, aliases, stemming, abbreviation normalisation (Known C/D)
- any D1RQ change
- any modification of `rar_deterministic.py`, `rar_contracts.py`, or `rar_safe_experimental.py`
- RAR contract changes
- promotion of anything
- commit or push without explicit User authorisation

A contract field for turn-attachment membership is out of scope to *add*. If DX-1 shows it is needed, A2.8K reports that and escalates it.

---

## 7. Execution order (binding)

1. The User answers §8. Claude records the answers in this plan's history and freezes S-D semantics.
2. S-D fixture file authored and hash-recorded **before** any hypothesis code is written.
3. `rar_l5_experimental.py` with all flags off; the flag-off equivalence test passes on S-A through S-E.
4. H1, H2, H3, and DX-1 toggles implemented; mechanism tests written from the frozen semantics.
5. Full battery run twice (determinism check); telemetry and aggregates written.
6. Execution report written.
7. Stop at `VERIFICATION_READY` for Claude's independent audit.

Routing follows the standing AO-4 roles. Antigravity routes implementation; Codex is preferred for this multi-file experimental work. The A2.8J Sonnet substitution was a one-batch User directive and is not assumed to carry over.

---

## 8. Decisions required from the User before freeze

These are product semantics that the repository cannot settle. The corpus answers them for its own rows; S-D needs general rules.

- **Q1 — Explicit attachment reference, ≥2 current attachments, no distinguishing words.**
  - Proposed: always AMBIGUOUS (ask), regardless of timestamp gaps.
  - The corpus already labels NB-C-04 and NB-C-05 this way.
  - The open question is whether wide gaps (e.g. yesterday vs now) may allow "latest".
- **Q2 — Near-tie ordering (uploads seconds or minutes apart) with a recency word ("first", "latest").**
  - Proposed: AMBIGUOUS.
  - NB-C-07's author calls strict-earliest binding "acceptable, but a human would likely ask".
  - Should S-D treat binding as wrong (ICB) or tolerated (count it separately, not as an ICB)?
- **Q3 — Relative anchors ("the one before that / it").**
  - Proposed: A2.8K measures them only (DX-2).
  - S-D expects abstention unless the ordering domain is unambiguous without the antecedent.
  - Confirm that antecedent tracking stays deferred.
- **Q4 — H3 inclusion.**
  - H3 uses lexical compatibility to restrict the ordering domain. Confirm it is acceptable within the "no S2 redesign" boundary, or drop it.

---

## 9. Acceptance criteria (for the eventual implementation; defined now)

A2.8K is complete when all of the following hold, with evidence:

1. Baseline RAR, contracts, D1RQ, corpus, and RAR-SAFE are byte-unchanged (SHA-256 before and after).
2. Flag-off `rar_l5_experimental` is decision-identical to baseline on S-A through S-E.
3. Every hypothesis (H0–H4) and DX-1 is run on every surface; results are reproducible across two runs.
4. **Each hypothesis is classified with the rules pre-registered here, not tuned afterwards:**
   - **SUPPORTED**
     - closes every target-class ICB on S-C and S-D;
     - adds 0 new ICBs on any surface;
     - every lost correct resolution is individually shown to be a row whose frozen expected outcome allows abstention;
     - S-A is unchanged.
   - **PARTIALLY SUPPORTED:** closes some target-class ICBs, adds 0 new ICBs anywhere, and any correct-resolution loss is disclosed per row.
   - **NOT SUPPORTED:** adds any new ICB, or closes none of its target-class ICBs.
5. Every changed row (versus H0) on every surface is listed individually with class, mechanism, and before/after. No aggregate-only reporting.
6. The DX-1 result explicitly answers: is Class A caused by precedence, by the rank clock, or by missing turn-attachment evidence?
   - If by missing evidence, the report escalates the contract question without implementing it.
7. The DX-2 result quantifies Class D and states what it would take to address it (not implemented).
8. S-E conflicts are classified per variant.
9. `UNMEASURED` is used wherever something was not measured.
10. The final report answers the central question (§0) in the form of an evidence-condition table: for each evidence situation, whether Level 5 may bind, whether Level 5.5 takes precedence, or whether to abstain. Each cell cites supporting rows, or is marked UNMEASURED or UNSUPPORTED.
11. No commit, push, or promotion.

---

## 10. Planning-stage self-review (Verification-First standard)

- **Claims checked against source:**
  - Level-5 rule semantics: code read at lines 564–741.
  - `is_attachment` meaning: harness `build_candidate`.
  - Hint provenance: harness mapping and D1RQ `_recency_hint_for_text`.
  - The 168-row inventory: rerun this session against baseline.
  - Corpus rationales: quoted from `reason` fields.
- **Deliberately not done:** no hypothesis was prototyped or measured during planning. This prevents fitting the hypotheses or the battery to observed outcomes. All hypothesis effects are therefore **UNMEASURED**.
- **Known limits of this plan:**
  - The natural corpus has only 9 Level-5 ICBs (which is why S-D exists).
  - Class D cannot be fixed within the frozen scope.
  - H3 inherits lexical brittleness.
  - S-B uses `created_at`, which may not be the clock a future production recency source would use; that is flagged, not solved.
- **Carried-forward process lesson from A2.8J:** measured coverage losses and test conflicts must appear in the report itself, not only in aggregates.

---

## 11. History

- 2026-09-24: Drafted by Claude after A2.8J closure (User authorisation: "A2.8K PLANNING ONLY").
  - Evidence recovered from `rar_deterministic.py` Level 5/5.5, the natural-boundary harness, D1RQ, the corpus (168-row oracle inventory, `conversation_context`, author rationales), and the existing fixture inventory.
  - Status set to `PLAN_READY_FOR_USER_APPROVAL`. Not auto-accepted, per explicit User instruction.
  - No implementation performed.
- 2026-09-24: **User approval and §8 freeze.** User authorized A2.8K experimental implementation and measurement only (not production modification, promotion, baseline/contract change, commit, push, S3, S1/S2, Level-6/New-F, or recency production wiring), stopping at `VERIFICATION_READY`. §8 decisions frozen as follows:
  - **Q1 (generic attachment reference, ≥2 compatible, no distinguishing evidence):** `AMBIGUOUS`, unconditionally — timestamp gaps (however wide) do not license "latest" for a *generic* reference such as "the attachment". This is a separate S-D case from an *explicit* temporal/ordinal reference ("the latest attachment", "the first attachment"); Q1 is not encoded as a universal `>=2 attachments => AMBIGUOUS` rule and must not veto Q2 cases.
  - **Q2 (explicit temporal/ordinal attachment reference — "the first/latest attachment"):** no arbitrary timestamp-gap threshold (e.g. no "<=60s => AMBIGUOUS" rule). Distinguish **Case A** (the supplied ordering evidence is authoritative for the relation the reference actually expresses — a deterministic binding may be correct even seconds apart) from **Case B** (the ordering field is the wrong clock — e.g. historical object `created_at` rather than current-turn attachment order — where the correct behaviour is abstention/ambiguity even with a wide gap, because the evidence does not represent the asked-about relation). DX-1 must help attribute Class-A failures among: Level-5 precedence, wrong rank clock, missing current-turn attachment membership/order evidence, or an interaction of these.
  - **Q3 (relative anchors — "the one before that/it"):** remain `MEASURE_ONLY` under DX-2. No antecedent/session tracking is implemented in A2.8K; if correct resolution requires knowing the antecedent, record that as a capability dependency and leave the solution deferred.
  - **Q4 (H3 inclusion):** approved as originally scoped (Evidence-Compatible Ordering Domain — restricts the *domain* the ordinal relation operates over to candidates lexically compatible with the span's substantive tokens; does not veto an already-proposed winner, which remains S2's distinct, out-of-scope question). No stemming, fuzzy matching, aliases beyond baseline, abbreviation normalization, or semantic similarity is added; the St/Street case remains a measured known-limitation row, not repaired.
  - Execution routing: Codex preferred implementer, Antigravity coordinator per standing AO-4 (routing directive dated 2026-09-24); Claude Sonnet is fallback 1. Both Codex and Antigravity run entirely outside the Claude Code session per standing governance (see memory `uri-ao4-development-cycle`), so — after verifying repository/branch state and the presence of this plan/state — Claude proceeded as fallback 1 implementer with the User's explicit confirmation, since Codex/Antigravity could not be invoked or simulated from this session.
  - No hypothesis code existed at the time of this freeze entry (§7 step order preserved: S-D authored and hash-recorded next, before any `rar_l5_experimental.py` code).

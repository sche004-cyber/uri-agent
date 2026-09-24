# M35 URIv1 — A2.8L: Trustworthy Attachment-Order Evidence Transport Factorial (FROZEN PLAN)

**Status:** `FROZEN — PLAN ONLY — IMPLEMENTATION AND EXECUTION NOT AUTHORIZED`

**Date:** 2026-09-24  
**Branch:** `m35-uri-v1-parallel-architecture`  
**Planning baseline:** `9e5d5e2810b38e046ead2adb2482403b4d3166a5`  
**Predecessors:** A2.8K `CLOSED / ACCEPTED`; A2.9 `CLOSED / ACCEPTED AS PILOT`

This document freezes the next RAR experiment derived directly from A2.8K's
accepted residual findings. It authorizes no implementation, execution,
production integration, promotion, contract change, commit, or push.

The experiment is deterministic. It adds no model or AI component. It preserves
the accepted `RARCandidate`, `RAREvidence`, `RARDeterministicAnchor`, `RARQuery`,
and `RARResolution` contracts and does not modify the production resolver.

### Amendment history

This file was authored and left untracked (`git status` showed it as `??`)
before this pass. It is amended here, under accepted planning review findings
A1–A8, before its first immutable freeze checkpoint. No prior git-tracked
version exists, so this amendment is recorded as the file's origin revision,
not a delta against a previously frozen state. The amendments applied are:

- **A1** — gave factors **P** and **G** independently testable consumers
  (§4.1) so their necessity can be measured separately rather than only as a
  joint effect through **R**.
- **A2** — constrained **G**'s ordinal use: without **P** authorizing it,
  group evidence may supply same-event ties only, never an ordinal (§4.1).
- **A3** — froze the explicit-attachment-ordinal trigger for **D** to the
  existing `recency_hint`/`is_attachment` predicates already used by the
  production query path, adding no new detection logic (§4.1).
- **A4** — froze the transport-compiler algorithm as an explicit numbered
  procedure (§4.2.1) and labelled the runtime guardrail thresholds in §10.2 as
  provisional pre-registered thresholds.
- **A5** — corrected the classification of `NB-C-04`/`NB-C-05` (the former is
  a control-only row, not a causal Case-A/B target) and disclosed that every
  Case-A trustworthy-order target in this plan is authored-only (§5.1).
- **A6** — corrected the decision-row and overlay-manifest-entry arithmetic,
  which had not accounted for `C-NATURAL-PHOTOS`'s two pool-condition rows
  (§4.3, §9).
- **A7** — constrained every ordinal case to at most two current-turn members
  and disclosed the resulting truncation risk for 3+-member generalization
  (§4.3).
- **A8** — required the immutable plan-plus-overlay-manifest freeze checkpoint
  to exist and be hash-recorded before any mechanism code may be written
  (§5.4, §14).

---

## 1. Research question

For explicit attachment-ordinal references, which evidence and resolver
mechanisms are necessary, sufficient, or interacting to:

1. preserve a trustworthy Case-A binding when the supplied order actually
   represents the current-turn attachment relation expressed by the user; and
2. abstain safely in Case B when the apparent order is historical object time,
   same-event/tied attachment input, unknown provenance, or polluted by
   non-turn distractors?

The experiment must also answer a narrower architecture question:

> Can the required evidence be deterministically compiled into the accepted
> RAR contracts for one query, or does a sidecar-aware resolver demonstrate a
> behavioral capability the existing-contract projection cannot reproduce?

No result from this experiment may be labelled `NEW_CONTRACT_FIELD_REQUIRED`.
At most it may establish `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`, because
the experiment does not enumerate every possible transport design.

---

## 2. Evidence recovered and frozen

### 2.1 A2.8K accepted findings

- DX-1 tied current-turn attachments and closed 5 of 6 measured Class-A ICBs
  with zero new ICBs and zero lost correct resolutions. It established a
  sufficient intervention and partial clock causality, not sole causality.
- `NB-C-05` C2 is the decisive residual: the two actual current-turn
  attachments are complete in `turn_attachments`, while a third newer
  file-reference candidate is outside that set. Level 5 ignores membership and
  selects the third global rank-0 candidate.
- Distinguishing trustworthy from untrustworthy attachment order requires:
  current-turn membership; event/order grouping or ties; and provenance that
  identifies what relation an order represents.
- Membership alone is insufficient for the Case-A/Case-B distinction.
- H2's unconditional Level-5.5 precedence closed six measured attachment ICBs
  but lost the two valid Case-A bindings `SD-A-04` and `SD-A-06`.
- Corrected H3 established that candidate-domain restriction and
  domain-relative rank can repair ordering-domain cases only when the domain is
  genuinely narrowed. Re-ranking an unchanged domain is unsafe.
- H1/H2/H3/H4 remain `PARTIALLY_SUPPORTED`; none is production-ready.
- A2.8K did not establish that a new RAR contract field is necessary.

### 2.2 Accepted contracts and current path

- `RARCandidate` carries `recency_rank` and `is_attachment`, but no membership,
  event id, order-source, or provenance field.
- `RARDeterministicAnchor.current_attachment_id` is singular and can represent
  a certain single attachment, not a multi-attachment set or order.
- Production-shaped candidate construction sets every candidate rank to `0`;
  the ordinal branches are currently masked on that path.
- Baseline Level 5 runs before Level 5.5. Level 5 uses the current candidate
  pool and raw `recency_rank`; Level 5.5 treats every `is_attachment=True`
  candidate in that pool as an attachment candidate.
- In the natural-boundary harness, `is_attachment=True` means
  file-reference-shaped, not current-turn membership.

### 2.3 Prior evidence reused, not duplicated

- A2.8J already established that RAR-SAFE does not repair the zero-substantive
  Level-5 attachment residual (`NB-C-04`/`NB-C-05`) and that unconditional
  precedence is a distinct question. RAR-SAFE is historical evidence, not a
  new factor or implementation base in A2.8L.
- A2.8K's R2 telemetry, aggregates, and accepted audit remain the baseline for
  H2/H3/DX-1 effects. A2.8L does not rerun those variants merely to reproduce
  already-accepted counts.
- D1RQ remains unchanged. Its realistic clause-level hint behavior is used only
  on a confirmation surface; the causal factorial uses authored exact spans and
  hints so detector behavior cannot confound the factor effects.
- The existing frozen S-D fixtures remain byte-unchanged. A2.8L supplies a
  separate immutable evidence-overlay manifest keyed to those fixture ids.

---

## 3. Frozen semantics

### 3.1 Case A — trustworthy order

The reference is explicitly temporal/ordinal (for example, "the latest
attachment" or "the first attachment"). The order supplied to the resolver is
authoritative for the relation expressed by the user. A deterministic binding
is required even when attachment times are close.

### 3.2 Case B — untrustworthy or insufficient order

The apparent order is not authoritative for the requested relation: it may be
historical object `created_at`, an unknown source, a same-event/tied group, or a
global rank polluted by non-turn candidates. The required outcome is
`AMBIGUOUS` over exactly the compatible current-turn members when at least two
are known; otherwise safe `UNKNOWN`/`AMBIGUOUS` is accepted only as explicitly
frozen per case. A confident binding is always wrong.

### 3.3 Generic attachment references

For a generic singular reference such as "the attachment", two or more
indistinguishable current-turn attachments remain `AMBIGUOUS` regardless of
timestamp gaps. This is a control inherited from A2.8K Q1, not an ordinal case.

### 3.4 Provenance vocabulary

The experiment-only overlay uses exactly these values:

- `CURRENT_TURN_ATTACHMENT_SEQUENCE`: authoritative for Case-A attachment
  order.
- `HISTORICAL_OBJECT_CREATED_AT`: not authoritative for current-turn
  attachment order.
- `UNKNOWN`: no authority to use the supplied order for a confident binding.

No other provenance label may be added after freeze without reopening the plan.

---

## 4. Variables and factorial design

### 4.1 Six binary factors

| ID | Factor OFF | Factor ON |
|---|---|---|
| **M** | Current-turn membership omitted | Exact current-turn candidate-id set is transported |
| **G** | Attachment event grouping/order omitted | Exact event group and group ordinal are transported; same-event members tie |
| **P** | Ordering provenance omitted | The truthful provenance label from §3.4 is transported |
| **D** | Level 5 evaluates the baseline/global candidate domain | For an explicit attachment ordinal, Level 5 restricts to transported current-turn membership, then applies existing type/lexical compatibility; if M is absent, D is a recorded no-op |
| **R** | Preserve supplied/global ranks | Within a genuinely restricted domain, derive dense domain-relative ranks from transported event/order evidence only when its provenance authorizes that relation; ties remain ties. Missing/untrusted evidence cannot license a bind |
| **Q** | Baseline precedence: Level 5 before Level 5.5 | Unconditional H2 precedence: Level 5.5 before Level 5, byte-equivalent in intent to A2.8K H2 |

The causal phase executes the complete `2^6 = 64` matrix. Conditional no-ops
are not dropped: they are telemetry (`factor_requested`, `factor_consumed`,
`no_op_reason`) and are required to distinguish unavailable evidence from a
mechanism with no effect.

**A1 — independent consumers for P and G.** G and P are consumed by two
decoupled gates inside R, not by one merged check, so each factor's effect is
independently observable:

- the **order-derivation gate** consumes G alone: it groups current-turn
  members by event id and detects same-event ties;
- the **authorization gate** consumes P alone: it checks whether the
  transported provenance equals `CURRENT_TURN_ATTACHMENT_SEQUENCE` before any
  derived group ordinal may be used as a bind-worthy rank.

A cell with G on/P off and a cell with G off/P on must therefore be
distinguishable in the failure-class telemetry
(`EVENT_GROUP_NOT_AVAILABLE` vs `ORDER_PROVENANCE_NOT_AVAILABLE`, §8), not
collapsed into one combined "R had insufficient evidence" outcome.

**A2 — G is ties-only without P.** When the authorization gate is not
satisfied (P absent, or P present but not
`CURRENT_TURN_ATTACHMENT_SEQUENCE`), the order-derivation gate's group
ordinal values are discarded: G may only report same-event equality (a tie),
never a derived order. A confident bind can be produced only when both gates
pass. This prevents G's ordinal from silently acting as an unauthorized
order source.

**A3 — frozen ordinal trigger for D.** "Explicit attachment ordinal" (§4.1
row D) is frozen to the conjunction of two predicates already present on the
production query path, and no new detection logic may be added to recognize
it: `query.recency_hint in {"latest", "first"}` and
`candidate.is_attachment is True` for the pool member under evaluation. D
restricts the Level-5 domain only when this exact conjunction holds and M is
present; per §4.1, if M is absent the restriction is a recorded no-op rather
than a partial restriction.

The factorial implementation must not change more than the six named semantics.
Every cell is generated from the same resolver body with flags; no cell-specific
branch, case id, title, timestamp threshold, or benchmark vocabulary is allowed.

### 4.2 Transport comparison

After the causal matrix identifies all minimal sufficient factor sets, each set
and each one-factor ablation is evaluated through two transport arms:

1. **SIDE-CAR REFERENCE:** an experiment-local immutable evidence overlay is
   consumed directly by the experimental wrapper. It does not change any RAR
   contract.
2. **EXISTING-CONTRACT COMPILER:** a deterministic upstream adapter consumes the
   same overlay, constructs a query-local clone using only accepted fields
   (candidate projection, `is_attachment`, `recency_rank`, and the existing
   singular anchor where valid), then calls the unchanged baseline resolver.
   No overlay reaches the resolver.

The compiler may project a candidate subset only for the single explicit
attachment reference being evaluated. It must validate the returned resolution
against the original supplied candidate universe, not merely the projected
subset. It may not mutate source candidates or reuse projected state across
references.

#### 4.2.1 Frozen compiler algorithm (A4)

The EXISTING-CONTRACT COMPILER must implement exactly this deterministic
procedure, in this order, with no case-specific branch:

1. Confirm the query matches the A3-frozen ordinal trigger
   (`recency_hint in {"latest","first"}` and `is_attachment is True` on the
   pool). If not matched, pass the query through unmodified.
2. Read the overlay's current-turn membership set for this query. If M is not
   transported, skip projection and call the unchanged baseline resolver on
   the original candidate universe.
3. Clone only the candidates whose id is in the membership set into a
   query-local candidate list; do not mutate the original list or any shared
   candidate object.
4. If R is enabled and the overlay's provenance equals
   `CURRENT_TURN_ATTACHMENT_SEQUENCE`, set each cloned candidate's
   `recency_rank` to the dense domain-relative rank derived from the overlay's
   event ordinals (ties receive equal rank); otherwise leave `recency_rank`
   values as originally supplied.
5. If the overlay carries a single authoritative current attachment and no
   multi-member order is needed, the existing singular
   `RARDeterministicAnchor.current_attachment_id` may be populated as a
   control value only; it is never used as the multi-member order source.
6. Call the unchanged baseline resolver with the query-local clone.
7. Validate the returned resolution: the bound or ambiguous candidate id(s)
   must be a subset of the original supplied candidate universe. A resolution
   referencing an id outside that universe is
   `CONTRACT_VIOLATION_OR_CANDIDATE_INVENTION` (§8), not a valid row.
8. Return the validated resolution; discard the query-local clone.

No step may be reordered, merged, or made conditional on case id, title, or
benchmark vocabulary.

`RARDeterministicAnchor.current_attachment_id` is additionally measured as a
single-attachment control. It is not treated as a candidate solution for
multi-attachment order.

### 4.3 Experimental size (A6 — corrected arithmetic)

`C-NATURAL-PHOTOS` is one case template that produces two decision rows (its
`NB-C-04` C1 and C2 pool conditions), so the 13 case *templates* yield 14
decision-generating rows per cell/repeat. The counts below are corrected
accordingly; the prior draft's `1,664`/`832` figures undercounted this and are
superseded here.

- Causal matrix: 64 cells × 14 rows (13 case templates, one contributing 2
  pool-condition rows) × 2 deterministic repeats = **1,792 decision rows**.
- Transport comparison: let `T = 1 (baseline)` + `S` (minimal sufficient
  cells) + `Σablations` (one-factor ablations across those cells, each cell
  contributing at most 6). Rows = `T × 14 rows × 2 arms × 2 repeats = 56 × T`.
  The hard cap is **896 decision rows**, so `T ≤ 16`. If the discovered
  minimal-sufficient-set count would push `T` above 16, stop and report
  `PLAN_REOPEN_REQUIRED` rather than silently sampling cells or cells'
  ablations.
- Confirmation/regression surfaces are additional but fixed in §5.3.

**A7 — ordinal member-count constraint and disclosed truncation risk.** Every
frozen ordinal case (§5.1, §5.2) uses at most two current-turn members. This
plan draws no conclusion, explicit or implied, about resolver behavior with
three or more simultaneous current-turn ordinal candidates; that generalization
is untested and is a disclosed truncation risk, not a validated boundary. A
minimal sufficient set accepted under this plan authorizes only the
two-member case, and any future extension to 3+ members requires its own
plan or plan reopening.

No model calls occur.

---

## 5. Frozen cases

### 5.1 Causal target cases

| ID | Source | Frozen distinction | Expected |
|---|---|---|---|
| **A-LATEST-2** | Reuse `SD-A-04` | Two current-turn attachments, distinct ordered events, order provenance `CURRENT_TURN_ATTACHMENT_SEQUENCE` | Resolve `sd-a4-new` |
| **A-FIRST-2** | Reuse `SD-A-06` | Same as above, `first` relation | Resolve `sd-a6-early` |
| **A-LATEST-DISTRACTOR** | New overlay case | Two current-turn attachments in authoritative order plus a newer non-turn file at global rank 0 | Resolve the latest current-turn attachment; never the distractor |
| **B-LATEST-WRONG-CLOCK** | Reuse `SD-A-05` | Same apparent ranks as Case A, but provenance `HISTORICAL_OBJECT_CREATED_AT`; current-turn event evidence ties the members | `AMBIGUOUS` over the two current-turn ids |
| **B-FIRST-WRONG-CLOCK** | Reuse `SD-A-07` | Same as prior with `first` relation | `AMBIGUOUS` over the two current-turn ids |
| **B-LATEST-PROVENANCE-TWIN** | New overlay case | Candidate ids, membership, groups, numeric ranks, and wording identical to A-LATEST-2; only provenance changes to `UNKNOWN` | `AMBIGUOUS` over the two current-turn ids |
| **B-DISTRACTOR** | Reuse natural `NB-C-05` C2 | Two re-attached current-turn documents plus newer non-turn file-reference distractor | `AMBIGUOUS` over exactly the two `turn_attachments` ids |

`A-LATEST-2` and `B-LATEST-PROVENANCE-TWIN` are the load-bearing provenance
minimal pair. Their serialized records must be byte-identical after removal of
the provenance and expected-outcome fields.

The two new records are frozen at planning time as follows (the future fixture
module must encode these values exactly):

| Field | `A-LATEST-DISTRACTOR` |
|---|---|
| Reference | `the latest attachment`; `recency_hint=latest`; no type hint |
| Candidates | `a2l-ad-old` / `Draft_Old.pdf` / rank 2 / attachment; `a2l-ad-new` / `Draft_New.pdf` / rank 1 / attachment; `a2l-ad-distractor` / `Unrelated_Newer.pdf` / rank 0 / attachment |
| Current-turn membership | `{a2l-ad-old, a2l-ad-new}` |
| Event groups | `a2l-ad-old → event-0`; `a2l-ad-new → event-1`; distractor has no current-turn event |
| Group ordinal | `event-0=0`, `event-1=1` |
| Provenance | `CURRENT_TURN_ATTACHMENT_SEQUENCE` |
| Expected | `RESOLVED → a2l-ad-new` |

`B-LATEST-PROVENANCE-TWIN` reuses `SD-A-04` without changing its query or
candidates: membership is `{sd-a4-old, sd-a4-new}`; `sd-a4-old → event-0`,
`sd-a4-new → event-1`; ordinals are `0,1`; supplied candidate ranks remain
`sd-a4-new=0`, `sd-a4-old=1`. Its only semantic input difference from
`A-LATEST-2` is provenance `UNKNOWN`; its expected decision is `AMBIGUOUS`
over `{sd-a4-new, sd-a4-old}`. The overlay serializer must prove the stated
minimal-pair equality before any run.

Frozen overlay facts for the reused A/B causal-target fixtures are:

| Case | Membership | Event relation | Provenance |
|---|---|---|---|
| `SD-A-04` | both fixture ids | distinct ordered events, old then new | `CURRENT_TURN_ATTACHMENT_SEQUENCE` |
| `SD-A-06` | both fixture ids | distinct ordered events, early then late | `CURRENT_TURN_ATTACHMENT_SEQUENCE` |
| `SD-A-05` | both fixture ids | one shared event (tie) | `HISTORICAL_OBJECT_CREATED_AT` |
| `SD-A-07` | both fixture ids | one shared event (tie) | `HISTORICAL_OBJECT_CREATED_AT` |
| `NB-C-05` C1/C2 | exactly the two corpus `turn_attachments` ids | one shared re-attachment event (tie) | `HISTORICAL_OBJECT_CREATED_AT` |

`NB-C-05` is the only natural-corpus row above and is a genuine §5.1 causal
Case-B target (`B-DISTRACTOR`). The C2 distractor has no current-turn event
and must never enter the current-turn ambiguity set.

**A5 — `NB-C-04` reclassified.** `NB-C-04` C1/C2 is **not** a §5.1 causal
Case-A/B ordinal target. It is a §5.2 control (`C-NATURAL-PHOTOS`) exercising
generic wording and near-time photos, not an explicit attachment ordinal; its
overlay facts (membership = the two corpus `turn_attachments` ids, one shared
attachment event, provenance `HISTORICAL_OBJECT_CREATED_AT`) are frozen in
§5.2, not in this causal-target table. Listing it here in the prior draft
misclassified it as a causal target and risked double-counting it against
both the causal-matrix and control row totals in §4.3.

**A5 — Case-A authored-only disclosure.** Every Case-A trustworthy-order
target in this plan (`A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR`) is
authored: none is drawn from or confirmed against the natural corpus. The two
natural-corpus rows used (`NB-C-04`, `NB-C-05`) confirm only Case-B
abstention and generic-wording control behavior, not Case-A resolution
accuracy. Any claim that a minimal sufficient set "resolves Case-A correctly"
is therefore scoped to authored fixtures only; it carries no natural-corpus
external-validity evidence for Case-A specifically. This limitation is
disclosed here rather than left implicit, per Verification-First Audit
disclosure requirements.

### 5.2 Controls and interaction cases

| ID | Source | Purpose | Expected |
|---|---|---|---|
| **C-GENERIC-2** | Reuse `SD-A-02` | Generic attachment ambiguity | `AMBIGUOUS` over both ids |
| **C-NATURAL-PHOTOS** | Reuse natural `NB-C-04` C1 and C2 as one paired control | Generic wording, near-time photos, optional non-turn distractor | `AMBIGUOUS`; ambiguity set excludes the non-turn distractor when M+D are consumed |
| **C-LEXICAL-ATTACHMENT** | Reuse `SD-A-08` | Lexically distinguished member inside attachment domain | Resolve `sd-a8-invoice` |
| **C-DOMAIN-RANK-SYNTH** | Reuse `SD-C-02` | Non-attachment candidate-domain restriction and domain-relative rank | Resolve `sd-c2-minutes` |
| **C-DOMAIN-RANK-NATURAL** | Reuse natural `NB-D-01` C2 | Natural ordering-domain confirmation | Resolve `2f58b7c0-e6a3-4d91-a4c5-09d7e1f2d111` |
| **C-NO-RANK0** | Reuse the accepted `test_rc1_current_conflicting_no_rank0_abstains` shape | Prevent re-ranking an unchanged domain from fabricating a winner | Must not `RESOLVE` |

The natural C1/C2 pair counts as one frozen case template with two pool
conditions, keeping the factorial case count at 13 while preserving both rows.

### 5.3 Confirmation and regression surfaces

The winning/minimal sufficient cells and their one-factor ablations run on:

- the full existing 18-case S-D battery, unchanged;
- selected natural rows `NB-C-04`, `NB-C-05`, `NB-D-01`, and `NB-D-02` at C1/C2;
- a D1RQ confirmation surface for those natural rows using D1RQ spans and
  clause-level hints, with both production-shaped all-zero ranks and the
  existing `created_at` oracle ranks;
- the unchanged A2.5 RAR test modules used by A2.8K S-E;
- flag-off equivalence against baseline on every above surface.

`NB-D-02` remains a relative-anchor capability-gap control. No cell may claim
to solve it without antecedent evidence; safe abstention is the only accepted
non-baseline change.

### 5.4 Freeze mechanics

**A8 — blocking freeze checkpoint.** Before mechanism code exists, both of the
following must be true, verified by an independent reader who is not the
implementer:

1. This plan file itself is immutable: its SHA-256 is recorded and no further
   semantic edit occurs without reopening the plan.
2. The overlay manifest (`docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`)
   exists, contains every new case and every overlay for reused cases, and its
   SHA-256 is recorded alongside the hashes of the protected files listed in
   §13.2, the natural-corpus fixture file, and A2.8K R2 evidence.

Both hashes are recorded in the A2.8L state file at `IMPLEMENTING` entry, not
merely referenced. Any later fixture/overlay change invalidates all results
and reopens this plan. No mechanism code (§13.1 items 1–4) may be written
before both conditions hold.

---

## 6. Hypotheses

- **HM:** Membership transport is necessary in the presence of non-turn file
  distractors, but is not sufficient without a domain consumer.
- **HG:** Event grouping is necessary to abstain on same-event Case-B inputs
  whose historical ranks differ.
- **HP:** Provenance is necessary for the A/B provenance twin, where all other
  values are identical.
- **HD:** Candidate-domain restriction is necessary to prevent a global
  non-turn rank-0 distractor from winning.
- **HR:** Domain-relative rank is necessary when the correct latest member has
  a nonzero or gapped global rank after domain restriction; it must remain off
  for an unchanged domain.
- **HQ:** Unconditional Level-5.5 precedence is neither necessary nor
  sufficient for the joint A/B objective and interacts destructively with
  valid Case-A order. This is a confirmatory hypothesis based on A2.8K H2,
  not a novel claim.
- **HT:** A query-local existing-contract compiler is behaviorally sufficient
  to reproduce every minimal sufficient sidecar cell. Failure to reproduce is
  evidence of compiler insufficiency, not automatic proof that a new field is
  required.

---

## 7. Necessity, sufficiency, and interaction rules

A cell is **QUALIFYING** only when it:

1. resolves every Case-A target to the exact frozen id;
2. returns the exact frozen Case-B abstention family and ambiguity set;
3. passes every control;
4. introduces zero incorrect confident bindings, candidate inventions,
   non-member bindings, and wrong-domain ambiguity sets;
5. is decision-identical across two runs; and
6. causes no unexplained A2.5/S-D/D1RQ confirmation regression.

Definitions are deterministic and pre-registered:

- **Necessary factor:** ON in every qualifying cell, and switching it OFF in a
  matched ablation of at least one minimal qualifying cell causes a frozen
  target failure. If an alternative qualifying cell omits it, it is not
  necessary.
- **Sufficient factor:** the cell with only that factor ON qualifies.
- **Minimal sufficient set:** a qualifying cell for which no strict subset of
  enabled factors qualifies.
- **Interacting pair:** neither single-factor cell qualifies, the pair under
  the same background repairs at least one case neither single repairs, and
  the pair occurs in at least one minimal sufficient set. Report the exact
  2×2 decision table. The same subset rule applies to higher-order
  interactions.
- **Alternative mechanisms:** multiple incomparable minimal sufficient sets
  are reported separately; their shared factors alone may be called necessary.

No p-value, model judge, aggregate accuracy threshold, or post-hoc weighting is
used. Full decision tuples are `(outcome, candidate_id,
set(ambiguous_candidate_ids))`.

---

## 8. Failure classifications

Every failing row has one earliest primary class and optional secondary factor
interactions:

- `INCORRECT_CONFIDENT_BINDING`
- `UNTRUSTWORTHY_ORDER_BIND`
- `NON_CURRENT_TURN_MEMBER_BIND`
- `WRONG_AMBIGUITY_DOMAIN`
- `MISSED_TRUSTWORTHY_BINDING`
- `MEMBERSHIP_NOT_AVAILABLE`
- `EVENT_GROUP_NOT_AVAILABLE`
- `ORDER_PROVENANCE_NOT_AVAILABLE`
- `DOMAIN_RESTRICTION_NOT_APPLIED`
- `RANK_FRAME_ERROR`
- `PRECEDENCE_SUPPRESSION`
- `UNCHANGED_DOMAIN_RERANK`
- `BASELINE_REGRESSION`
- `CONTRACT_VIOLATION_OR_CANDIDATE_INVENTION`
- `HARNESS_OR_FIXTURE_INVALID`

Safe abstention caused by deliberately omitted evidence is recorded as
`EVIDENCE_ABLATION_SAFE_ABSTENTION`, not credited as solving a Case-A target.

---

## 9. Acceptance criteria

A2.8L may reach `VERIFICATION_READY` only if all are met:

1. The overlay manifest was frozen and hash-recorded before mechanism code.
2. All 64 factorial cells ran for all 14 rows (13 case templates, with
   `C-NATURAL-PHOTOS` contributing 2 pool-condition rows per §4.3) twice; no
   missing/duplicate key.
3. Full decision tuples are identical across repeats.
4. Main effects, every pairwise 2×2 interaction, all minimal sufficient sets,
   and any observed higher-order minimal interaction are reported from raw rows.
5. Every changed row versus all-off baseline is listed; no aggregate-only
   claim is allowed.
6. Necessary/sufficient/interacting labels follow §7 exactly.
7. The winning cells introduce zero ICBs, non-member binds, wrong ambiguity
   domains, candidate invention, or contract violations on any surface.
8. Flag-off behavior is decision-identical to baseline.
9. Existing contracts, production RAR, RAR-SAFE, D1RQ, natural corpus, S-D,
   A2.8K telemetry/aggregates/reports, and existing tests remain byte-unchanged.
10. SIDE-CAR and EXISTING-CONTRACT COMPILER results are compared on all
    required transport cells. Every mismatch is row-level and causally traced.
11. Contract conclusion is one of:
    - `EXISTING_CONTRACT_COMPILATION_BEHAVIORALLY_SUFFICIENT`;
    - `EXISTING_CONTRACT_COMPILATION_INSUFFICIENT`;
    - `TRANSPORT_RESULT_INCONCLUSIVE`.
    `NEW_CONTRACT_FIELD_REQUIRED` is prohibited.
12. D1RQ confirmation results are reported separately from the causal matrix;
    detector errors cannot be attributed to an RAR factor.
13. CPU, latency, and memory measurements in §10 are present and reproducible.
14. No implementation is integrated or promoted to production.
15. No commit or push without separate explicit authorization.

No individual mechanism is accepted merely because it reduces ICBs. It must
preserve all frozen trustworthy bindings and pass the full safety gate.

---

## 10. Telemetry and runtime measurements

### 10.1 Required decision telemetry

Each row records:

- schema version, run id, repeat index, case id/source/hash, surface, pool
  condition, and transport arm;
- M/G/P/D/R/Q requested bits, consumed bits, and no-op reasons;
- original candidate ids/ranks/attachment flags;
- ground-truth and transported membership ids;
- event group ids and group ordinals;
- order provenance;
- effective Level-5 domain and eliminated/non-member ids;
- original, projected, and effective domain-relative ranks;
- whether Level 5 or Level 5.5 ran first and which branch returned;
- expected and actual full decision tuples, rule, level, failure class, and
  primary/secondary experimental failure classifications;
- evidence consumed by the winning decision;
- compiler projection details and validation against the original universe;
- wall time, CPU time, and allocation metrics.

Aggregates must reconcile to a raw-row rescan for every cell, as A2.8K-R1/R2
required. Ambiguous-id order is non-semantic and compared as a set; emitted ids
remain in deterministic candidate order.

### 10.2 Performance protocol

Functional scoring runs do not use allocation tracing. A separate performance
pass measures:

- `perf_counter_ns` wall time and `process_time_ns` CPU time;
- Python peak allocated bytes using `tracemalloc` in an isolated pass;
- pool sizes 2, 8, 32, and 128 using deterministic synthetic distractors;
- all-off baseline, each single factor, every minimal sufficient cell, and each
  transport arm;
- 200 warmups and 2,000 randomized/interleaved measured iterations per cell;
- OS, Python version, CPU identifier, process bitness, and source hashes.

Runtime guardrails for a qualifying mechanism (provisional pre-registered
thresholds — set from A2.8K R2's reference range and engineering judgement,
not from a completed A2.8L measurement pass; may be revisited only through
plan reopening, never adjusted post-hoc to fit observed results):

- for pools up to 32, paired p95 wall-time overhead versus all-off must be no
  more than `max(0.25 ms, 2× baseline p95)`;
- median CPU-time overhead must be no more than 2× baseline;
- growth from pool 32 to 128 must be consistent with no worse than `O(n log n)`
  (measured ratio ≤ 6×); and
- peak Python allocation at pool 128 must remain below 256 KiB per call.

Crossing a threshold yields `RUNTIME_COST_BLOCKER`; it does not invalidate the
causal evidence, but prevents any promotion recommendation. A2.8K R2's observed
reference range (mean about 0.04–0.06 ms; p95 about 0.12–0.16 ms across variants)
is context only, not substituted for the new measurements.

---

## 11. Reproducibility requirements

- Record SHA-256 before and after for every protected file and every generated
  fixture/overlay, script, telemetry, and aggregate artifact.
- Persist the complete 64-cell manifest and the exact ordering of randomized
  performance iterations.
- Run the functional battery twice in fresh processes; latency is excluded from
  decision determinism comparison.
- Use no network, model, clock-derived case data, random case generation, or
  mutable external state.
- Any seed used only for performance interleaving is fixed and recorded.
- Preserve original, R1, and R2 A2.8K evidence unchanged.
- An independent auditor must reproduce raw decision counts and transport-arm
  equivalence before closure.

---

## 12. Risks and confounds

- **Hierarchical factors:** D cannot consume absent M; R cannot lawfully use
  absent/untrusted G/P. The full matrix retains these as explicit no-op cells so
  hierarchy is visible rather than silently pruned.
- **Oracle overlay risk:** the causal matrix uses authored evidence. D1RQ and
  natural confirmation surfaces are therefore reported separately.
- **Candidate projection risk:** compiling evidence into a narrowed query may
  affect earlier/later cascade levels. Flag-off and non-attachment controls,
  plus sidecar/compiled row comparison, are mandatory.
- **`is_attachment` semantic overload:** current code treats file-reference
  shape as attachment. A2.8L never relabels that as current-turn membership;
  membership remains a separate overlay fact or query-local projection.
- **Precedence duplication:** H2's standalone result is already known. Q is
  retained only to measure interactions with correct domain/rank evidence.
- **Authored-case external validity:** the factorial gives causal separation,
  not population frequency. Natural rows provide bounded confirmation only.
- **Latency noise:** sub-millisecond functions are noise-sensitive; randomized
  interleaving, warmup, CPU time, and separate allocation passes are required.
- **Transport conclusion scope:** compiler success shows a new field was not
  needed for these cases. Compiler failure does not prove a field is the only
  solution.

---

## 13. Frozen scope and future files

### 13.1 Files to create if implementation is separately authorized

1. `uri_v1/turn/rar_attachment_order_experimental.py`
2. `uri_v1/turn/rar_attachment_order_factorial_fixtures.py`
3. `scripts/m35_a2_8l_rar_attachment_order_factorial.py`
4. `tests/test_m35_uriv1_a2_8l_rar_attachment_order_factorial.py`
5. `docs/plans/M35_URIV1_A2_8L_TELEMETRY.json`
6. `docs/plans/M35_URIV1_A2_8L_AGGREGATES.json`
7. `docs/plans/M35_URIV1_A2_8L_EXECUTION_REPORT.md`
8. `docs/plans/M35_URIV1_A2_8L_STATE.md`

The only files created at planning freeze are this plan and the overlay
manifest required by the A8 checkpoint (§5.4):
`docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`. No mechanism code, fixture
module, script, or test file from the list above is created at freeze.

### 13.2 Protected files

No implementation may modify:

- `uri_v1/turn/rar_contracts.py`
- `uri_v1/turn/rar_deterministic.py`
- `uri_v1/turn/rar_safe_experimental.py`
- `uri_v1/turn/rar_l5_experimental.py`
- `uri_v1/turn/rar_l5_diagnostic_fixtures.py`
- `scripts/m35_a2_8h_detector_d1rq.py`
- `scripts/m35_a2_8k_l5_battery.py`
- `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json`
- any A2.8J, A2.8K, or A2.9 evidence artifact
- production call sites or governance files

### 13.3 Explicitly out of scope

- production integration, promotion, recency wiring, or contract migration;
- a new RAR contract field;
- any model/AI component;
- D1RQ, Level 6, relative-anchor/session tracking, stemming, aliases,
  abbreviation normalization, S1/S2 redesign, New F, or S3 promotion;
- reinterpretation of accepted A2.8K/A2.9 evidence;
- commit or push.

---

## 14. Binding execution order if later authorized

0. Confirm the A8 freeze checkpoint (§5.4) holds: plan hash and overlay
   manifest hash both recorded in the A2.8L state file. Do not proceed past
   this step until confirmed.
1. Verify branch/HEAD and protected hashes.
2. Author and hash the overlay/fixture manifest before resolver code.
3. Implement flag-off experimental wrapper and prove full equivalence.
4. Implement the six independent factors without case-specific logic.
5. Run unit/mechanism tests before the battery.
6. Run the complete factorial twice and reconcile raw/aggregate decisions.
7. Derive minimal sufficient sets and pre-registered interactions.
8. Run the two transport arms only for the bounded cell set in §4.2.
9. Run confirmation/regression surfaces.
10. Run the separate performance protocol.
11. Write telemetry, aggregates, report, and state; stop at
    `VERIFICATION_READY` for independent audit.

No adaptive fixture change, factor redesign, threshold change, or vocabulary
addition is permitted after step 2. Any required change reopens planning and
invalidates measurements already taken.

---

## 15. Freeze decision

Repository evidence resolves the material semantics needed for this plan:
A2.8K Q1–Q4 already froze generic ambiguity, trustworthy-vs-untrustworthy
order, relative-anchor deferral, and H3's lexical-domain boundary. No new User
semantic choice is required.

This plan was amended under accepted planning review findings A1–A8 (see
"Amendment history" after §0) and cross-checked against
`docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`, which satisfies the A8
freeze checkpoint (§5.4): every overlay record is enumerated and hashed
against verified repository evidence, and no mechanism code exists. The
internal-consistency check covered plan arithmetic (§4.3), the factor matrix
(§4.1), case counts (§5.1–§5.2), the compiler rules (§4.2.1), the hypotheses
(§6), and the acceptance criteria (§9); the corrections found (A5, A6) were
applied directly rather than deferred.

**Unresolved ambiguity:** none material to freezing the plan. The only
disclosed open item is the A7 truncation risk (3+-member ordinal
generalization is untested by design, not an oversight) and the A5 Case-A
authored-only external-validity limitation; both are scope disclosures, not
blockers, and do not require a User decision to freeze.

**Recommendation:** run A2.8L only if separately authorized. It is the smallest
direct follow-up that can separate membership, grouping, provenance, domain,
rank frame, and precedence while testing—rather than assuming—the need for a
new transport contract.

`FROZEN_READY_FOR_IMPLEMENTATION`

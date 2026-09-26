# M33.3 — S1 State: Reference-Clarification Deterministic Core (frozen scope)

**Current state:** `S1_IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT`
**State history:** S1 `BLOCKED` pending RG-0R (`docs/plans/M33_3_CROSS_PLAN_STATE.md` §4) → RG-0R `RG_0R_ACCEPTED` → S1 pre-implementation scoping audit `S1_SCOPE_READY_WITH_BOUNDED_FOLLOWUP` → bounded governance follow-up (this file, Plan A R4) → `S1_SCOPE_READY_FOR_IMPLEMENTATION_REVIEW` → S1 fidelity self-audit `S1_FIDELITY_AUDIT_ACCEPTED_WITH_BOUNDED_FOLLOWUP` → docs-only repair of follow-ups F-U1 to F-U4 (2026-09-26; state unchanged: `S1_SCOPE_READY_FOR_IMPLEMENTATION_REVIEW`).
**Implementation authorized:** **YES, S1 only**, by the User's S1 implementation task package at starting HEAD `ad9e2a6fef7b12c4aa4ecfde93fa06d397de7682` (2026-09-26). No later slice is authorized.
**Workstream identity:** `URI-REFERENCE-CLARIFICATION` (planning identity; the bare alias "ARN" stays forbidden).
**Branch / baseline:** `m35-uri-v1-parallel-architecture` @ `94ccf2ab24414007feccbcf2c5c903f8755621ec`.
**Date:** 2026-09-26

**Sources.**
- Plan A: `docs/plans/M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md`, revisions R2, R3, R4 (R4 carries D5, D6, F-1 to F-6).
- Cross-plan state: `docs/plans/M33_3_CROSS_PLAN_STATE.md` (D1–D6, slices, gates).
- RG-0R record: `docs/plans/M33_3_RG0R_FOCUSED_INDEPENDENT_REAUDIT_REPORT.md`.
- The S1 scoping audit report is not stored in the repository. Its verdict, decisions, and findings reached this pass through the User's instruction. The findings were re-verified against source (Plan A R4.1). Everything else in this file is derived from the accepted Plan A text and repository evidence; where this file makes an interpretive choice, it says so.

---

## 1. Purpose and boundary

S1 builds the deterministic reference-clarification and binding core in `uri_v1`, exercised against fixtures only. It turns a deterministic RAR result into a binding state or a validated clarification, and validates user responses back into bindings. It calls no model, no router, no provider, and no `uri_core` code. It persists nothing beyond process memory.

S1 is the **full** state-file S1 (D6). It is not split into S1 and S1b.

## 2. User decisions

- **D5 — CONFIRMED authority.** Only certainty-tier deterministic rules may produce `CONFIRMED`: `EXACT_ID`; `EXACT_ALIAS`; `ACTIVE_UI`; `CURRENT_ATTACHMENT` only when tied to `deterministic_anchor.current_attachment_id`; `EXACT_TITLE` only when tied to `deterministic_anchor.unique_title_match` or an equivalent unique verbatim-title anchor. Other deterministic `RESOLVED` rules are only TENTATIVE-eligible through the R2.9 check. `CONSEQUENTIAL` or undeclared `wrong_binding_impact` → `CONFIRM_ONE`. The same classification applies to typed free input. The classifier lives outside frozen RAR/A9. Operational table: Plan A R4.2.
- **D6 — S1 boundary.** S1 = deterministic clarification/binding core + deterministic template + RenderValidator + `ClarificationBundle` / multi-reference contract. No S1/S1b split.
- **Free input with display overflow (User decision, 2026-09-26; follow-up F-U3).** Free input reruns over the full ambiguity scope RAR returned for that round, including candidates hidden only by the display cap. The display cap is a presentation constraint, not a reduction of binding scope. URI never reconstructs candidates frozen RAR omitted or truncated. Operational text: Plan A R4.12.
- D1–D4 stand unchanged (`docs/plans/M33_3_CROSS_PLAN_STATE.md` §2).

## 3. Evidence findings (re-verified; detail and line citations in Plan A R4.1)

| ID | Finding | S1 consequence |
|---|---|---|
| F-1 | Frozen RAR sets `basis=DETERMINISTIC_ANCHOR` on every outcome, including heuristic rules. | Authority comes from `rule_used` + anchor provenance (R4.2), never from `basis`. |
| F-2 | Several RAR ambiguity paths truncate `ambiguous_candidate_ids` to two. | S1 uses the returned set exactly; never reconstructs omitted survivors; never modifies RAR. |
| F-3 | Deterministic RAR never reads `RAREvidence.clause_text`. | Free-input re-resolution uses the typed text as the fresh `RARQuery.reference_expression`. |
| F-4 | `RARCandidate` grounds only `title`, `type`, `owner`, `recency` as attribute axes. | Other axes stay unavailable in S1 (need S4 producers). |
| F-5 | `uri_v1` has zero imports from `uri_core`. | ARN.1 narrowing semantics are ported into S1; parity tests live under `tests/`. |
| F-6 | RAR exact-ID/alias runs before `ACTIVE_UI`. | BindingService confirms a click only if the re-run returns the clicked candidate via `ACTIVE_UI`; otherwise fails closed. |

## 4. Responsibilities

### 4.1 IN (S1 implements)

1. Contract types and deterministic validation: `ClarificationKind` (`CHOOSE_ONE`, `CONFIRM_ONE`, `CHOOSE_ATTRIBUTE`, `FREE_INPUT_ONLY`), `CandidateFact`, `ClarificationCandidate`, `ClarificationContract` (with R3.1 attribute fields), `ClarificationOptionKind`, `AttributeOption`, `ReferenceSlot`, `ClarificationBundle`, response payloads (`CANDIDATE`, `ATTRIBUTE`, `FREE_INPUT`), binding-state enum, and an S1-local `wrong_binding_impact` value type (`NONE` / `RECOVERABLE` / `CONSEQUENTIAL`; undeclared → `CONSEQUENTIAL`).
2. The D5 binding-authority classifier (Plan A R4.2), pure and outside frozen RAR.
3. The contract builder and trigger (Plan A R4.3, replacing R2.3's table): top-N ordering in RAR order, cap 5, `overflow_count` over the returned set only, contrast exclusions, near-identical handling (§4.2). The builder keeps two distinct sets (Plan A R4.12): the **displayed option set** (`candidates`, at most 5) and the **round ambiguity scope** (`scope_candidate_ids`, exactly the IDs RAR returned for the round, including candidates hidden by the cap). `candidate_set_fingerprint` covers every round-scope candidate, displayed or hidden (existing R3.1 rule).
4. `CHOOSE_ATTRIBUTE` axis selection and clue narrowing over `title` / `type` / `owner` / `recency` only, as a port of ARN.1 semantics (R3.1 A, R4.6).
5. The deterministic R2.9 TENTATIVE eligibility check.
6. The session-evidence adjunct (R2.1): session-local, in-memory, display reorder/annotation among RAR ties, and R2.9(c) input only.
7. The deterministic template for every kind, including `CHOOSE_ATTRIBUTE` and overflow suffix (§6, R3.1 B).
8. The RenderValidator: all V-* checks of §6 plus the R3.1 B `a*` namespace rules. It validates any supplied render output (template or canned), so L2 adversarial tests need no model.
9. BindingService: R3.1 D response validation; R3.2 admissible source states and rebind checks 1–7; fingerprint freshness; expiry; replay rejection; the R4.4 `ACTIVE_UI` re-run check; R4.5 free-input re-resolution over the round ambiguity scope (R4.12), never beyond it and never reconstructing RAR-omitted candidates; the per-candidate freshness check on any candidate free input resolves to.
10. The lifecycle state machine (§6 below).
11. The bundle contract (R2.11): validation (targets exist, no cycles, pending-parent slots hidden), `COMBINED` / `SEQUENTIAL` presentation, per-slot binding, dependent-slot rebuild from a caller-supplied fresh `RARQuery`.
12. Stop safeguards (R1.8): progress-based round limit and per-turn budget counters. Limit values are parameters; no value is frozen (values are [EXPERIMENT]).

### 4.2 BOUNDARY-ONLY (S1 defines an input or port; the owner is elsewhere)

| Boundary | S1 side | Owner |
|---|---|---|
| `wrong_binding_impact` of the proposed action | supplied as an input value; undeclared → `CONSEQUENTIAL` | S2 (`Action` field, execution gate) |
| Execution outcome of an action (`APPLIED` / `TENTATIVE_APPLIED`) | an injected event driving the state machine | S2 / S13 |
| Fresh redo authorization (execution policy, impact gate, approval for Y's arguments) | an injected decision; S1 never grants it and never reuses X's approval | S2 / `uri_core` approval gate / S13 |
| Edited-result status of the X-derived result | an injected value `UNEDITED` / `EDITED` / `UNKNOWN` | S11 |
| Candidate facts beyond `RARCandidate` fields, `fact_sources`, `depends_on` provenance | taken from fixtures; empty when absent | S4 evidence producer |
| Deterministic RAR | called read-only via `resolve_rar_deterministic_extended` | frozen RAR (A9) |

### 4.3 DEFERRED (explicitly not in S1)

| Item | Slice / owner |
|---|---|
| `Action.wrong_binding_impact` production field and execution-gate check | S2 |
| Formal frozen L1/L2 battery, manifest, hash anchor | S3 |
| Source-to-candidate producer, evidence envelope, pre-ask investigation (R2.8), axes `modified` / `version` / `sender` / `thread_subject` / `locator` | S4 |
| Model wording tiers, renderer port and adapters, need-class policy, wording qualification | S5 (and P3/P4) |
| Unified router consultation | S6 |
| Response `trace_id` and the structured evaluation event stream (R2.12) | S7 |
| Model interpretation of free input into `(axis, value)` (R3.1 F.2, D3) | after S4/S5; not S1 |
| Durable reference evidence and learned tie-breaking | S9 / URI-Memory (D4) |
| Result versioning and the `VERSIONED` state | S11 |
| Clickable options in `uri_ui` | S12 |
| `uri_core` integration, `turn_state` projection, real session persistence | S13 (needs INT authorization) |
| Graphify use | not used by S1 |

## 5. Ownership map

| Concern | Owner |
|---|---|
| Candidate identity, IDs, rank, outcome | frozen RAR (read-only) |
| Authority class (`CERTAINTY` / `HEURISTIC`) | S1 D5 classifier |
| Binding state and transitions | S1 BindingService + state machine |
| TENTATIVE eligibility | S1 R2.9 check |
| Display order, cap, overflow, attribute split | S1 builder (RAR order preserved) |
| Wording | S1 template (only tier in S1); validated by S1 RenderValidator |
| Execution, approval, impact declaration | outside S1 (injected; §4.2) |
| Implementation routing | decided at authorization under AO-4 (multi-file, authority-sensitive work routes to Codex). Not decided here. |

## 6. State-machine boundary

S1 implements the Plan A R3.2 machine per `ambiguity_id`, with R4.4/R4.5 authority rules:

- **Owned states:** `PENDING`, `TENTATIVE`, `CONFIRMED`, `REJECTED`, `EXPIRED`, `CHANGE_PENDING`, `REBIND_CHECK`, `CHANGE_ABANDONED`, `REDO_AUTHORIZED`, `REDO_NOT_EXECUTED`.
- **Externally driven transitions:** `APPLIED`, `TENTATIVE_APPLIED`, and `REDONE` are entered only on an injected execution event. `REDO_AUTHORIZED` is entered only on an injected positive authorization decision for `CONFIRMED(Y)` from a Change round (I-1, I-5).
- **Not reachable in S1:** `VERSIONED` (needs S11).
- **I-6 fail-closed representation (interpretive choice, subject to implementation review):** if the injected edited-result status is `EDITED` or `UNKNOWN`, S1 never enters `REDO_AUTHORIZED`; it records `REDO_NOT_EXECUTED` with the reason "result-version owner (S11) required". Only `UNEDITED` can proceed.
- A contract accepts at most one successful response. Replays are rejected.
- **Attribute-narrowed results never confirm directly (Plan A R3.1 E; follow-up F-U1).** A result reached through `CHOOSE_ATTRIBUTE` / attribute narrowing never directly produces `CONFIRMED`, even when the fresh RAR rerun returns a certainty-tier rule (R4.2 `CERTAINTY`). After attribute narrowing:
  - multiple candidates → another clarification round;
  - one candidate, R2.9 check passes, impact `NONE` / `RECOVERABLE` → `TENTATIVE`;
  - one candidate where R2.9 does not permit `TENTATIVE`, or RAR returns `UNKNOWN` → `CONFIRM_ONE`;
  - never `CONFIRMED` directly. `CONFIRMED` is reachable afterwards only through an explicit `CONFIRM_ONE` confirmation or a candidate click (R4.4).

## 7. Persistence boundary

In-memory only. Pending contracts, session evidence, and state live in process objects for the life of the test/session object. No file, database, `turn_state`, ExperienceStore, or cross-session write. Binding records hold `candidate_id` and fingerprints, not display text.

## 8. Test battery (unit tests under `tests/`; no model, no network)

1. Contract validation: every kind's counts, ID membership, uniqueness, contiguous ranks, contrast exclusion, `a*` / `s*` namespaces, no mixed option kinds.
2. D5 classifier: one case per R4.2 row, including `CURRENT_ATTACHMENT` via the Level 5.5 inference → `HEURISTIC`; `EXACT_TITLE` anchor, verbatim Level 2, and stem-only Level 2; every heuristic rule; unknown rule → `HEURISTIC`; `MODEL_SELECTION` never `CERTAINTY`.
3. Negative regression for F-1: a heuristic `RESOLVED` with `basis=DETERMINISTIC_ANCHOR` and `CONSEQUENTIAL` or undeclared impact yields `CONFIRM_ONE`, never `CONFIRMED`.
4. F-2: a truncated two-candidate ambiguity produces a contract over exactly those two; no survivor is re-added; `overflow_count` is 0.
5. F-3: free input re-resolves with the text as `reference_expression`; a text-in-`clause_text`-only construction is not used.
6. F-4: axis selection never chooses an axis outside `title` / `type` / `owner` / `recency`; `owner = None` disqualifies `owner`.
7. F-5 parity: tests import both `uri_core.core.arn` and the S1 port, and compare clue elimination and axis recommendation on shared cases. A structural test asserts that no new `uri_v1` module imports `uri_core`.
8. F-6: a click where the re-run returns `EXACT_ID` / `EXACT_ALIAS` (same or other candidate) is `REJECTED`; only `ACTIVE_UI` + same candidate binds.
9. R2.9 check: passes and failures for each clause (a)–(d).
10. Template: output passes the RenderValidator for every contract the tests build (FROZEN_REQUIRED intent of §11).
11. RenderValidator adversarial: each V-* check rejects a canned bad output.
12. BindingService: R3.1 D steps 1–6, R3.2 admissible-state table, rebind checks 1–7, expiry, stale fingerprint, replay.
13. Lifecycle: every R3.2 edge; I-1 to I-6; `CHANGE_ABANDONED` on Y = X; heuristic free input in a Change round yields `CONFIRM_ONE`, not `TENTATIVE`; `REDO_NOT_EXECUTED` on declined authorization and on `EDITED` / `UNKNOWN`.
14. Bundle: combined vs sequential, cycle rejection, hidden pending parents, dependent-slot rebuild.
15. Stop safeguards: no-progress stop; budget exhaustion; a new clue counts toward budget, not the round limit.
16. Edge independence: S1 imports no model, provider, router, or Edge module.
17. Protected-hash test: the §13 RAR/A9 hashes are unchanged before and after the test run.
18. F-U1 (R3.1 E): attribute narrowing whose fresh RAR rerun returns a certainty-tier result (for example, a Level 2 verbatim `EXACT_TITLE` that becomes unique only after narrowing) is **not** `CONFIRMED`; it yields `TENTATIVE` (R2.9 passes, impact `NONE` / `RECOVERABLE`) or `CONFIRM_ONE`. Also: multiple remaining → new round; `UNKNOWN` with one remaining → `CONFIRM_ONE`.
19. F-U3 (R4.12): a `CHOOSE_ONE` round with more than 5 RAR-returned candidates displays 5 plus overflow; free input naming a hidden candidate re-resolves within the round scope; free input never resolves to a candidate outside the RAR-returned scope; a truncated RAR set is not re-expanded; `candidate_set_fingerprint` changes when a hidden scope candidate's fingerprint changes; a stale candidate reached by free input is `REJECTED`.

## 9. Proposed file-impact map (proposed; confirmed at authorization)

**New (production, `uri_v1`):**
- `uri_v1/turn/rar_clarification_contract.py` — contracts, validation, D5 classifier, builder/trigger.
- `uri_v1/reference_clarification/` package — `attribute_narrowing.py` (ARN.1 port), `tentative_check.py`, `session_adjunct.py`, `template_renderer.py`, `render_validator.py`, `binding.py` (BindingService + state machine), `bundle.py`, `safeguards.py`.
  The package name follows the registered identity `URI-REFERENCE-CLARIFICATION` instead of Plan A §15's pre-identity `uri_v1/arn_clarification/`.

**New (tests):** `tests/test_m33_3_s1_*.py` (contracts, classifier, builder, attribute parity, validator, template, binding, lifecycle, bundle, safeguards, boundary/hash).

**Modified at S1 closure only (governance):** this file, `docs/plans/M33_3_CROSS_PLAN_STATE.md`, `docs/governance/URI_STATE.yaml`.

**Never modified by S1:** `uri_v1/turn/rar_deterministic.py`, `uri_v1/turn/rar_contracts.py`, `uri_core/**`, `fixtures/m33_3_batch_a/**`, `uri_ui/**`.

## 10. Implementation order

1. Contracts and validation.
2. D5 classifier.
3. Builder and trigger (R4.3).
4. Attribute narrowing port + parity tests.
5. Template + RenderValidator (+ template-passes-validator test).
6. Session adjunct + R2.9 check.
7. BindingService (response validation, `ACTIVE_UI` re-run check, free input).
8. Lifecycle state machine including Change round.
9. Bundle contract.
10. Stop safeguards.
11. Boundary, import, and protected-hash tests; full run.
12. Independent audit, then Claude final audit and release per AO-4.

## 11. Stop conditions (halt and return to Claude/User)

- Any need to modify `rar_deterministic.py`, `rar_contracts.py`, `uri_core/**`, frozen fixtures, or `uri_ui/**`.
- Any protected hash mismatch (§13).
- Any need to import `uri_core` from `uri_v1`.
- Any need for an axis outside F-4, or to reconstruct truncated RAR survivors.
- Any model, provider, router, network, or Graphify call.
- Any durable persistence.
- Any path where a `HEURISTIC` result would become `CONFIRMED`, or a click would bind without the R4.4 check.
- Any work belonging to a deferred slice (§4.3).
- Any new product or authority decision not covered by D1–D6.

## 12. Items for the implementation-authorization review (non-blocking)

1. `EXACT_TITLE` stem-only Level 2 treated as `HEURISTIC` (Plan A R4.11 item 1).
2. The I-6 fail-closed representation in §6.
3. R4 fidelity (Plan A R4.11 item 2).
4. The proposed package name in §9.

## 13. Protected hash anchors (verified 2026-09-26, before this pass)

| Artifact | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` (A9-protected) | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `fixtures/m33_3_batch_a/battery.json` (LF-normalized, frozen) | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` |

Parity reference (informational, not protected by this file): `uri_core/core/arn/models.py` `e462ff0edc21f59f401932f8a40425dd36546b6bbd10c59f0769a8eb0f04d609`; `uri_core/core/arn/engine.py` `a350d6d3dcb36d4f4b6b47fc2ef799a70a131691e33d3106ee6097409db57879`.

## 14. Authorization state

- `S1_SCOPE`: frozen and unchanged.
- `CODE_IMPLEMENTATION_AUTHORIZED: YES — S1 ONLY` (User task package, 2026-09-26).
- `S1_IMPLEMENTATION_AUTHORIZED: YES` (same package).
- `S1_IMPLEMENTATION_STATE: IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT` (evidence: `docs/plans/M33_3_S1_IMPLEMENTATION_REPORT.md`). This is not an independent acceptance or full M33.3 closure.
- S2–S13 remain unauthorized. No `INT-*` event. `URI-RAR` not adopted.

# M35 URIv1 — A2.8L Overlay Manifest (FREEZE CHECKPOINT)

**Status:** `FROZEN — MANIFEST ONLY — NO MECHANISM CODE` (A1–A8: `804d68e`, historical); amended by plan §16 (A9) — case-row annotations below record the A9-1/A9-2/A9-3/A9-5 amendments that apply to each affected row; no overlay field value is changed
**Date:** 2026-09-24
**Branch:** `m35-uri-v1-parallel-architecture`
**Governs:** `docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md`
(A8 freeze checkpoint, §5.4)

This manifest enumerates every overlay record required by A2.8L §5.1–§5.2. It
records no executable mechanism code. All field values below are transcribed
verbatim from the frozen plan; this manifest and the plan must remain in
agreement. Any later change to either file invalidates all A2.8L results and
reopens the plan.

---

## 1. New overlay records (authored, defined at planning time)

### 1.1 `A2L-OV-01` — `A-LATEST-DISTRACTOR`

| Field | Value |
|---|---|
| Reference | `the latest attachment`; `recency_hint=latest`; no type hint |
| Candidates | `a2l-ad-old` / `Draft_Old.pdf` / rank 2 / attachment; `a2l-ad-new` / `Draft_New.pdf` / rank 1 / attachment; `a2l-ad-distractor` / `Unrelated_Newer.pdf` / rank 0 / attachment |
| Current-turn membership | `{a2l-ad-old, a2l-ad-new}` |
| Event groups | `a2l-ad-old -> event-0`; `a2l-ad-new -> event-1`; distractor has no current-turn event |
| Group ordinal | `event-0=0`, `event-1=1` |
| Provenance | `CURRENT_TURN_ATTACHMENT_SEQUENCE` |
| Expected | `RESOLVED -> a2l-ad-new` |
| Used by | §5.1 causal target `A-LATEST-DISTRACTOR` |

### 1.2 `A2L-OV-02` — `B-LATEST-PROVENANCE-TWIN`

| Field | Value |
|---|---|
| Base fixture | `SD-A-04` (candidates/query unchanged) |
| Membership | `{sd-a4-old, sd-a4-new}` |
| Event groups | `sd-a4-old -> event-0`; `sd-a4-new -> event-1` |
| Group ordinal | `0, 1` |
| Supplied candidate ranks | `sd-a4-new=0`, `sd-a4-old=1` |
| Provenance | `UNKNOWN` (only field that differs from `A-LATEST-2`) |
| Expected | `AMBIGUOUS` over `{sd-a4-new, sd-a4-old}` |
| Used by | §5.1 causal target `B-LATEST-PROVENANCE-TWIN`; must be byte-identical to `A2L-OV-03` (`A-LATEST-2`) after removing provenance and expected-outcome fields; abstention requires R's domain-wide tie per plan §16.1 A9-5 (its two members are in distinct event groups, so a same-event-only tie would not abstain here — only P's failure does) |

---

## 2. Reused overlay records (attach overlay facts to existing frozen fixtures)

| Manifest id | Case id | Source fixture | Membership | Event relation | Provenance | Used by |
|---|---|---|---|---|---|---|
| `A2L-OV-03` | `A-LATEST-2` | `SD-A-04` | both fixture ids | distinct ordered events, old then new | `CURRENT_TURN_ATTACHMENT_SEQUENCE` | §5.1 |
| `A2L-OV-04` | `A-FIRST-2` | `SD-A-06` | both fixture ids | distinct ordered events, early then late | `CURRENT_TURN_ATTACHMENT_SEQUENCE` | §5.1 — `SD-A-06`'s `recency_hint` is `"earlier"`; A3 trigger match per plan §16.1 A9-3 (frozen hint set includes `"earlier"`) |
| `A2L-OV-05` | `B-LATEST-WRONG-CLOCK` | `SD-A-05` | both fixture ids | one shared event (tie) | `HISTORICAL_OBJECT_CREATED_AT` | §5.1 |
| `A2L-OV-06` | `B-FIRST-WRONG-CLOCK` | `SD-A-07` | both fixture ids | one shared event (tie) | `HISTORICAL_OBJECT_CREATED_AT` | §5.1 |
| `A2L-OV-07` | `B-DISTRACTOR` | `NB-C-05` C1/C2 (natural) | exactly the two corpus `turn_attachments` ids | one shared re-attachment event (tie); C2 distractor has no current-turn event | `HISTORICAL_OBJECT_CREATED_AT` | §5.1 — per plan §16.1 A9-2, reachable only via the D/M-to-Level-5.5 extension (no ordinal wording, A3 never fires) |
| `A2L-OV-08` | `C-GENERIC-2` | `SD-A-02` | both fixture ids | generic wording control, no ordinal | n/a (no explicit ordinal trigger) | §5.2 |
| `A2L-OV-09` | `C-NATURAL-PHOTOS` | `NB-C-04` C1/C2 (natural) | exactly the two corpus `turn_attachments` ids | one shared attachment event; C2 pool condition adds optional non-turn distractor | `HISTORICAL_OBJECT_CREATED_AT` (control only, not a causal A/B target per A5) | §5.2 — produces 2 rows (C1, C2); C2's distractor exclusion per plan §16.1 A9-2 is via the D/M-to-Level-5.5 extension |
| `A2L-OV-10` | `C-LEXICAL-ATTACHMENT` | `SD-A-08` | n/a — lexical distinction, not order | n/a | n/a | §5.2 — per plan §16.1 A9-1, excluded from the §7 qualification gate (`reachable_by_factors: false`); still scored/reported every cell |
| `A2L-OV-11` | `C-DOMAIN-RANK-SYNTH` | `SD-C-02` | n/a — non-attachment domain | n/a | n/a | §5.2 |
| `A2L-OV-12` | `C-DOMAIN-RANK-NATURAL` | `NB-D-01` C2 (natural) | n/a — non-attachment domain | n/a | n/a | §5.2 |
| `A2L-OV-13` | `C-NO-RANK0` | `test_rc1_current_conflicting_no_rank0_abstains` shape | n/a — must not resolve | n/a | n/a | §5.2 |

Total manifest entries: **13** (2 new + 11 reused), governing **13 case
templates / 14 decision rows** per §4.3 (A6-corrected arithmetic).

---

## 3. Freeze checkpoint — protected and reference file hashes (SHA-256)

Computed directly from repository state at freeze time (not asserted from
memory):

| File | SHA-256 |
|---|---|
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_safe_experimental.py` | `4d9317311bdda0eaabc4ff5277bd3ac8b7628d83871dbd2da607954d946032a5` |
| `uri_v1/turn/rar_l5_experimental.py` | `8e95774420a6d5f165dc7163e8085e92d3f64ed5c32856579674614af7d342b5` |
| `uri_v1/turn/rar_l5_diagnostic_fixtures.py` (S-D battery) | `ce25cd76c1652284145dc95c3d3037c6e784fe51f92a97ace6e67e7fdf371148` |
| `scripts/m35_a2_8h_detector_d1rq.py` | `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82` |
| `scripts/m35_a2_8k_l5_battery.py` | `62b7229ce7576ac4d666bc0c1de68937f9c2e72f1a7ef5f570c43ced83cbf0f7` |
| `uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json` (natural corpus) | `0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380` |
| `docs/plans/M35_URIV1_A2_8K_R2_TELEMETRY.json` (A2.8K R2 evidence) | `9f40f53a945920c4661080dbf9008ba9e121f166452190b7acc4c9513817e183` |
| `docs/plans/M35_URIV1_A2_8K_R2_AGGREGATES.json` (A2.8K R2 evidence) | `f1be0393da2390d599fc8dd9306e080887be6d79375a00e912b084a33874d6da` |

The plan file's own hash and this manifest's own hash are not embedded here
(a file cannot hash itself without circularity); they are fixed by the git
blob objects created in the freeze commit and are reported alongside the
commit hash, per the A8 checkpoint (plan §5.4).

Any mismatch between these recorded hashes and the repository at
implementation time means A2.8L's evidence baseline has drifted; the plan
must be reopened before mechanism code is written.

---

## 4. Verification note

- No mechanism code, fixture module (`.py`), script, or test file listed in
  plan §13.1 exists as a result of this manifest.
- This manifest and the plan's §5.1/§5.2 overlay-fact tables were checked for
  agreement during this freeze pass; no discrepancy was found beyond the
  corrections already applied to the plan under amendments A5/A6.
- Independent-auditor reproduction of these ten hashes (§3) is required
  before implementation, per plan §11.

---

## 5. A9 checkpoint (post-audit amendment, pre-rerun freeze)

- The ten §3 protected/reference-file hashes are unaffected by A9 — no
  mechanism code exists and none was touched by this amendment pass. They
  remain valid and do not need to be recomputed for this checkpoint.
- The five row annotations added above (§1.2, §2 `A2L-OV-04/07/09/10`)
  record which plan §16.1 amendment (A9-1, A9-2, A9-3, or A9-5) applies to
  that case; no overlay field value (membership, event group, ordinal,
  provenance, or expected outcome) was changed by any annotation.
- This manifest's own hash and the amended plan's own hash are fixed by the
  git blob objects created in the A9 freeze commit, per the same convention
  §3 uses for the original A8 checkpoint (a file cannot hash itself without
  circularity); both are reported alongside the A9 commit hash.
- A9-4 (H3 as an always-on substrate) and A9-5 (R's domain-wide tie) do not
  change any manifest row's overlay facts — they are resolver-behavior
  amendments (plan §16.1), not case/fixture amendments — so no additional
  manifest row annotation is required for them beyond the `B-LATEST-
  PROVENANCE-TWIN` note above (§1.2), which documents why A9-5 matters for
  that specific case's expected abstention.

---

## 6. R2 governance correction (dated note, §5 wording preserved unedited above)

**Date:** 2026-09-24 (A2.8L-A9-R2, authorized as a bounded, report/governance-
only correction; §5's original text above is left unedited so the freeze
history stays auditable, per this repository's Evidence Integrity Rules —
this section adds a correction, it does not overwrite or delete §5).

**§5 correction (post-A9-R1 re-audit):** the A2.8L mechanism and fixture
modules already existed, untracked, in the working tree at the A9 freeze.
Neither they nor any §3 file was modified by the A9 amendment pass. The §3
hashes remain valid.

This corrects §5's first bullet, which stated "no mechanism code exists" —
that clause was already false at the moment §5 was written (the mechanism
module `uri_v1/turn/rar_attachment_order_experimental.py` and fixture
module `uri_v1/turn/rar_attachment_order_factorial_fixtures.py` were
created during the original A1–A8 implementation pass, `804d68e`, well
before the A9 amendment pass this manifest's §5 documents). §5's
substantive claim — that A9 itself touched no mechanism code and that the
§3 hashes are unaffected — remains true and is not disputed by this note;
only the "no mechanism code exists" clause was inaccurate as a statement
about repository state at the time A9 was written. Identified by the
independent audit of A2.8L-A9 (`docs/plans/M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md`
§1) and confirmed by the A9-R1 independent re-audit
(`docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md` §12,
disposition `NON_BLOCKING_GOVERNANCE_DOC_CORRECTION`); corrected here under
the R2-9 bounded governance-correction authorization
(`docs/plans/M35_URIV1_A2_8L_A9_R2_TELEMETRY.json` records the R2 evidence
round this correction accompanies). No overlay field value, hash, or
mechanism/fixture file is changed by this note.

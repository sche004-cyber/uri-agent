# M35 URIv1 — A2.8L-A9 Closure Report

**A2.8L-A9 = CLOSED**
**Verdict:** `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`
**Date:** 2026-09-24
**Closed by:** Claude Code (Sonnet 5), acting under standing release
authority (AO-4 governance) after the release authority/user supplied the
final independent re-audit externally (see
`docs/plans/M35_URIV1_A2_8L_A9_R2_INDEPENDENT_REAUDIT_REPORT.md` §0 for
provenance) and this agent independently reconciled its material claims
against live repository evidence (same report, §10).

---

## 1. Lineage

`591f806` (A9 freeze, plan/manifest) -> A9 rerun (`REPAIR_REQUIRED`) ->
A9-R1 repair (implementer self-report
`docs/plans/M35_URIV1_A2_8L_A9_R1_REPAIR_REPORT.md`) -> A9-R1 independent
re-audit (`docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md`,
verdict `REPAIR_REQUIRED`) -> A9-R2 bounded correction (implementer
self-report `docs/plans/M35_URIV1_A2_8L_A9_R2_CORRECTION_REPORT.md`,
status `VERIFICATION_READY_FOR_REAUDIT`) -> final independent re-audit,
externally supplied and reconciled
(`docs/plans/M35_URIV1_A2_8L_A9_R2_INDEPENDENT_REAUDIT_REPORT.md`, verdict
`ACCEPT_WITH_DOCUMENTED_LIMITATIONS`) -> **this closure record**.

## 2. Frozen Evidence Hashes (verified, full values)

| File | SHA-256 (full) |
|---|---|
| `uri_v1/turn/rar_attachment_order_experimental.py` | `90d89c372e7618f3476719ed1acebcb81cdb0907b4723b695ec6d4a4f289f79c` |
| `uri_v1/turn/rar_attachment_order_factorial_fixtures.py` | `3657070635827bf9850d11aafe7cdd0c47bd7c7c7747025de6cb17227566315a` |

Both identical to A9-R1 and to the A9-R2 correction round. The eight
protected files and two A2.8K reference artifacts listed in
`M35_URIV1_A2_8L_OVERLAY_MANIFEST.md` §3 were independently re-hashed
during closure and remain byte-identical to the manifest.

## 3. Qualified Factorial Result

- **Qualifying cell:** `M1G1P1D1R1Q0` — the only cell of 64 at which all
  reachable Case-A/B/C targets pass (`C-LEXICAL-ATTACHMENT` excluded as
  unreachable, per A9-1).
- **Necessary factors:** M, G, P, D, R (Q must be 0). No single factor is
  sufficient alone.

## 4. Transport Conclusion

`EXISTING_CONTRACT_COMPILATION_INSUFFICIENT` — scoped exactly to the
tested §4.2.1 compiler algorithm under factor-state parity. **This is not
a claim that the RAR contract cannot represent ties**; a densified rank or
an all-equal `recency_rank` both fit the existing `recency_rank` int
field. The limitation is in the tested compiler algorithm's step-4
branching, which never emits either form.

`NEW_CONTRACT_FIELD_REQUIRED = NOT_ESTABLISHED`.

Transport mismatch total: 88/196, attributed without remainder across six
buckets (H3 absence 28, compiler step-4 unsafe bind 30, Level-5.5
extension not compiled 16, M/D-gated no R event fallback 4, sidecar
gate-abstains-compiler-correct 8, rank not densified without R 2).

## 5. Interaction Findings

- M×D is an unconditional two-factor interaction for `B-DISTRACTOR` and
  `C-NATURAL-PHOTOS-C2` (passes only at M=1,D=1, on any background).
- G×P meets the interacting-pair test for the three Case-A targets
  (`A-LATEST-2`, `A-FIRST-2`, `A-LATEST-DISTRACTOR`) **only on the
  qualifying-cell background where R=1**; this is a gate-induced effect of
  R's domain-wide tie construction, not an independent two-factor
  contribution from G's ordinal content or P alone. With R=0, all three
  Case-A targets pass regardless of G/P state.

## 6. ER-9

Closed. `M35_URIV1_A2_8L_OVERLAY_MANIFEST.md` §6 (additive, dated
2026-09-24) corrects §5's "no mechanism code exists" clause without
deleting or rewriting §5; the manifest's §3 hashes remain valid and
unaffected.

## 7. Reproduction / Test Evidence

- 119 tests / 178 subtests reported by the A9-R2 implementer;
  independently re-verified in this closure pass across the most
  plausible 8-module regression set, reproducing the 178-subtest figure
  exactly (127 top-level tests counted under this agent's own module
  grouping — see the independent re-audit report §10 for the disclosed,
  non-blocking module-boundary caveat on the top-level count).
- Two fresh-process causal runs, 1,792 decision rows, 0 delta from A9-R1
  — independently reproduced in this closure pass by re-running
  `scripts/m35_a2_8l_a9_r2_correction.py` fresh in-session.
- Protected/mechanism/fixture hashes verified unchanged before and after
  reproduction.

## 8. Documented Limitations (carried forward, none resolved by this closure)

1. G↔M coupling — G's event map acts as a membership signal; no frozen
   case supplies conflicting ordinal content between G and supplied ranks.
2. R↔overlay-presence coupling — R's safe-abstention activates on overlay
   presence, not cleanly separable from the frozen G+P gate sequence alone.
3. `NB-D-01` under production-shaped (non-oracle) ranks — pre-existing,
   out-of-scope limitation, identical across every cell including baseline.
4. §16.5 per-row telemetry fields (G/M separability, R overlay-vs-gate
   attribution) are not recorded directly; both conclusions are derivable
   from the raw 64-cell matrix but require cross-referencing rather than a
   dedicated field. Classification: `TELEMETRY_FORMAT_LIMITATION_NOT_EVIDENCE_GAP`.
5. `"earlier"` ref-token residual — matches a literal `"earlier"` token
   outside the frozen recency-hint set; classification
   `NON_EFFECTING_SPEC_RESIDUAL`; verified zero effect across all 14
   factorial cells and 140 (compiler)/32 (natural-surface expanded rows,
   per the disclosed R2 wording note) corpus spans; neither fixed nor
   formally frozen.
6. §16.3 item 7 — CPU measurement covers only the 6 conditions the §10.2
   threshold gate compares, a disclosed subset of the "not a subset"
   instruction; all measured CPU threshold comparisons pass; full-protocol
   CPU coverage is not established.
7. A9/A9-R1 historical runs lack complete per-run environment metadata
   (R2 onward captures it). Classification: `HISTORICAL_GAP_DISCLOSED_NOT_BACKFILLED`.
8. Performance numbers are host-specific.
9. A9-R2's `"32 spans"` wording describes expanded selected-surface rows,
   while the residual-check script scans corpus spans more broadly.
   Non-blocking.

## 9. Freeze Boundary

**A2.8L-A9 is frozen as of this closure.** No further A9 mechanism repair,
factorial expansion, compiler redesign, contract redesign, or causal
experimentation is authorized by this closure. Any future work addressing
the nine limitations above must be opened as a separately authorized
batch/experiment — this closure does not implicitly reopen A9 or
pre-authorize such work merely because limitations remain documented.

## 10. Explicit Boundaries on Claims Not Established

- `NEW_CONTRACT_FIELD_REQUIRED` is **not established** — neither proven
  nor disproven by this closure. The transport conclusion is scoped to
  the tested compiler algorithm, not the contract's representational
  capacity.
- Full-protocol CPU threshold coverage (beyond the 6 measured conditions)
  is **not established**.
- No claim is made that G's ordinal content or P contributes to Case-A
  resolution independently of the R=1 gate.

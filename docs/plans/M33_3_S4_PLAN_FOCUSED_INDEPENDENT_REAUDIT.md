# Focused Independent Re-Audit: M33.3 S4 Plan (F1/F2 Repair Verification)

**Scope:** read-only re-audit. No edits to any repo file. Verified F1/F2 repair, input allowlist, numeric budget coherence.

## Acceptance criteria
1. F1 (incomplete scorer-only field list) repaired: revised plan §1 must enumerate all eight fields matching corpus `harness_input_contract.system_under_test_must_not_receive`.
2. F2 (malformed hash) repaired: revised plan's `rar_contracts.py` hash must be 64 hex chars and match independently recomputed SHA-256 of the actual file.
3. Plan uses an input allowlist (not a blocklist-by-deletion) for producer input construction.
4. Numeric budget (candidate/byte caps) internally coherent against corpus baseline stats, with fail-closed behavior stated.

## Evidence and verdict

**F1 — REPAIRED.** Revised plan §1 (docs/plans/M33_3_S4_OFFLINE_SOURCE_TO_CANDIDATE_PLAN.md:11) lists exactly the eight fields the corpus contract names: `ground_truth_references`, `variants[].expected_*`, `variants[].acceptable_alternatives`, `variants[].intended_candidate_id`, `reason`, `category`, `secondary_signals`, `difficulty`. §3 (line 27) confirms anti-leakage focused test covers "all eight scorer-only field paths named in §1." Matches original pre-audit's required repair exactly.

**Allowlist — CONFIRMED.** §1 line 11: "Construct producer inputs by allowlisting only the three input fields [`candidate_library`, per-case `conversation_context`, C1/C2 `available_candidates`], never by copying a case or variant and deleting forbidden keys." This is a positive allowlist, structurally stronger than a blocklist — closes the F1 defect class categorically rather than just patching the enumerated list.

**F2 — REPAIRED, independently reverified.** Revised plan §1 (line 13) cites `rar_contracts.py` SHA-256 as `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` (64 hex chars). Independently recomputed via `sha256sum uri_v1/turn/rar_contracts.py` in this session: identical match. Not merely trusting the original pre-audit's recorded value — recomputed fresh, direct from the live file, in this audit.

**Numeric budget — COHERENT.** §2.5 (line 21): producer cap = 16 candidate IDs / 16,384 UTF-8 bytes of canonical source-record JSON per snapshot; frozen corpus baseline = 8 IDs / 1,972 bytes (~246 bytes/record). 16 IDs is 2x corpus max; 16,384 bytes gives ~8x headroom over a linear extrapolation (16 × 246 ≈ 3,936 bytes) — generous but not contradictory or too tight to be exercisable. Fail-closed behavior on overrun is explicitly stated ("over-budget input must fail closed rather than silently truncate a relevant candidate"), and §3 lists "budget fail-closed" as a required focused-test case. No incoherence found.

## Verdict

**ACCEPT**

Both F1 and F2 from the prior independent pre-audit are fully repaired in the revised plan text. The plan additionally adopts a positive input allowlist (stronger than the minimum repair required). The numeric telemetry budget is internally coherent with stated fail-closed behavior and corresponding focused-test coverage. No new defect surfaced during this re-audit.

## Unverifiable / out of scope
None — both items in the task scope (allowlist presence, budget coherence) were directly verifiable from the plan text and corpus baseline stats cited within it; no runtime execution was needed or in scope for this static text re-audit.

## Final plan-text check (2026-09-27)

After this focused ACCEPT, the plan's allowlist wording was corrected from three to four fields by explicitly adding `raw_user_text`, which the frozen corpus permits and the detector arms require. A separate final read-only independent check of that exact revised plan returned **ACCEPT; no blocking finding; no file edit needed**. This addendum records that later verdict without rewriting the earlier audit's historical text.

## Scorer-only amendment check (2026-09-27)

The first replay revealed that NB-A-02 and NB-A-04 contain unannotated extra referring phrases. Plan §5 changes the proposed treatment of unmatched detector spans from presumed false positives to `UNATTRIBUTED_DETECTOR_FIND` with semantic correctness `UNMEASURED`; true no-reference K cases remain false-positive controls. A separate independent, read-only focused check inspected those corpus cases and the frozen A2.8F scorer precedent, and returned **ACCEPT**. It found the change scorer-only, consistent with existing precedent, and preserving PG-5 and the annotated-wrong-binding safety gate. This check did not audit the S4 implementation.

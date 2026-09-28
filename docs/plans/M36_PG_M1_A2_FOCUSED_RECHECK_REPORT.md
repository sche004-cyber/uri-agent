**Verdict: `PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS`.** All eleven repairs R-1…R-11 are present, consistent with each other and buildable, and each has an objective Q-A2 gate. One concrete bounded defect remains in the F-1 area (N-1 below). It needs one extra rule before PG-M2 can be requested.

### Acceptance criteria (set before checking)

1. Each of R-1…R-11 is present in §17.
2. The repairs do not contradict each other or the in-place supersession notices.
3. Each repair is buildable against the frozen code.
4. Each finding has an objective Q-A2 case with a pass condition.
5. The ten safety properties in the brief hold.
6. No frozen, code or test file changed.
7. The Memory boundary, D-A, OD-2…OD-5, VG-1 and LF-1 are unchanged.
8. The `harness_run_ref` deferral is kept, and Edge sufficiency is disclosed as unverified.

### Checks I ran

- `git diff 291c9da..HEAD`: only 8 documentation and governance files changed. No tracked file under `uri_v1`, `uri_core`, `tests`, `scripts` or `fixtures` changed.
- Every untracked file under those directories has an mtime of 2026-09-24 or earlier, before the planning baseline.
- scripts/m33_3_r_anchors.py returned `ok=True, changed=[]`.
- `git diff e26d98c..cc4d7bc` on the plan removes exactly 4 lines: Status, G-10, the `user_storage` row and E-3. Everything else is additive notices plus §17. §16 rulings text is untouched.
- Governance diffs change only the M36 block and add one `corrections` entry.
- I read these frozen files myself: `authority.py:23-43`, `rar_deterministic.py` L0–L2 (≈299-384), `binding.py:_fresh/_binding_locked`, `fingerprints.py`, `user_storage.locked_append` and `lfm_semantic_decoder.py:320-355`.
- Python 3.13.15 has `DirEntry.is_junction`, `Path.is_junction`, `FILE_ATTRIBUTE_REPARSE_POINT` and `FILE_ATTRIBUTE_OFFLINE`. It has no `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS` constant.

### Per-finding determination

| Finding     | Determination                     | Basis                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F-1 / R-1   | **Holds as written, but see N-1** | The collision scope covers all registered roots, title and stem. Only a COMPLETE receipt may project. An incomplete scan sends no query at all, which is correct because a flag cannot downgrade S1 (`authority.py:35-42`). Projection sets `exact_aliases=()`, so EXACT_ALIAS cannot fire. §17.3 runs the lookup whatever the tier.                                                              |
| F-2 / R-2   | Holds                             | Adds a closed transition table and a kind × provenance matrix. The expected head is checked under a stable per-user guard, with no timestamp selection. `MODEL_DERIVED` is limited to a labelled `next_step` subfield. The loader re-derives authority and quarantines mismatches. The guard design matches `locked_append`, whose module lock is not reentrant, and the plan forbids nesting it. |
| F-3 / R-3   | Holds                             | Eligibility is separated from freshness, with a per-item recorded-hash baseline. Registry refresh runs before exclusion, and tier 4 runs when nothing survives. The cap rule uses size and mtime to detect change only. Degraded identity never gives certainty. Q-10 and E-3 are corrected.                                                                                                      |
| F-4 / R-4   | Holds                             | Exactly one attachment for the whole turn. Multi-slot turns need a raw-span type word. The type map is closed, and a model `type_hint` never enables an anchor. See advisory A-2.                                                                                                                                                                                                                 |
| F-5 / R-5   | Holds                             | Closed temporal vocabulary with IANA timezone and ISO weeks. Task and time predicates are applied before lexical filtering. Tier-3 stopwords are defined. Overflow fails the whole query, with no top-N. A 20+ task fixture is required.                                                                                                                                                          |
| F-6 / R-6   | Holds                             | Bootstrap-only registry, a non-serializable capability and a receipt with a protected attestation. The provenance × status matrix is complete. Negative verdicts get `VERIFIER_ATTESTED`, which a claim cannot supersede. The threat boundary is disclosed honestly.                                                                                                                              |
| F-7 / R-7   | Holds                             | Sorted `os.scandir` traversal. Entries that are symlinks, junctions or reparse points are never descended. Containment is checked per path component, never by string prefix. Hashing uses handle identity with a recheck. Junction tests use native tooling, and symlink skips must state the reason.                                                                                            |
| F-8 / R-8   | Holds                             | Tail inspection happens on a separate read handle, with a separator inserted under the guard. Fsync precedes unlock. `persisted=True` only after exact read-back and validation. Quarantine is deduplicated, and retry is idempotent by record ID.                                                                                                                                                |
| F-9 / R-9   | Holds                             | An immutable turn snapshot is reused as `current_query`. This matches `_fresh`, which compares fingerprints that include `recency_rank`. Material change forces a new round. `verify_source` is required before use, which is needed because `candidate_fingerprint` does not include the content hash.                                                                                           |
| F-10 / R-10 | Holds                             | `open_tasks` works from validated heads. Q-9 starts in a new process with no `task_id`. `HISTORICAL_BINDING` is labelled. Consequential actions rebind, and completed tasks never auto-resume.                                                                                                                                                                                                    |
| F-11 / R-11 | Holds                             | The correction and state are written as a pair under one guard, sharing an operation ID. `PENDING_CORRECTION` covers a crash between the two records. The loader never promotes half a pair. The history chain A→B→C is kept, and dependent derivatives become `SUPERSEDED_REFERENCE`.                                                                                                            |

Status of the ten safety properties:

- **Exact-name certainty:** holds only for a user-verbatim expression. Not confirmed otherwise (N-1).
- **Held:** the other nine — task heads, edited-source rediscovery, per-slot anchors, temporal and paused-task discovery, registered verifiers only, junction and reparse fail-closed, read-back before `persisted=True`, stable clarification IDs, paired corrections.
- **Boundary items all intact:** frozen scope, the Memory boundary, D-A, OD-2…OD-5, VG-1 and LF-1. The `harness_run_ref` deferral is preserved (§17.14). Edge sufficiency is disclosed as unverified.

### Remaining bounded defect (required)

**N-1: exact-name and exact-ID certainty can come from model-produced expression text.**

- **Evidence:**
  - `authority.py:29-30` gives `EXACT_ID` CERTAINTY.
  - `authority.py:39-42` gives CERTAINTY when the expression equals a unique title.
  - In the production decoder path (`lfm_semantic_decoder.py:345-352`), `reference_expression` is the model's `cand_ref.expression`. Nothing in `uri_v1/reference_clarification` checks it against the raw user text.
  - M36 §7.7 exposes `source_id` values to the Brain in the context package, and §7.6 uses `source_id` as `RARCandidate.id`.
- **Scenario 1:** the user says "update the budget sheet". The decoder normalizes this to `budget.xlsx`. The collision receipt is COMPLETE with one match. S1 grades CERTAINTY, and the result is a wrong CONFIRMED binding.
- **Scenario 2:** the decoder copies a `source_id` out of the context package. Level 0 `EXACT_ID` fires and grades CERTAINTY.
- **Why it matters:** §17.1 checks completeness but never checks where the expression came from. This breaks D3 and the Q-A2-1 "0 wrong CONFIRMED" gate. R-1's intent covered a *typed* exact filename.
- **Repair (one rule plus fixtures in §17.1 / §17.12):**
  - `project()` sends a `reference_expression` to S1 only when URI has checked it is a verbatim, casefold-equal substring of the raw user turn. The raw span is already in `MemoryQuery` via §17.5.
  - Any other expression must not reach S1 as an exact title or ID. Use the raw span instead, or ask for clarification.
  - Add two Q-A2-1 fixtures: (a) the decoder rewrites a descriptive phrase into a unique filename; (b) the decoder emits a `source_id` taken from the package. Pass condition: 0 CONFIRMED in both.

### Advisory (not blocking)

- **A-1:** `stat` has no `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS`. The implementer must define `0x00400000` with a comment.
- **A-2:** The multi-slot guard (§17.4) depends on the slot count, which the model decoder produces. If a two-reference turn is decoded as one slot, it falls back to the plain S4 single-attachment rule. That rule was accepted as the baseline, so this is not a regression. Applying the type-word guard whenever a raw span exists would harden it.
- **A-3:** `locked_append` uses a module-global thread lock shared with S7 and S11 writers. Holding the Memory guard can add contention across stores, though it cannot deadlock if the no-nesting rule is followed.
- **A-4:** Scanning all roots for exact-name completeness will often fail closed on large roots. This is safe but hurts usability. Measure it at qualification.
- F-12…F-18 remain open, as §17.14 discloses.

### Limitations

- I could not independently confirm that the pre-audit report is byte-identical to its pre-commit version. It was untracked before `cc4d7bc`, so git history only shows it as committed there.
- I did not rerun the governance validator or the 83-test suite. Only the anchor checker was rerun.
- All Q-A2 gates are future evidence. No Memory code exists yet.
- Edge sufficiency and E-6 remain unverified, pending OD-3.
- An unrelated pre-existing `SKILL.md` edit is uncommitted in the working tree. I left it untouched.
# M36 URI-Memory Minimum — Independent Closing Audit

**Auditor:** Claude (independent of the implementer, Codex), per Chetan's instruction of 2026-09-28. The audit ran on a clean Linux clone and on Chetan's Windows `_V1` checkout. A device-side copy of the report sits untracked at `_V1/M36_INDEPENDENT_CLOSING_AUDIT_REPORT.md`; this file is the merged version.
**Audited commit:** `be4451c6fda7803a742e0ad48c7fec63140ec30b` ("feat(memory): implement M36 minimum with grounded qualification"), head of `m35-uri-v1-parallel-architecture` on `github.com/sche004-cyber/uri-agent` (verified with `git ls-remote` on 2026-09-28).
**Implementation base:** `23f5cd9` (plan through A4). **Frozen M33.3 baseline:** `291c9da`.
**Environment:** Linux, Python 3.11.15, clean clone. Not the implementer's Windows 11 / Python 3.13 host.
**Scope:** read-only audit. No repair, commit, push, freeze or promotion was performed.

## Verdict

**REPAIRS_REQUIRED — not accepted for freeze.**

The boundary, governance and frozen-artifact claims reproduce exactly. Most A2 gates hold under code reading and re-execution. The audit ran twice: once on a clean Linux clone and once on Chetan's Windows `_V1` checkout. Six defects reproduce with probe scripts, and one of them breaks M36's primary safety gate (zero wrong CONFIRMED):

| # | Severity | Gate broken | One line |
|---|---|---|---|
| F-1 | **High** | Q-3, A3 F, §18.2 rule 2 | Negated references other than the literal word "not" bind CONFIRMED to the file the user excluded. |
| F-2 | Medium-High | Q-A2-2, §17.2 transition table | "I'm not done yet" is accepted as an explicit user COMPLETED; "please don't cancel this" as ABANDONED. |
| F-3 | Medium | Q-A2-6, Q-A2-10, §17.2 restart rule | Reloading without the same verifier registry drops verdicts; a FAILED verdict disappears behind its claim and a verified-complete task silently reverts to OPEN. |
| F-4 | Medium-High | §17.6 "cannot hide a verifier failure" | A user forget (TOMBSTONE) can hide a FAILED verdict; the package then shows only a later harness claim, with no degraded flag. |
| F-5 | Medium | Q-A2-1 collision completeness | Memory's `stem_title` drops the frozen matcher's `.` and `/` separators, so a collision set can be declared complete while missing a same-stem file. |
| F-6 | Medium (demonstrator) | Q-A2-1 / §17.1 usability | Any hidden or system file in a root (desktop.ini, `~$` lock files, `.git`) marks every scan incomplete and blocks all exact-title certainty. |
| D-1 | Docs | Governance history | `URI_STATE.yaml` overwrote the PG-M1 verdict instead of appending, and still says "PG-M2 blocked" in one place. |

All six code repairs are bounded to `uri_v1/memory/` and M36 tests. None touches a frozen file.

## Observed evidence (re-executed by the auditor)

| Check | Command / method | Result |
|---|---|---|
| M36 tests | `pytest tests/test_m36_memory_*.py` | **90 passed, 1 skipped** (`test_m36_memory_sources.py:24`, "Windows junction qualification requires Windows"). Codex reported 91 passed on Windows; the one skip is platform, not failure. |
| Qualification driver | `python scripts/m36_memory_qualification.py --output <scratch>` | 45 cases × 2 runs, `wrong_confirmed=0`, `invented_ids=0`, `deterministic=True`; F-B: 22 S1 bindings, 1 S7 Change, 1 S11 version, 16 records, forced termination + new-process discovery true, verifier `VERIFIED`, derivative `DERIVATIVE_STALE`. Matches Codex's claim **within its battery** (see F-1 for the battery's gap). |
| Threshold file | `sha256sum fixtures/m36_memory/threshold_gate.json` | `e5fdeff5…af24af`, matches the report. |
| `tests/` directory (frozen M33.3, M35, M36, governance, dev_workflow) | `pytest tests/` | **706 passed, 1 skipped, 130 subtests passed.** |
| Full repository suite | `pytest` at repo root, excluding `step*_test.py`, `uri_workspace`, `graphify-out` | Linux: 3,345 passed, 15 failed, 67 skipped. The 4 extra failures are network or package-staging tests (yt-dlp, GitHub package, strip_json_comments), and none touch Memory. This matches the 15 failures recorded earlier for the pre-M36 m35 head on Linux. Authoritative run by the run on Chetan's Windows `_V1` checkout at `be4451c`: **3,351 passed, 11 failed, 65 skipped** over 258 files. The 11 failures are the same node IDs Codex reproduced on the pre-M36 base, and the +91 passes are the M36 tests. No new failure. The repo is not fully green. |
| Governance validator | `python -m scripts.governance.uri_state_validator` | `VALID`, no DCL violations. |
| Frozen anchors | `python scripts/m33_3_r_anchors.py` | `ok=True, changed=[]`, 8 S4 + 24 LF anchors, RAR SHA-256 `4db77566…5e1b95` (also hashed directly). |
| Frozen scope | `git diff --quiet 291c9da be4451c -- uri_v1/turn uri_v1/reference_clarification uri_v1/evaluation uri_v1/results tests/test_m33_3*` | No change. |
| Commit contents | `git show --stat be4451c`; `git diff --name-only 291c9da be4451c` | 44 files: `uri_v1/memory/**`, 9 `tests/test_m36_*`, 1 driver, 2 fixtures, governance/docs. No `uri_core/`, S1–S12, `/ask` or UI file. `SKILL.md` and unrelated dirty files are not in the commit. |
| Whitespace | `git diff --check 23f5cd9 be4451c -- uri_v1/memory tests/test_m36* scripts/m36*` | Clean. |

## Findings

### F-1 (High): negation outside the literal word "not" yields wrong CONFIRMED

**Evidence.** `uri_v1/memory/uri_adapter/envelope.py:64-67` treats a reference as negated only if the ref span contains one of `{not, no, except, exclude, without}`. `envelope.py:143` then passes frozen RAR `RAREvidence(clause_text=expression)`, so the grounded filename is all RAR sees. Frozen RAR's own negation handling (`uri_v1/turn/rar_deterministic.py:196`, `:447`) relies on `negation_spans` or the tokens `not`/`skip`/`other` inside the reference expression. The adapter drops the former and crops the latter away. The driver's only negated form is `f"not {name}"` (`scripts/m36_memory_qualification.py:119`), the one word the guard covers.

**Reproduction.** Real `setup` / `retrieval` / `registered` helpers from the M36 tests, files `budget.xlsx` + `report.docx`, trusted intake, proposal `budget.xlsx`:

| Raw user turn | Span | Result |
|---|---|---|
| `not budget.xlsx` | whole | PENDING (control, correct) |
| `don't use budget.xlsx` | whole | **CONFIRMED budget.xlsx** |
| `never budget.xlsx` | whole | **CONFIRMED** |
| `skip budget.xlsx` | whole | **CONFIRMED** |
| `anything other than budget.xlsx` | whole | **CONFIRMED** |
| `instead of budget.xlsx use the report` | whole | **CONFIRMED** |
| `not budget.xlsx` | `(4,15)`, "budget.xlsx" only | **CONFIRMED** |

Probe: `docs/plans/m36_audit_probes/probe_negation.py` (copy into `tests/` to run).

**Why it matters.** §18.2 rule 2 says "Existing negation and reference validation still apply". A3 F says negation cannot be cropped into a positive selection. Q-3 requires zero wrong CONFIRMED. `skip` and `other` were handled by frozen RAR before M36, so the adapter regresses frozen behaviour, not just a gap.

**Bounded repair.** In `envelope.ground()`, evaluate negation over the whole trusted raw turn, not only the span, with a closed deterministic cue set: `not, no, never, don't/dont/do not, skip, except, excluding, exclude, without, other than, instead of, rather than, avoid`. Handle apostrophes before tokenizing. Any hit returns `NEGATED_REFERENCE`, which leads to clarification. Add the seven rows above to the M36 tests and add a battery case per cue form as newly predeclared cases, without relaxing thresholds.
**Acceptance check.** All probe rows are non-CONFIRMED. `test_a3_c_literal_controls` and H3 (`budget.xlsx` typed) still CONFIRMED. Full M36 suite and driver still pass with `wrong_confirmed=0`.
**Accepted cost.** Turns such as "update budget.xlsx, not the old one" will clarify rather than confirm. This is conservative and consistent with §18.3.

### F-2 (Medium-High): user-transition gate ignores negation

**Evidence.** `uri_v1/memory/recorder.py:116-119` accepts a user status change if any word of the raw turn is in a keyword list (`done`, `complete`, `cancel`, `pause`…). The record is then stored as `USER_PROVIDED` / `USER_ASSERTED` with a `USER` event.

**Reproduction** (`docs/plans/m36_audit_probes/probe_state.py::test_negated_user_transitions`):

| Raw user turn | Requested status | Result |
|---|---|---|
| `I'm not done yet` | COMPLETED | persisted, head COMPLETED, USER_ASSERTED |
| `please don't cancel this` | ABANDONED | persisted, head ABANDONED (terminal) |
| `do not pause` | PAUSED | persisted, head PAUSED |

**Why it matters.** §17.2 admits COMPLETED only on an "explicit user declaration" and ABANDONED on "explicit user cancellation only". A model-proposed status plus a negated keyword satisfies the gate and is recorded as the user's own assertion. Once terminal, only a USER_CORRECTION can undo it.
**Bounded repair.** Reuse the F-1 cue set. If the raw turn contains a negation cue, reject with `EXPLICIT_USER_TRANSITION_REQUIRED`. Add the three rows as tests.
**Acceptance check.** The three probe rows return not persisted. Existing transition tests (`pause`, `resume`, `complete`, `cancel`) still pass.

### F-3 (Medium): verdict history depends on the process's verifier registry

**Evidence.** `uri_v1/memory/index.py:146-148` validates each `VERIFIER_RESULT` against the process-global `recorder._VERIFIERS` on every load. A mismatch raises, and `log.py:113-117` quarantines the record. Its dependents cascade: a TASK_STATE that cites it fails `INVALID_OUTCOME_LINK` or `VERIFIED_CURRENT_REFERENCES_REQUIRED`, and later states fail `INVALID_SUPERSESSION_TARGET`.

**Reproduction** (`docs/plans/m36_audit_probes/probe_state.py`):
- FAILED verdict written with registry `("BYTE_EVIDENCE","1")`, then reloaded with an empty registry or version `"2"`. The verdict is not loaded, and the only current outcome is the harness claim `CLAIMED_ONLY`. The context package shows the claim and `degraded=QUARANTINED_RECORDS`.
- Task completed through a VERIFIED verdict, then reloaded without the registry. The head is **OPEN**, `open_tasks()` lists it as resumable, and there are 2 recovery IDs.

**Why it matters.** §17.6 says a verdict "cannot silently remove the earlier verdict" and must be protected from later claims. §17.2 says restart "reconstructs the validated head exactly; no automatic completion/resume". §17.6 does allow unsupported versions to be quarantined, but the combined effect is that a verifier upgrade, or a load before bootstrap, re-opens finished work. Retrieval and `open_tasks` carry no degraded signal; only the context package does. Codex's report discloses the bootstrap dependency but not this effect.
**Bounded repair (default chosen by the auditor).** When any stored attestation references a verifier id or version absent from the registry, fail the whole load closed with a distinct `VERIFIER_REGISTRY_MISMATCH` degradation. Retrieval returns `STORE_UNAVAILABLE`-style degradation, `open_tasks` raises or returns nothing, and no record is quarantined for this reason alone. Add both probe scenarios as tests.
**Acceptance check.** Both probe scenarios yield an explicit degradation, never a CLAIMED-only current outcome or an OPEN head.
**Open user decision (not needed for the bounded repair).** Should the registry also retain retired verifier versions, so that upgrades don't make history unreadable? That is an architecture choice for Chetan, not a repair.

### F-4 (Medium-High): user forget can hide a verifier verdict

**Evidence.** `index.py:165-167,181` admits any existing record as a TOMBSTONE target, and `current()` (`index.py:40-44`) then excludes it. This covers verifier verdicts and the current TASK_STATE head.
**Reproduction** (`docs/plans/m36_audit_probes/probe_forget.py`): claim, then a FAILED verdict, then a later claim, then `forget(verdict)`. The package's `recent_outcomes` is only `CLAIMED_ONLY` and `degraded=None`. Forgetting the current state head leaves the task with no head, which is stuck.
**Why it matters.** §17.6 says "A user can correct task intent or declare completion, but cannot self-issue VERIFIED or hide a verifier failure."
**Bounded repair.** In `index.accept` for TOMBSTONE, reject targets that are `OUTCOME/VERIFIER_RESULT` or `TASK_STATE` records (`INVALID_HIDE_TARGET`).
**Acceptance check.** The probe's forget is not persisted and the verdict remains in the package.

### F-5 (Medium): stem normalization diverges from frozen RAR

**Evidence.** `retrieval.py:36` replaces only `[_\-]`. Frozen `rar_deterministic.py:111` replaces `[_\.\-\/]`, and the code comment claims lineage from it. `exact_name()` feeds both the collision set (`retrieval.py:84`) and the adapter completeness check (`envelope.py:102-106`).
**Reproduction** (on Chetan's device): with `budget-v2.xlsx` and `budget.v2.xlsx`, typing "budget v2" produced a "complete" collision receipt listing one match, then bound TENTATIVE to it without showing the other file. There was no wrong CONFIRMED, because frozen S1 needs the exact full title for certainty.
**Bounded repair.** Use the frozen regex `[_\.\-\/]` in `retrieval.stem_title`, and add a two-file collision test.

### F-6 (Medium, demonstrator readiness): hidden entries make every scan incomplete

**Evidence.** `sources.py:130-131,147` (previously advisory A-1). `envelope.py:98` withholds projection whenever `collision.complete` is false, even when the excluded entry could not match the expression.
**Bounded repair.** Record excluded hidden entries by name. Treat the scan as incomplete for a query only when an excluded entry's name or stem could match that expression, or when an excluded directory could contain one. Excluded directories stay incomplete.
**Acceptance check.** A root containing `desktop.ini` and `budget.xlsx` still CONFIRMs a typed `budget.xlsx`, and a hidden `budget.xlsx` still blocks it.

### D-1 (docs): governance history overwritten

On the device review, `docs/governance/URI_STATE.yaml` replaced `PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS` with `PG_M1_ACCEPTED` rather than appending, and still says "PG-M2 blocked" in one place. The repair is an additive history entry and removing the stale line.

## Advisories (non-blocking, documented limitations)

- **A-8: lock timeout raises instead of reporting.** A write-lock timeout raises out of `append`/recorder calls instead of returning `persisted=False`. Inferred from `user_storage.locked_append`; not reproduced.
- **A-9: some claims can't be confirmed from git.** "Thresholds before first run" cannot be verified, because they landed in the same commit as the implementation. The final A4 acceptance was supplied by Chetan directly and has no report file.

- **A-1 (promoted to F-6).** `sources.py:130-131,147`: any dotfile or hidden/system entry (Windows `desktop.ini`, Office `~$*.xlsx` lock files) excludes itself and marks the whole scan incomplete. Every exact-title request in such a root then degrades with `COLLISION_SCOPE_INCOMPLETE`. This is plan-consistent and fails closed, but in a typical Windows Documents folder it means exact-title certainty is almost never projected. This is relevant to demonstrator readiness.
- **A-2: `persisted=False` can later become persisted.** After a fault between body and newline, the next append's separator recovers the complete record (`log.py:152-156`). This matches §17.8 step 2, and `test_fault_persistence_truthful_and_retry` documents it. Callers must treat False as "uncertain", not "absent". A distinct reason such as `UNCERTAIN_TAIL` would make that explicit.
- **A-3: write cost grows with history.** Each record write reloads and revalidates the entire log twice (`log.py:163,190-191`), plus one load per recorder call. That is O(history) per write and O(n²) per batch. This is not measured by the telemetry, and Codex marks load/fingerprint as UNMEASURED.
- **A-4: only the first transition event is checked.** `index.py:125` checks actor and action on `events[0]` only when a TASK_STATE cites several transition events. Current writers emit one, so this is latent.
- **A-5: trust tokens are in-process only.** They are module globals (`contracts.py:17-19`, `recorder.py:15-16`), so any in-process Python can forge them. This is inside the disclosed threat boundary (§17.6).
- **A-6: spans are a caller responsibility.** `URIIntake.capture` accepts spans from its caller. No production span producer exists yet (no S13 integration). F-1's cropped-span row shows why the negation check must not depend on span choice.
- **A-7: Windows gates not re-executed here.** The junction, reparse, ADS and `MoveFileExW` paths are Windows-only and were not re-executed on Linux. The Linux symlink-escape and handle-identity paths ran and passed.

## Gate dispositions

| Gate | Disposition | Basis |
|---|---|---|
| PA-3 / T-FROZEN / T-BOUNDARY | **VERIFIED** | Frozen diff empty; anchors ok; RAR hash matches; `tests/` passes. |
| PA-4 / PA-5 (no S13, `/ask`, `uri_core`, Office) | **VERIFIED** | Commit file list. |
| Q-1 regression | **VERIFIED** on Linux for `tests/`; full suite see above | Re-executed. |
| Q-2 / Q-3 zero wrong CONFIRMED | **FAIL** | F-1. |
| A3 A/B/C/D/E/G, A4 H1–H3 | VERIFIED (tests re-run, adapter read) | `test_m36_memory_grounding.py`. |
| A3 F (negation, boundaries) | **FAIL** for negation (F-1); boundaries VERIFIED | Probe. |
| Q-A2-1 collisions | **PARTIAL** | F-5 stem divergence; F-6 usability. |
| Q-A2-2 causal task authority | **PARTIAL** | Chain, fork and expected-head logic verified; F-2 breaks the explicit-user requirement. |
| Q-A2-3 live vs historical | VERIFIED | Code + tests. |
| Q-A2-4 attachments | VERIFIED | Code + tests. |
| Q-A2-5 temporal | VERIFIED | Code + tests (tzdata installed for the run). |
| Q-A2-6 verifier admission | **PARTIAL** | Admission and forgery rejection verified; F-3 on reload; F-4 forget. |
| Q-A2-7 containment | VERIFIED (Linux symlink paths here; Windows junction tests passed on Chetan's device, 91/91 with no skips) | A-7. |
| Q-A2-8 read-back persistence | VERIFIED (with A-2 note) | Code + fault tests. |
| Q-A2-9 snapshots | VERIFIED | Tests. |
| Q-A2-10 / Q-9 unknown-task resume | **PARTIAL** | Works with the registry present; F-3 can re-open finished tasks. |
| Q-A2-11 correction pairs | VERIFIED | Code (`recorder.py:184-234`, `index.py:96-118`) + tests. |
| Q-11 / Q-12 package bounds and isolation | VERIFIED | Code + tests. |
| Q-LAT | Observed only; not a gate | A-3. |

## Distinguishing claims from evidence

- **Reproduced:** test counts on this platform, driver aggregates, threshold hash, frozen/anchor/governance/whitespace results, commit scope.
- **Reproduced on Chetan's device:** 91/91 M36 tests with no skips, including the junction tests; the full suite at 3,351/11/65 with the same 11 baseline failures; the working tree is `SKILL.md` modified plus untracked M35/research files, none of them in the commit.
- **Inferred:** severity ratings and the demonstrator impact in A-1.

## Recommended next step

Authorize a bounded M36 repair, scoped to F-1..F-6 and D-1 plus their tests in `uri_v1/memory/` and `tests/test_m36_*`, with no frozen files. Then run a focused re-audit of those three findings before freeze.

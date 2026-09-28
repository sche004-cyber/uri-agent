# M33.3-R — Independent Closing Audit, Repair and Requalification

**Auditor:** Codex, independent of Claude's implementation session.
**Authority:** direct User closing-audit task package, 2026-09-27. This one
session may inspect, reproduce, bounded-repair, requalify, conditionally
freeze, commit and push. It does not change the standing AO-4 role rules.
**Current verdict (2026-09-28):** `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`.
**Milestone state:** `CLOSED_FROZEN`, within the explicit offline/fixture scope.
**Release files:** [exact manifest](M33_3_R_CLOSING_AUDIT_EVIDENCE/release_files.json).

## A. Baseline and independence

- Worktree: `C:\Users\cheta\Development\Uri\_V1`.
- Branch: `m35-uri-v1-parallel-architecture`.
- Starting HEAD: `d1feaf72f7b1322fe30cc21e2808d5eab09bcdf4`.
- Live `git ls-remote origin refs/heads/m35-uri-v1-parallel-architecture`
  returned the same hash; tracking ahead/behind was 0/0.
- `c2f583909a3d13d295c997c038b0ac724f787755` is an ancestor; the candidate
  range contains one commit. No reset, clean, or absorption of unrelated work.
- Clean managed baseline/candidate checkouts were created. Separate LF
  exports use `git -c core.autocrlf=false archive`, not the dirty source tree.
  Audit repairs are a separately enumerated overlay for pre-commit testing.
- Independence means source/telemetry/test re-derivation by a different
  session/model, not a claim that the auditor's own bounded repairs received
  a second external review. Repairs were independently falsified first and
  then regression-tested within the User-authorized audit/repair loop.

## B. Candidate diff audit

The exact baseline-to-candidate range changes 66 files, 126,561 insertions,
5 deletions. Most volume is retained model telemetry. Mechanisms are the
existing Edge router extension, additive RuntimeLease metadata and ownership
ledger, isolated wording/evaluation/version modules, and one fixture-backed
Flutter card. Fixtures, runners, tests, research decisions and state carry
the remaining changes. No dependency manifest is changed.

Initial unrelated work is inventoried in
`M33_3_R_CLOSING_AUDIT_EVIDENCE/initial_status.txt`: modified `SKILL.md` and
untracked M35 experiments/reports/modules, scratch and graph conversions.
These are excluded from the audit release. Flutter-generated line-ending
touches are not part of the intended patch.

Research/reuse decisions are proportionate: the single router is extended;
frozen clarification builders, validator and BindingService remain owners;
storage follows existing per-user/append-lock patterns without violating the
uri_v1/uri_core import boundary; provider APIs own residency. No material
duplicate orchestrator or dependency framework was introduced. The isolated
result ledger fills a documented gap rather than replacing production stores.

## C. Governance adjudication

- **GD-1:** candidate flags still authorized next/later implementation after
  implementation was complete. Corrected both to false, with explicit
  audit-side repair authority separately recorded and historical authorization
  retained. This does not revoke the current audit or authorize S9/S13.
- **GD-2:** YAML's human-readable canonical pointer matched the candidate,
  but the narrative §1c still presented a stale reservation. An additive
  current-state paragraph corrects that pointer; historical text is retained.
- **GD-3:** current RAR raw hash is
  `4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95`.
  Historical Batch A/A9 remains
  `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649`.
- **S1-A1 authorization:** the repository's explicit User decision is in
  M33_3_R_STATE §6 and the amendment record. It authorizes bounded allowlist
  widening plus S1/S3/S5 requalification. The auditor used repository records,
  not private assistant session scraping. The present User package explicitly
  authorizes a bounded amendment correction when the intended contract is clear.
- **S1-A1 validity:** authorized in principle, defective as submitted. New
  auxiliary tokens `may` and `will` also admitted an ungrounded month/name.
  Independent inputs `Which document from May do you mean?` and `Which file
  from Will do you mean?` both passed with no flags before repair. Removing
  those two global tokens tightens the existing contract without changing
  acceptance criteria. Grounded uses remain allowed. Ordinary `or/of/is`
  grammar remains accepted; new number/name/date/extension probes fail closed.
- The amendment record retains original and candidate hashes. Corrected LF
  hash: `7f9294ea34160f3b2806f7d8c686dc24101db04344746aaad7d82af167157642`.
  Only that protected file changes. Prompt v4 reflects the smaller list.
  The previous gate is retained as `candidate_threshold_gate.json`; numeric
  thresholds are unchanged. Requalification must precede closure.
- Closure includes S5/S6/S7/S8/S10/S11/S12 only. S9 is URI-Memory/D4;
  S13 is a future INT-* milestone. `/ask` and production agent-loop wiring
  are expressly not closure gates under this task package.

## D. S5 audit

The battery has 60 cases: 36 inherited S3 cases and 24 office fixtures.
Need classes are 31 SIMPLE, 26 EXPLAIN, 3 REASONING. The original 1,020-row
final aggregate and gate verdict reproduce exactly from UTF-8 telemetry
using original candidate code and gate. Original final tiers: Edge EXPLAIN
37/52 fallbacks (71.15%), p95 540.9 ms; Capable REASONING 4/6 (66.67%),
p95 1,202.7 ms. Both fail; template is the only qualified route.

The 9B EXPLAIN result is informational: R2.5 does not permit Capable cosmetic
wording. This says nothing about general specialist Edge suitability or final
Brain/model selection. The latency gate remains p95 <= 1,500 ms, fallback
<=25%, zero provider errors. The recorded User answer removes a subjective
improvement gate; the blind sheet remains unrated.

Exploratory R1, R2 and original final artifacts remain unchanged. Hash pins,
gate metadata, and execution timestamps support the recorded ordering, but
the single squashed implementation commit cannot independently prove every
pre-run file-write timestamp. The audit's new input-only gate re-pin is
recorded before its fresh final run; there is no post-result threshold tuning.
Deterministic qualification after repair has zero policy violations and
60/60 valid templates. Fresh live final: 1,020 rows; all six required gates and every input pin
pass. Edge EXPLAIN 40/52 fallbacks (76.92%), p95 524.3 ms; Capable
REASONING 4/6 (66.67%), p95 1,208.3 ms; zero provider errors. Template
remains the only qualified route. Independent raw-output revalidation has
zero flag/validity discrepancies, and aggregates/verdict recompute exactly.
Evidence: `M33_3_R_CLOSING_AUDIT_EVIDENCE/S5_FINAL_*`.

## E. S6 audit

One pure router module remains. D2 covers AUTO/explicit, Edge ON/OFF,
supporting/substantive work and availability. Explicit substantive selection
never silently downgrades to Edge. Qualified supporting Edge remains allowed
under G2. EDGE_ONLY maps unavailable/escalating substantive routes to
LIMITATION, with the deterministic preflight exception explicitly preserved.
The 6,144-entry grid and old-routing regression are included in qualification.
Source comparison confirms old behavior outside the intended EDGE_ONLY guard.
No new routing entry point is invoked from production `/ask` or orchestration.

## F. S7 audit

Versioned events use closed event/category vocabularies, derived labels,
bounded IDs, comment-presence only, strict unknown-field rejection, separate
per-user durable storage and session evidence. OFF stops durable learning;
inspect/delete/reset and isolated users are covered. Session evidence remains
separate from durable reset, as documented. S9 reference memory is not added.

Audit repairs enforce full-string trace/span/identifier matching (Python `$`
previously accepted a trailing newline, including after an all-zero trace)
and require a nonempty event ID. W3C requires exact-length, nonzero hex IDs:
<https://www.w3.org/TR/trace-context/#trace-id>. Identifier syntax is not a
proof of producer authenticity; authenticated event binding remains S13.
No free-form comment or raw-message field is introduced.

## G. S10 audit

The legacy two-argument RuntimeLease constructor remains valid. Ownership
requires an acquired ledger entry; orphan URI-looking names remain external.
Independent collision probes found that candidate classification/unload
accepted a matching instance name with conflicting runtime/model/lease
provenance. The repair checks observed runtime/model and exact lease identity.
When a provider identifier is observed with a replaced or unknown model, the
old permission is revoked, so later cleanup cannot act on a stale lease.
String-ID lookup remains the ledger's local acquired-instance lookup, used
by the LM Studio-only study; it is not a cross-provider unload endpoint.

The frozen study protocol owns measurement/limits; provider TTL handles idle
unload. Original evidence: roughly 2.4/4.5 s cold loads, 379/555 ms Edge warm
p50/p95, 945/1,222 ms Capable, ~9.4 GB co-resident GPU, TTL ~21.4 s.
The external model is explicitly simulated, not an unconsenting user's model.
Original S5 final window ends 11:09:34 UTC; S10 starts 11:10:02 UTC; snapshots
show empty-model preflights. This supports serialized recorded windows, not
an unsupported assertion about every process on the host.
Fresh independent study passes all ownership/resource checks: cold loads
3,060.2/4,537.0 ms; Edge warm p50/p95 406.0/574.2 ms; Capable
949.2/1,238.7 ms; co-resident GPU 9,056,174,080 bytes; provider TTL
release 21.4 s. Simulated external lease stayed loaded through URI cleanup,
then was released separately by its creating study. No limit hit or cleanup
error. Fresh S5 and S10 timestamp windows do not overlap; regression runs
were held until after both windows completed.

The final study after stale-permission revocation also passes (2026-09-28):
Edge/Capable cold 3,307.7/7,661.2 ms, warm p50/p95 379.2/548.6 and
913.8/1,203.8 ms; co-resident GPU 10,284,978,176 bytes and available RAM
4,309,966,848 bytes. TTL 21.4 s; external protection passes; empty postflight;
no provider errors, resource stop or cleanup error. Evidence: `s10-final/`.
Different cold-load/resource measurements are retained rather than averaged
away; they do not establish a permanent residency policy.

## H. S11 audit

The written discovery/plan identifies external artifact edits and the frozen
S1 redo seam. Versions retain content-addressed blobs and append history.
`observe` makes preserved edits the head; `edited_status` correctly retains
USER_EDITED when that head is read back. Automatic redo on edited/unknown
content stops; normal authorized unedited redo appends. Explicit new-version
requests require a confirmed Change's blocked state and fresh authorization.
D-S11-1 is the conservative implementation of the invariant within frozen S1,
not an authorization bypass. Tests cover byte-preserved edits, missing/unreadable
content, ordinary redo, explicit versions, and external-edit detection.
An additional audit probe found that an unknown persisted version origin
would be treated as UNEDITED when its hash matched. Readback now validates
origin/version/hash and rejects malformed blob handles before filesystem
access. No S11 production persistence redesign or frozen BindingService change.

## I. S12 audit

Grounded ranked options have no padding; selections emit IDs and fingerprints;
bridge tests reject labels-as-IDs. Attribute chips emit ATTRIBUTE narrowing,
not a confirmed candidate. Escape is clickable; nonempty free input is
authoritative (outer whitespace is trimmed, as the existing fixture tests
explicitly specify). One answer locks the round.

Candidate widget state did not reset for a new round on the same element.
The repair resets input/answered state only when ambiguity ID changes and
keeps the same round locked. A widget regression reproduces the transition.
Original clean candidate Flutter: 203/203. Repaired focused card: 36/36.
Final full Flutter: 204/204. S12-specific analyzer: no issues. Full analyzer
reports one pre-existing informational deprecation at providers_screen.dart:730
(`DropdownButtonFormField.value`); independently reproduced on c2f5839.
The full analyzer is therefore not globally clean (exit 1); no new analyzer
finding was introduced. This is preserved as a baseline limitation, not
fixed outside scope or described as a passing global analyzer. No screen or real clarification core is
wired; fixture status is intentional and is not grounds for rejection.

## J. S8 audit

Per-user version-keyed records and pure preference are restricted to the
qualified, eligible set. OFF/reset and stale-route invalidation are retained.
Three audit defects were repaired: arbitrary raw text in trace_id, unusable
record types/timestamps/latencies/settings, and negative feedback rewarding
a SUCCESS at maximum reward with triple weight. Negative feedback now yields
zero reward at the existing negative weight. No reference tie-break memory.

The replay harness now refuses an S5 artifact from a different gate/prompt.
The synthetic method check uses 1,000 training observations and 4,000 separate
evaluation events, tests IPS and SNIPS, and explicitly labels its seeded
fixed-policy replay limitation. Seed 808 selects B; IPS 0.8775 vs true 0.9,
SNIPS 0.89. It does not show unseeded exploration. Real-route learning remains
degenerate while template is the only qualified route. No useful adaptive
routing or online promotion is claimed. Fresh current-gate replay: 3,000/3,000 events accepted; fixed, learned, IPS
and SNIPS all 1.0; all five guards pass. Evidence remains explicitly offline.

Method reference: Li et al., *Unbiased Offline Evaluation of Contextual-bandit-
based News Article Recommendation Algorithms*, <https://arxiv.org/abs/1003.5956>.
The implementation's deterministic one-route result must not be generalized
into evidence for an adaptive multi-route policy.

## K. Integrated regression

Fresh clean CRLF checkouts, same tracked-file test selection:

| State | Passed | Failed | Skipped | Subtests |
|---|---:|---:|---:|---:|
| baseline c2f5839 | 3,146 | 14 | 66 | 218 |
| candidate d1feaf7 | 3,236 | 14 | 66 | 218 |
| intermediate audit repairs, CRLF | 3,256 | 14 | 66 | 218 |

All 14 failing IDs match. Exact per-test failures are retained in
`failure_comparison.json` and JUnit/log artifacts. The failures cover the
standing capability-directory privacy assertion, five M20 recovery/interpreter
assertions, two M33.2 CRLF corpus hashes, session workflow, orchestrator size,
restart recovery, S3 CRLF manifest, and two S4 raw-anchor checks.

The implementer's additional intermittent durable-primitives failure did
not reproduce in either fresh full run or a clean baseline isolated run
with the required synthetic test credential secret (1 passed, 12 deselected).
An unconfigured isolated invocation fails credential setup; that is retained
separately and is not evidence of the claimed Windows atomic-write failure.
CRLF versus LF is a pre-existing checkout portability issue. No frozen raw
hash semantics or gitattributes were redesigned. Explicit LF export makes
the original S1-S12 slice tests 411/411; repaired slice tests initially 428/428
(17 audit tests at that checkpoint; subsequent tests are recorded below).
Final explicit-LF export at d1feaf7 plus the exact audit source/test overlay:
**3,261 passed, 9 baseline failures, 66 skipped, 218 subtests passed**. All remaining failure IDs are baseline failures;
all five CRLF hash failures disappear. No new material regression remains.
The final run includes 431/431 passing M33.3 tests, all 248 original tracked
test files plus the 20-case
audit regression file. Exact counts/logs/JUnit: `repaired-final-lf.*`.
`failure_adjudication.json` records every baseline failing test individually.
The intermediate repaired CRLF run predates the final stale-lease revocation
assertions; this final LF run includes them. S8 also replayed from the clean
LF export without unrelated local research helpers.

## L. Protected anchors and governance

All 8 S4 raw anchors and 24 S1-S4 LF anchors were recomputed. Full expected,
actual and baseline Git-blob hashes are retained in `protected_hashes.json`.
Only the authorized render-validator amendment differs from the prior baseline;
its successive re-pins are explicitly recorded. S3 requalification is 82/82
(60 L1, 22 L2). S4 replay: 79 cases, 18 groups, 2,466 rows, zero wrong-confident
bindings. Historical Batch A and A9 evidence is retained.
Governance validator and scoped `git diff --check` passed at intermediate
checkpoints. Final checks are recorded in `final-governance.log`, `final-anchors.json`
and `final-diff-check.log`: VALID, all 32 anchors match, and the full staged
`git diff --check` passes. Text output views normalize trailing whitespace;
exact captured originals and hashes are retained in `raw_test_output.zip`
and `raw_test_output_manifest.json`.

## M. Audit repairs

| ID | Defect | Bounded repair / affected qualification |
|---|---|---|
| CA-1 | S1-A1 admits invented May/Will | Remove two ungrounded homonyms; preserve/re-pin history; S1/S2/S3/S4/S5/S8 and integrated regression |
| CA-2 | Non-exact W3C IDs / missing event ID | Fullmatch and required provenance ID; S7 plus audit regression |
| CA-3 | S8 raw trace text, malformed records/settings, negative feedback rewards | Strict record validation, fail-closed settings, zero reward for negative feedback; S8 replay/regressions |
| CA-4 | S10 name collision confers foreign lease ownership | Compare runtime/model and exact lease identity, revoke replaced-model permission; S10 tests and two fresh studies |
| CA-5 | S12 reused widget locks the next round | Reset only for a new ambiguity ID; focused/full Flutter and bridge tests |
| CA-6 | S8 replay can combine old verdict with new gate; synthetic check lacks held-out SNIPS/replay | Verify gate/prompt identity, distinct output paths, held-out synthetic method check; fresh replay |
| CA-7 | Stale implementation flags and narrative pointer | Scoped audit-state/closure reconciliation; governance validation |
| CA-8 | S11 unknown persisted origin read as unedited | Validate version origin/number/hash and exact blob/result identifiers; S11 and audit regression |

## N. Remaining limitations

- No qualified model wording tier at either candidate or fresh audit checkpoint.
- REASONING has only three contracts/six production-config rows.
- No calibrated need-class preference rating; User accepted template primary.
- S8 one-route degeneracy, no demonstrated useful adaptation or exploration.
- S12 fixture-only; external artifact writers/real event provenance remain S13.
- CRLF raw-byte hash portability; use explicit LF checkout for qualification.
- Full Flutter analyzer has one independently reproduced baseline informational
  deprecation outside S12; scoped analysis is clean.
- Frozen lexical validation is not general semantic entailment; no arbitrary
  semantic safety claim is made from word allowlisting.
- Single squashed commit limits independent reconstruction of original
  pre-implementation/pre-run artifact timing; original evidence is preserved.
- The full standing suite is not globally green; pre-existing failures are
  reported individually rather than waived as a group.
- Broader Specialist Edge Brain overhaul remains subsequent work; no permanent
  Edge/Main model choice, residency policy, or production adoption is frozen.

## O. Final state

| Slice | Final state |
|---|---|
| S1 | CLOSED_FROZEN, corrected S1-A1 requalified |
| S2 | CLOSED_FROZEN, preserved |
| S3 | CLOSED_FROZEN, 82/82 reconfirmed |
| S4 | CLOSED_FROZEN, offline replay reconfirmed |
| S5 | CLOSED_FROZEN, template qualified; model tiers not qualified |
| S6 | CLOSED_FROZEN, isolated routing contract |
| S7 | CLOSED_FROZEN, isolated event contract |
| S8 | CLOSED_FROZEN, offline one-route replay |
| S10 | CLOSED_FROZEN, ownership contract and bounded study |
| S11 | CLOSED_FROZEN, isolated result-version contract |
| S12 | CLOSED_FROZEN, fixture-backed UI |
| S9 | EXCLUDED; URI-Memory/D4, not complete |
| S13 | EXCLUDED; future INT-* integration, not complete |
| M33.3 | CLOSED_FROZEN with documented limitations |

Closure becomes durable at the commit containing this report. No subsequent
milestone is opened by this one-session release authorization.

## P. Commit and push

The release consists only of the bounded repairs, audit regression, affected
qualification evidence and linked governance/state records. Exact paths are
in `release_files.json`. Unrelated SKILL.md/M35 work and Flutter-generated
platform touches are excluded. The commit containing this report is the
closure commit; the final session receipt records its hash and actual push
result to `origin/m35-uri-v1-parallel-architecture`, with live equality.
This file does not assert a push before it occurs.

## Q. Final verdict

**ACCEPT_WITH_DOCUMENTED_LIMITATIONS — M33.3 CLOSED_FROZEN.**
The authorized offline/fixture-backed gates pass after bounded audit repairs
and fresh requalification. This is not production integration or a declaration
that the standing repository test suite is globally green.

# M30.8 - Canonical Default Cutover (Read-Only Pre-Audit)

STATE: PRE-AUDIT ONLY - NOT A PLAN, NOT ACCEPTED, NOT AUTHORIZED.

Produced by Claude (Architect/Pre-Auditor role, AO-4) at the User's
explicit request, strictly read-only: no production code was written
or modified to produce this document. This is not Stage 4
implementation authorization and does not itself start M30.8. Per the
User's own instruction, Claude stops here for explicit approval before
any M30.8 plan is drafted or any implementation begins.

**Sources consulted (all re-read this session, not assumed from
memory):** `docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md`
(§1, §4, §6, §7, §13-§19), `docs/architecture/
URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md` (§4 Decision ownership),
`docs/research/URI_AGENT_LOOP_ROOT_CAUSE_AUDIT.md` (§4 authority
fragmentation), `docs/plans/M30_7_STATE.md` (final disposition),
`docs/governance/URI_ACTIVE_MILESTONE.md` (current state), and direct
source inspection (`orchestrator.py`, `canonical_execution.py`,
`decision_gates.py`, `capability_planner.py`) for current line counts
and call-site facts cited below.

---

## 1. Exact objective

Per the migration plan's own Phase D / §17 row M30.8 (verbatim intent,
not paraphrased into something new): **`enable_decision_engine_live`
defaults on for all capabilities** (today it is an explicit allowlist
of exactly two: `Gmail`, `remember_fact`, per M30.6's
`CANONICAL_EXECUTION_ALLOWLIST`). The old five/six-mechanism priority
chain (§4 below) becomes fallback-only, invoked solely when the
Decision Engine itself is unreachable or returns a malformed/rejected
contract - mirroring exactly `capability_planner.py`'s already-planned
demoted role. This is the first milestone where the canonical loop is
authoritative for *every* capability, not a controlled subset.

## 2. Architectural responsibility changes

| Component | Before M30.8 | After M30.8 |
|---|---|---|
| Decision authority | Decision Engine authoritative only for `Gmail`/`remember_fact` (M30.6 allowlist); every other capability still resolved by the legacy priority chain | Decision Engine + deterministic gates authoritative for all capabilities |
| `orchestrator.py`'s ~300-line interleaved priority block | Fully intact, executes every turn (M30.6's canonical path is purely additive/parallel, per M30.6's own report: "Not changed: orchestrator.py... every execution mechanic reused unchanged") | Replaced by flat mode-dispatch; the priority block's *decision* role is removed (its execution mechanics are reused via the Execution Engine, not deleted - migration plan §1's KEEP/ADAPT rows) |
| `capability_planner.py` | One of (at minimum) five competing first-movers, scored every turn regardless of outcome (root-cause audit §4, item 4) | Demoted to exactly two roles: Unsupported-Gate cross-check engine, and the fallback decision-maker when the Decision Engine is unreachable/malformed |
| `skill_memory.py` | Can short-circuit directly into a plan (`learned_skill.get("tool_name")`) ahead of the deterministic planner (root-cause audit §4, item 3) | Demoted to a Turn State reference hint only - the direct-plan shortcut line is removed |
| `MultiActionDispatch` (M27) | A parallel, narrow-shape-triggered dispatcher, live-verified essentially never fires today (root-cause audit §4, item 2) | Folded fully into the Execution Engine as the universal action-execution path for every mode |
| `WorkflowPlanner`/`WorkflowCapabilityRouter` | A sixth, fully independent deterministic decision engine with its own task-type-keyed template logic (root-cause audit §4, item 5) | Retired as a *decision* engine; specific templates it still uniquely covers become named Directory procedures (inventory work is M30.2's job, not M30.8's - confirm this inventory actually happened before relying on it, §5 below) |

## 3. Dependencies that must already be proven

Per the migration plan's own dependency column for row M30.8: **"M30.7,
full regression green."**

- **M30.7 closure:** satisfied. `docs/plans/M30_7_STATE.md` records
  `LIVE_VERIFIED + CLAUDE ACCEPT (documented residual)`, explicit User
  disposition 2026-09-13. The one residual (organic live trigger of
  the `post_execution_reevaluation` capability_id-threading fix) was
  explicitly accepted as non-blocking by the User and does not, on its
  own, block M30.8.
- **Full regression green:** satisfied for every file M30.7 touched
  (independently re-run by Claude across two audit rounds - 135/135,
  137/137 via pytest; 123-125/123-125 via unittest, zero failures both
  runners, both rounds). The full ~1710-test repository baseline
  (8 known, pre-existing, unrelated failures - Drive `AttributeError`,
  M20 resilience tests, `orchestrator.py` line-count) was not re-run
  this session at any point; **this should be re-run once more,
  fresh, immediately before an M30.8 plan is accepted**, since several
  milestones' worth of source changes have accumulated since the
  baseline note was recorded.
- **The migration plan's own, separate M30.8 acceptance gate is a
  stronger bar than "M30.7 closed" and is NOT yet satisfied - see §9,
  this is the single most important finding of this pre-audit.**

## 4. Legacy decision/routing mechanisms affected

Named exactly, from the root-cause audit's own enumeration (§4, five
candidates plus a sixth):

1. The Brain's own `action`/`workflow`/`clarification` output
   (`_model_proposed_capability`/`_model_proposed_workflow`/
   `_model_clarification`, M11/M13) - currently first-priority when
   present.
2. `MultiActionDispatch` (M27) - currently priority-overrides #1 when
   its narrow shape is detected (rarely).
3. `skill_memory` learned-skill direct-plan shortcut.
4. `capability_planner.py` - currently the deterministic last resort.
5. `WorkflowPlanner`/`WorkflowCapabilityRouter` - a sixth, independent
   decision engine for task-type-templated workflows.

Also affected: the **3 real `_apply_clarification_pause` call sites**
in current code (`orchestrator.py:2796` `post_execution_reevaluation`,
`4592` `pre_execution_check`, `4662` `initial_reasoning` - confirmed by
direct grep this session, not assumed). Note: the original root-cause
audit (§4) recorded *four* such call sites including one inside "the
M13 Part 2 acceptance-retention loop"; only 3 exist in current code.
This is a stale historical count, not a live gap - it is not being
raised as a new M30.8 blocker, only disclosed since this pre-audit
found the discrepancy while verifying facts rather than repeating the
older document's number uncritically.

**One real, newly-observed residual not previously tracked:** the
`pre_execution_check` call site (`orchestrator.py:4592`) fires *after*
a plan was already formulated (per its own M13 Part 1 design intent -
"a plan was formulated, then the Brain decided against acting on it
once given fuller context") - meaning, unlike `initial_reasoning`, a
capability is very plausibly already known in scope at that exact
point, the same way `post_execution_reevaluation` was found to have
one during M30.7's own REVISION v4 fix. This call site was never
audited for the same `capability_id`-threading opportunity M30.7 gave
`post_execution_reevaluation`. Not a blocker for M30.7 (already closed)
and not automatically an M30.8 blocker either, but worth a bounded
look before or during M30.8, since M30.8 makes `workflow_continuation`
authoritative for every capability, not just the two allowlisted ones -
a real gap here would matter more once every clarification pause can
plausibly need to resume canonically.

## 5. What becomes canonical vs. fallback

**Canonical (authoritative for all capabilities):** Turn State →
Decision Engine → deterministic gates (availability, completeness,
unsupported, connection, permission, approval, execution-validation,
per migration plan §6) → Execution Engine (`MultiActionExecutor`/
`ApprovalGate`/`ToolDispatcher`, unified) → response drafting
(unchanged, single call site).

**Fallback-only (reachable exclusively on Decision-Engine
unreachability or a malformed/rejected contract):** the entire legacy
priority chain named in §4 above, with `capability_planner.py` as its
specific entry point - mirroring exactly the role migration plan §1
already assigns it. This is a **flag-gated behavior**, not a code
deletion - `enable_legacy_decision_fallback` (already named in the
plan's own flag table, default **on**, "cannot be turned off before
Phase E/M30.10") keeps the fallback reachable throughout M30.8 and
M30.9.

## 6. Risks of reintroducing multiple decision owners

This is the exact failure mode the entire migration exists to remove
(root-cause audit §4: "up to five mechanisms independently decide and
only one wins by accident of ordering") - M30.8 is the milestone with
the highest risk of a *partial* or *silent* regression back into it,
because it is a global behavior flip, not an additive one like
M30.1-M30.7:

- **Incomplete `capability_planner.py` demotion:** if any code path
  still calls it as a first-mover (not merely as the Unsupported-Gate
  cross-check or the unreachable-model fallback), dual authority is
  silently reintroduced for whichever capability that path covers.
  Must be verified by a real, structural check (e.g., grep for every
  remaining call site and confirm each maps to exactly one of the two
  sanctioned roles), not by trusting the flag flip alone.
- **`skill_memory.py`'s direct-plan line surviving in a second form:**
  the migration plan is specific that "the single line that turns a
  skill match directly into a plan is removed" - a partial removal
  (e.g. gated behind a condition that's usually false, rather than
  deleted) would reintroduce exactly this risk under specific inputs.
- **Directory adapter drift (named risk, migration plan §19):** the
  Capability Directory's legacy and M27-derived adapters could present
  different shapes for the same underlying capability if one drifts
  out of sync - at allowlist scale (2 capabilities) this was
  containable; at global scale (every registered capability) an
  undetected drift becomes a real, silent per-capability decision-
  authority split, not merely a shape bug.
- **`WorkflowPlanner` template gaps (named risk, migration plan §19):**
  if M30.2's own template inventory was incomplete or never fully
  reconciled, a task type with no Directory-procedure equivalent yet
  would either silently fall through to `WorkflowPlanner` as a
  seventh, undemoted decision path, or silently lose coverage - both
  are real dual-authority-shaped failures. **This pre-audit could not
  confirm from the artifacts read whether M30.2's template inventory
  was ever actually completed and reconciled against production
  capabilities** - this should be explicitly re-verified, not assumed
  closed, before an M30.8 plan is drafted.
- **`CANONICAL_EXECUTION_ALLOWLIST` reconciliation, an open design
  question not resolved by the migration plan's text as written:**
  `canonical_execution.py`'s `CANONICAL_EXECUTION_ALLOWLIST =
  frozenset({"Gmail", "remember_fact"})` is the concrete M30.6
  mechanism gating canonical execution today; the migration plan
  describes M30.8 as `enable_decision_engine_live` defaulting on
  "for all capabilities," but does not explicitly say whether the
  allowlist mechanism itself is retired/expanded-to-everything or
  kept as a second, now-redundant gate. Left unresolved, this is
  exactly the kind of two-owners situation this section warns
  against - a future M30.8 plan must explicitly decide and state
  which happens.

## 7. Required feature flags

| Flag | Current state (verified) | Required M30.8 change |
|---|---|---|
| `enable_decision_engine_live` | Allowlist-scoped (`Gmail`, `remember_fact`) since M30.6 | Default **on**, globally, for all capabilities - the core of this milestone |
| `enable_legacy_decision_fallback` | Not yet introduced in code (named only in the migration plan's own flag table) | Must be introduced, default **on** - this is the actual fallback-reachability switch M30.8 needs; distinct from the flag above |
| `enable_workflow_continuation_mode` | On in verification, default off in code (`URI_ENABLE_WORKFLOW_CONTINUATION_MODE`, M30.7) | Must already be provably safe at default-off *and* correctly on, per M30.7's own closed disposition - no change needed, just must not regress |
| `CANONICAL_EXECUTION_ALLOWLIST` | Hardcoded frozenset, not an env-gated flag | Must be explicitly resolved per §6's open question above - either retired or deliberately widened, and that decision documented, not left ambiguous |

## 8. Rollback strategy

Per the migration plan's own §17 row M30.8: **"Flag off - full return
to pre-migration behavior."** This is the single lowest-risk rollback
in the entire migration sequence after M30.1-M30.7's own (all
flag-flip reversible) - unlike M30.9 (flag off = no regression, just
no improvement) or M30.10 (irreversible, code deleted), M30.8's
rollback restores the *exact* pre-migration priority chain, which the
plan is explicit "still exists and still works." Concretely: unset
`enable_decision_engine_live` (or set it back to the M30.6 allowlist)
and the legacy five/six-mechanism chain resumes full authority,
unchanged since it was never deleted, only demoted in priority.

## 9. Test layers

Per §17 row M30.8: **Full Layer 1 + 2 + 3** (the strongest bar of any
milestone before M30.10):

- **Layer 1 (component/unit):** every existing suite this session
  independently re-ran stays green (`test_decision_engine.py`,
  `test_decision_gates.py`, `test_turn_state.py`,
  `test_canonical_execution.py`, `test_multi_action_capabilities.py`,
  `test_capability_planner.py`, `test_capability_directory.py`,
  `test_gmail_connection_truth.py`, `test_workflow_continuation.py`) -
  none should need deletion at M30.8 (that's M30.10's job); if any of
  these now needs to *change* because the mechanism it tests is being
  demoted, that is itself a signal the change is bigger than a flag
  flip.
- **Layer 2 (integration):** Directory adapter parity across both
  backing stores at global scale (§6 risk above), gate-interaction
  coverage for every capability now reachable, not only the two
  previously allowlisted.
- **Layer 3 (canonical agent-loop, mandatory):** all 12 scenarios,
  §14 - see §10 immediately below, this is where the real gap is.

## 10. Live verification scenarios required

The migration plan's own acceptance gate for M30.8 (§16/§17) is **"all
12 mandatory scenarios (§14) passing live"** - not the M30.6 subset
(1, 2, 3, 6, 9, 10) nor the M30.7 subset (4, 11). Assessed against
every real live-verification report produced this session
(M30.6, M30.6A, M30.7 v2-v4):

| # | Scenario | Live-proven so far? |
|---|---|---|
| 1 | Gmail unread count, connected | Yes - real, both legacy (M30.6 §9) and canonical (M30.6A final verification) |
| 2 | Gmail unread count, disconnected | Partial - M30.6 observed a real `DISCONNECTED` gate outcome, but that was *before* M30.6A's connection-truth fix; not re-confirmed live post-fix |
| 3 | Multi-action (`list_labels` + `search_messages` back-to-back) | **Not confirmed live** - M30.6 §9 proved multi-action chaining only via a fake-connected `GmailService` double, explicitly disclosed as such, never against the real account |
| 4 | "Find the student." → "B250012CS." continuation | Partial, documented residual - resume/execute half real; organic pause-creation half not yet organically observed (M30.7's own accepted residual) |
| 5 | Unsupported request, no clarification loop | **Not confirmed live** in any report read this session |
| 6 | "I work at NIT Sikkim." → `remember_fact` | Yes - real, live, repeatedly (M30.6 §10) |
| 7 | Grounded follow-up chain (search → read → attachment) | **Not confirmed live against the real account** - M30.6 §9/§11 explicitly proved this only via the fake-connected `GmailService` double |
| 8 | `create_draft` approval-pending, no send path | **Not confirmed live** in any report read this session |
| 9 | "Convert this PDF to Word." (unchanged legacy mechanics) | **Not confirmed live** in any M30 report read this session |
| 10 | "Do you think changing careers is sensible?" → `conversation` | **Not confirmed live** in any M30 report read this session |
| 11 | Topic switch clears pending workflow | Yes - real, live, twice (M30.7 v2 and v4 audits, telemetry-cross-checked both times) |
| 12 | Provider failure → honest fallback, never fabricated | **Not confirmed live** in any M30 report read this session |

**Only 3 of 12 (scenarios 1, 6, 11) have unambiguous, real,
non-fake-double live proof.** Scenario 4 is a documented partial.
Scenarios 2 and 3 have real-adjacent but not fully current/real proof.
Six scenarios (5, 7 against the real account, 8, 9, 10, 12) have **no
live evidence at all** in any artifact this pre-audit could find.

## 11. Explicit go/no-go criteria

Per the migration plan itself (§16/§17, verbatim): **"Full regression
suite green; all 12 mandatory scenarios (§14) passing live."** Per
this session's own established audit discipline (M30.6A, M30.7):
**live means through the real `/ask` HTTP path with a genuinely
authenticated principal and real service connections - never a
directly-constructed executor, a bypassed principal, or a fake/double
service standing in for the final acceptance proof.**

**Current status against that bar: NOT MET.** Per §10 above, 9 of 12
scenarios lack full, current, real live proof. This is independent of
M30.7's own residual (which the User has already, separately, and
correctly disposed of as non-blocking) - it is a pre-existing evidence
gap across earlier milestones (M30.6 in particular) that M30.8's own
stricter acceptance bar newly makes consequential, exactly the way
M30.6 made the Gmail connection-truth gap consequential for the first
time (M30.6A's own root cause).

## 12. Whether known residuals from M30.4-M30.7 should block M30.8

- **M30.7's documented residual** (organic trigger for
  `post_execution_reevaluation`): **does not block**, per the User's
  own explicit 2026-09-13 disposition. Correctly closed.
- **`decide_fallback_reason()` telemetry-ordering debt** (M30.6-era,
  recorded as non-blocking debt in `M30_7_STATE.md`): **does not
  block** - cosmetic, execution behavior is unaffected.
- **M30.5A's own undocumented model provenance** (this session's
  separate provenance audit found M30.5A never states its model name,
  unlike M30.5B/C/D which explicitly name qwen3:14b): **does not
  block** - a documentation gap, not a correctness concern; recommend
  closing opportunistically, not gating on it.
- **The 6 scenarios with zero live evidence (§10) and the 3 with
  stale/partial evidence: these SHOULD block an M30.8 go decision**,
  because they are exactly what the migration plan's own accepted
  acceptance gate for this specific milestone requires, not an
  optional nice-to-have. This is a stronger, more directly on-point
  reason to hold than any of M30.4-M30.7's own already-disclosed
  residuals.
- **The `CANONICAL_EXECUTION_ALLOWLIST` reconciliation question (§6)
  and the unconfirmed M30.2 `WorkflowPlanner` template inventory
  (§6)** are open architectural questions a real M30.8 plan must
  answer explicitly - not blocking *this pre-audit*, but they should
  block treating any future M30.8 plan as ready to implement until
  answered.

---

## Recommendation (not a decision - the User's alone)

**Do not authorize M30.8 yet.** The single largest gap is not
M30.7's already-resolved residual, but that **9 of the migration
plan's own 12 mandatory acceptance scenarios have no current, real,
non-fake-double live proof** - a bar the plan's own text sets for this
exact milestone, not one this pre-audit is inventing. The smallest
correct next step, if the User wants to proceed toward M30.8, is a
bounded, User-approved milestone whose sole job is closing that live-
evidence gap (scenarios 2, 3, 5, 7, 8, 9, 10, 12) against real
accounts/services under the *current* (M30.6-M30.7) allowlist-scoped
system, before any global authority cutover is attempted - proving the
canonical path works for what it already governs, before making it
govern everything.

---

Stopping here per explicit instruction. No plan drafted, no
implementation performed, M30.8 not authorized and not started.

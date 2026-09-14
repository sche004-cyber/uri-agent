# M30.7A - Canonical Live Evidence Closure (Plan)

STATE: ACCEPTED (plan only) - implementation NOT yet performed. Claude
(Architect/Planner) output per the standing AO-4 development cycle,
produced from direct inspection of current source (not assumed) and
from `docs/plans/M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md`'s own
findings, which this milestone exists to close. Sibling state file:
`docs/plans/M30_7A_STATE.md`.

**Authorization note (disclosed, not silently accepted):** the prior
handoff's approval record (`URI_ACTIVE_MILESTONE.md` §6a) shows
`APPROVAL RELAY: USER DIRECT` - the User authorized this milestone
directly to Antigravity, not through Claude as the standing User
Approval Channel Protocol otherwise specifies. Claude did not receive
this approval directly and cannot independently verify it beyond the
governance file's own record and the verbatim mandate's content, which
matches Claude's own pre-audit findings closely enough (exact scenario
numbers, exact phrasing) to be very likely genuine. Proceeding on that
basis - this plan is pure architecture/planning work, low-risk and
fully reversible (no code changes, no commit/push, no M30.8 start) -
but this deviation from the stated channel is flagged here explicitly
for the User's own awareness, not silently normalized.

Scope authority: exactly the User's own verbatim mandate (quoted in
full in `uri_workspace/dev_workflow/tasks/claude_m30_7a_plan_task.txt`)
and `M30_8_CANONICAL_DEFAULT_CUTOVER_PRE_AUDIT.md` §10-§12, which this
milestone was created to act on. M30.8 itself (global cutover, legacy
retirement) is explicitly out of scope and must not be started.

---

## 1. Objective

Close the live-evidence gap the pre-audit found: prove or honestly
disposition all 12 of the migration plan's mandatory acceptance
scenarios (§14) under the **current, unchanged, allowlist-scoped**
canonical system (`CANONICAL_EXECUTION_ALLOWLIST = {"Gmail",
"remember_fact"}`, unchanged by this milestone) - not by expanding
canonical execution's reach, only by exercising what it already
governs, honestly, against real accounts and the real `/ask` path.

## 2. Per-scenario disposition rubric (binding on Codex)

Exactly the four outcomes the User's mandate specifies - no other
label is acceptable in the final report:

- **LIVE_PASS** - proven through the real `/ask` HTTP path, a
  genuinely authenticated principal, and (where the scenario names an
  external system) the real service - never a directly-constructed
  executor, a bypassed principal, or a fake/double service. This is
  the exact bar Claude's own M30.6A and M30.7 audits already applied;
  Codex should hold itself to it without waiting for Claude to catch a
  shortcut after the fact.
- **LIVE_FAIL** - attempted for real, genuinely did not produce the
  expected behavior. Report exactly what happened, do not soften or
  omit.
- **BLOCKED_BY_CURRENT_SCOPE** - the scenario's capability is not in
  `CANONICAL_EXECUTION_ALLOWLIST` (or otherwise not currently reachable
  under today's system) - record this honestly rather than fabricating
  a canonical pass, or forcing an allowlist change (out of scope, §7).
- **DOCUMENTED_ACCEPTED_RESIDUAL** - used only for scenario 4, pointing
  at `docs/plans/M30_7_STATE.md`'s and `docs/plans/M30_7_CLAUDE_AUDIT.md`'s
  own already-closed disposition. Do not re-litigate M30.7.

## 3. Per-scenario execution notes (from direct source/evidence review)

| # | Scenario | Current evidence state | What Codex must do |
|---|---|---|---|
| 1 | Gmail unread count, connected | Real live proof exists (M30.6 §9, M30.6A final verification) | Re-confirm still real post-M30.6A/M30.7 changes; cheap, low-risk re-check |
| 2 | Gmail unread count, disconnected | Stale - predates M30.6A's connection-truth fix | Re-run with a genuinely disconnected/invalid token state; confirm `DISCONNECTED` gate outcome and real connection-guidance message, not a generic error |
| 3 | Multi-action (`list_labels` + `search_messages`) | Only ever proven via a disclosed fake-connected `GmailService` double (M30.6 §9/§11) | Re-run for real against the live account; if the real account's data makes back-to-back chaining hard to observe cleanly, document exactly what was tried and why, never substitute the double again |
| 4 | "Find the student." → "B250012CS." | `DOCUMENTED_ACCEPTED_RESIDUAL` per explicit User disposition | Record only - cite `M30_7_STATE.md`/`M30_7_CLAUDE_AUDIT.md`, do not re-attempt live |
| 5 | Unsupported ("Schedule a recurring job search") | No live evidence found in any report this session | Real `/ask` call; confirm `unsupported` outcome, honest message, no clarification loop, nothing executes |
| 6 | "I work at NIT Sikkim." → `remember_fact` | Real, live, repeated proof exists (M30.6 §10) | Re-confirm still real; low-risk |
| 7 | Grounded chain (search → read → attachment) | Only ever proven via the disclosed fake-connected double (M30.6 §9/§11) | Re-run for real against the real account with a real multi-message thread if one exists; if no real attachment-bearing thread is available, report that honestly as a real environmental limit, not a reason to fall back to a double |
| 8 | `create_draft`, approval-pending, no send | No live evidence found | Real `/ask` call proposing a draft; confirm `approval_required`/`awaiting_approval` state, drafted content shown, and - structurally, by inspecting `GmailService`'s own source, not just this turn's behavior - that no send-capable method exists anywhere reachable from this path (already true per `uri_core/services/gmail_service.py`'s own docstring; Codex should cite the specific absence, not just assert it) |
| 9 | "Convert this PDF to Word." | No live evidence found; capability is legacy (`convert_document`), not M27/Gmail-shaped | **Check allowlist membership first.** `convert_document` is not in `CANONICAL_EXECUTION_ALLOWLIST` today - record `BLOCKED_BY_CURRENT_SCOPE` unless Codex confirms the legacy path itself still independently satisfies this scenario's own intent (unchanged legacy mechanics, per migration plan §1's own "executes exactly as it does today" note for this scenario) - if so, that is a legitimate `LIVE_PASS` of the *legacy* path, not the canonical one; label which path was actually exercised, do not conflate the two |
| 10 | "Do you think changing careers is sensible?" → `conversation` | No live evidence found | Real `/ask` call; confirm `conversation` mode, no capability considered, no tool call |
| 11 | Topic switch clears pending workflow | Real, live, twice, telemetry-cross-checked (M30.7 v2 and v4) | Already closed - cite existing evidence, no need to repeat unless something upstream regressed |
| 12 | Provider failure → honest fallback | No live evidence found | Requires a genuine provider-unavailable condition (e.g. point `ModelRouter` at an unreachable endpoint for one real call, or use whatever existing test hook already exists for this - check `test_ollama_reasoning_adapter_live.py`/`ModelRouter`'s own health-tracking tests first rather than inventing a new mechanism); confirm an honest "could not reason about this right now" outcome, never a fabricated result |

## 4. Allowlist / M30.8 precondition - the required decision

Per the User's mandate, resolve (not implement) which of A/B/C/D fits:
**A.** remove/bypass the allowlist entirely, **B.** convert it to a
denylist/safety-exception list, **C.** preserve it only for
risky/write-capable capabilities, **D.** another architecture-
consistent design.

Claude's own recommendation for Codex to evaluate against real
evidence (not to implement, only to weigh): **C, refined** - convert
`CANONICAL_EXECUTION_ALLOWLIST`'s role from "the only capabilities
canonical execution may ever touch" to "capabilities that still
require an explicit human-reviewed addition before canonical execution
may touch them for the first time" is really just A with a one-time
audit step per capability, which is what M30.6's own "expand the list
only as each addition's own Layer 3 tests pass" language already
intended long-term. A pure denylist (B) risks the exact failure this
migration exists to prevent - a new capability silently gets full
canonical authority the day it's registered, with no per-capability
Layer 3 evidence bar, unless something else enforces that bar
structurally. **Codex/Claude's future M30.8 plan should treat this
section's evidence (§3 above - which capabilities are even reachable
today) as the actual deciding input**, not resolve it in the abstract;
this plan only frames the options, per the mandate's own "do not
implement this yet, record the required decision."

## 5. Structural demotion audit (required, evidence-based, not flag-trust)

Per the mandate: "Do not trust the flag flip alone." For each
mechanism, Codex must produce **the exact call path/condition** under
which it would still be reached during *normal, successful* canonical
operation once `enable_decision_engine_live` is imagined flipped
globally on (a dry structural trace, not an actual global flip - that
remains M30.8, out of scope here):

- `capability_planner.py` - trace every current call site; confirm
  each maps to exactly one of its two sanctioned M30.8 roles
  (Unsupported-Gate cross-check, unreachable-model/malformed-contract
  fallback) - if a call site fires unconditionally regardless of
  Decision-Engine success, that is a structural finding, not
  acceptable to wave through.
- `skill_memory.py` - confirm the direct-plan shortcut line still
  exists today (it has not been removed - that is explicitly M30.8's
  own job, not M30.7A's); document its exact current call site and
  condition so a future M30.8 plan knows precisely what to remove.
- `WorkflowPlanner`/`WorkflowCapabilityRouter` - confirm whether M30.2's
  own template inventory (named as a dependency in the migration plan,
  §17 row M30.2) was ever actually completed and reconciled against
  production capabilities; the pre-audit could not confirm this from
  documentation alone - Codex should check for its own artifact
  (an inventory doc/list) and report definitively found/not found.
- `MultiActionDispatch` - confirm the migration plan's own claim that
  it "essentially never fires" (root-cause audit §4, item 2) still
  holds today, or whether M30.6/M30.7's own additions changed that.
- **Any other implicit priority ordering** Codex finds while doing this
  trace that this plan did not anticipate - report it, do not silently
  fix it (unless it is the specific, narrow, already-scoped
  `pre_execution_check` finding in §6 below).

**If any old mechanism would still independently compete with the
Decision Engine during normal successful canonical operation, mark
M30.8 NOT READY in the final report** - this is the mandate's own
explicit instruction, not a suggestion.

## 6. `pre_execution_check` capability_id-threading audit - finding already confirmed, fix specified

Claude traced this directly this round (not left as an open question
for Codex): `orchestrator.py:4586-4599`, the `clarification_needed`
branch of the pre-execution sanity check, calls `_apply_
clarification_pause` with no `capability_id` - but
`model_capability_proposal` (the Brain's own original single-capability
proposal, computed at line ~4521 and still in scope at this exact
point) is real, already-available data, structurally identical to what
M30.7's REVISION v4 threaded at the `post_execution_reevaluation` site
from `attempt_history[-1]`. **This is a confirmed, real, bounded
defect** (the same class of gap M30.7 fixed for one call site, still
open at a second), not merely a hypothesis to audit further.

**Specified fix, mirroring REVISION v4's exact shape:**
```python
elif pre_execution_check["status"] == "clarification_needed":
    question = pre_execution_check["clarification"]["question"]
    return self._apply_clarification_pause(
        response, question, stage="pre_execution_check",
        session=session, session_id=session_id, user_text=user_text,
        capability_id=model_capability_proposal,
    )
```
`model_capability_proposal` is already a capability-id-shaped value
(consumed elsewhere via `_model_proposed_capability`) - never guessed,
never fabricated, `None` exactly as today whenever the Brain's first
call proposed nothing (workflow-only or empty proposals stay
unaffected). Per the mandate ("route as a bounded repair inside
M30.7A" once confirmed): Codex should apply this fix, add one focused
regression test mirroring `test_workflow_continuation.py::
test_post_execution_reevaluation_threads_last_capability_into_pause`,
and re-run the full M30.7-adjacent regression set - this is in scope
for M30.7A specifically because the mandate authorizes exactly this
one bounded repair once confirmed, and Claude has now confirmed it.

## 7. Full regression requirement

Per the mandate: run the **fresh, full repository suite**, not only
the ~130-test focused M30.7 sweep this session has repeatedly re-run.
Report total passed/failed, and for every failure, whether it matches
the session's own known 8-failure baseline (`step3_test.py::test_drive`,
`step4_test.py::test_download`, `test_m20_feasibility_validation.py`,
`test_m20_recovery_loop.py` x2, `test_m20_semantic_interpreter_
resilience.py` x2, `test_usage_import_boundary.py::
test_orchestrator_newline_count_does_not_increase`) or is genuinely
new. A new failure anywhere blocks `M30.8 READY FOR USER APPROVAL`,
even if every scenario in §3 otherwise passes.

## 8. Output required from Codex

`docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_REPORT.md`, containing:
the 12-scenario matrix (scenario, expected behavior, evidence type,
live status, canonical-path-used?, real-external-system-used?,
residual/blocker, artifact/log reference - exactly the columns the
mandate specifies), the §4 allowlist recommendation, the §5 structural
demotion audit findings, the §6 `pre_execution_check` fix and its
verification, the §7 regression comparison, and a final, explicit
disposition: **"M30.8 READY FOR USER APPROVAL"** or **"M30.8 NOT
READY - `<exact blockers>`"**. No other conclusion is acceptable per
the mandate's own stop condition.

## 9. Write scope (for Antigravity to record in `URI_ACTIVE_MILESTONE.md` §4 - already scoped there, confirmed matching)

Matches the handoff's own already-recorded scope exactly: `docs/plans/
M30_7A*`, `docs/governance/URI_ACTIVE_MILESTONE.md`, `docs/governance/
URI_AGENT_RELAY.md`, and source files **only** for the one confirmed,
bounded repair in §6 (`orchestrator.py`'s `pre_execution_check` branch
plus its new focused test) - no broader source scope is authorized by
this plan.

## 10. Stop conditions (restated, binding)

Do NOT make canonical execution global. Do NOT start M30.8. Do NOT
retire any legacy mechanism (demotion is *audited and documented* in
§5, never *performed*, in this milestone). Do NOT touch `uri_ui/`. Do
NOT commit or push. Do NOT expand scope beyond §3/§6/§7 above even if
a live attempt surfaces an unrelated, tempting fix - report it for a
future, separately-scoped milestone instead.

## 11. Process note

Marked ACCEPTED under the standing auto-approval rule
(`ORCHESTRATION.md` §1.5) - this is routine engineering/verification
planning within an already-authorized milestone (see the authorization
note at the top of this document regarding the relay-channel
deviation). Claude does not implement or perform live verification
itself; hands off to Antigravity for routing to Codex, per the
standing division of labor this session has followed throughout
(M30.6A, M30.7). Claude will independently re-audit Codex's report
against real telemetry/session-state artifacts before any `M30.8
READY`/`NOT READY` disposition is treated as final - exactly as for
every prior milestone this session.

---

Stopping here. M30.7A plan is ready for Antigravity to route to Codex.
M30.8 is not started and not authorized.

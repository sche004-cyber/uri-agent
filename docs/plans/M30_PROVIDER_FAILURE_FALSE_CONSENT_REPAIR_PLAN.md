# Provider-Failure False-Consent Memory Defect - Investigation & Repair Plan

STATE: ACCEPTED (plan only) - implementation NOT yet performed. Claude
(Architect/Planner) output per the standing AO-4 development cycle, at
the User's explicit direct request. **No production source was
modified to produce this document** - the root cause below was
established entirely by reading source and inspecting real, existing
data files. Sibling state file: `docs/plans/M30_PROVIDER_FAILURE_
FALSE_CONSENT_STATE.md`.

Treated as a **privacy-relevant canonical safety defect**, per the
User's own framing - not an availability/UX gap.

---

## 0. Recap of confirmed behavior (not re-litigated, cited from `docs/plans/M30_7C_CLAUDE_AUDIT.md`)

Independently reproduced twice (Codex, then Claude separately): when
every model role is unreachable, an unrelated user statement ("What is
the weather in Delhi today?") is executed via `remember_fact` and
persisted with `consent: "user_provided"`, while the visible response
claims `"status": "success"`. Real usage-log records confirmed zero
model calls succeeded during the reproduction. Both spurious memory
entries were removed as audit-verification cleanup, disclosed
transparently, prior to this plan.

## 1. Exact deterministic call path - traced to a precise line, not a hypothesis

Traced end-to-end through `uri_core/core/orchestrator.py`'s
`process_user_input`:

1. `semantic_interpreter.interpret(user_text)` raises (the underlying
   `ProviderSemanticInterpreter.interpret()` converts
   `AllProvidersUnreachableError` into a `ValueError`).
2. The caller's own `except Exception:` handler (`orchestrator.py`
   lines 379-392) degrades honestly: `{"goal": user_text, "task_type":
   "", "domain": "", "entities": [], "requested_output": "",
   "requires_evidence": False, "requires_clarification": True,
   "suggested_next_step": "URI could not classify this request
   automatically; the Brain will still reason about it directly."}`.
   **Confirmed correct and honest at this point** - independently
   reproduced this exact dict as the real `semantic_analysis` field in
   both live reproductions.
3. `learned_skill = self.skill_memory.find_matching_skill(semantic_result)`
   (`orchestrator.py` line 4301-4305) is called with this degraded
   dict. **`SkillMemory.find_matching_skill()`
   (`uri_core/core/skill_memory.py` lines 129-177) matches purely on
   case-insensitive string equality of `task_type` and `domain`** -
   including when *both* are empty strings. Confirmed directly against
   the real, persisted `uri_workspace/skill_memory.json`: a real entry
   exists (`"task_type": "", "domain": "", ... "tool_name":
   "remember_fact", "success_count": 5, "failure_count": 0`), created
   from an earlier genuine successful disclosure whose own semantic
   classification happened to be empty. A degraded, totally-
   unclassified request (task_type="", domain="") **spuriously matches
   this entry by coincidence of absence, not by relevance** - the
   confidence-floor check (`self.confidence(skill) < CONFIDENCE_
   RECALL_FLOOR`) does not help, since this entry's real 5/0 success
   record gives it high confidence for entirely the wrong reason.
4. `model_reasoning` also fails (same unreachable provider) →
   `model_capability_proposal = self._model_proposed_capability(model_
   reasoning)` correctly returns `None` (its own internal guard,
   `model_reasoning.get("status") != "reasoning_completed"`, fires
   first - confirmed by direct reading, `orchestrator.py` line
   1034-1035) → `model_workflow_proposal_present` is also `False`
   (same guard, `_strict_model_proposed_workflow`/`_model_proposed_
   workflow`, `orchestrator.py` lines 1261-1262).
5. **The exact defect site:** `orchestrator.py` lines 4704-4767's
   plan-selection cascade:
   ```python
   if model_capability_proposal is not None:
       plan = {...}                     # not taken - None
   elif model_workflow_proposal_present:
       plan = {...}                     # not taken - False
   elif learned_skill:                  # <-- TAKEN: the spurious match from step 3
       plan = {
           "status": "capability_selected",
           "tool_name": learned_skill.get("tool_name"),   # "remember_fact"
           "reason": "No fresh Brain proposal was usable for this "
                      "request; matched a previously learned workflow "
                      "for this task type/domain instead - still "
                      "executed and authorized like a fresh selection.",
           "source": "skill_memory",
           "success_count": learned_skill.get("success_count", 0),
       }
   else:
       plan = capability_planner_plan   # never reached
   ```
   `plan["status"] == "capability_selected"` then flows directly into
   `self.approval_gate.execute_tool("remember_fact", session_id=...,
   request_text=user_text, ...)` (`orchestrator.py` line 4774-4779) -
   **real execution, no model ever consulted, no capability_planner
   consulted, no genuine disclosure-intent signal checked at all.**

**This resolves a documentation/architecture discrepancy found during
tracing, worth stating plainly:** the migration plan's own component
matrix (§1) and several in-code comments (e.g. "URI Correction Part 1:
the single line that turns a skill match directly into a plan is
removed") describe learned-skill matching as already demoted to
"Turn State reference hint only, zero plan authority." **That
demotion was implemented for the model's own prompt context
(`session_context["learned_skill_reference"]`, lines 770-780) but not
for this separate, still-fully-active direct-execution branch
(lines 4742-4762).** Two different code sites, one demoted, one not -
the surviving one is the actual defect's execution authority.

## 2. Resolving `_run_acceptance_retention_step`/`_model_retention_candidate` - RULED OUT, not merely re-asserted

Traced their real call path this round, not left open:
`_run_acceptance_retention_step` is only reachable from
`_continue_brain_evaluation_loop`, itself only entered *after* an
initial real execution already occurred (`_is_paused_execution` guard,
line 2612), and only reaches the retention step after a **second,
separate, successful** model call: `evaluation =
self._model_evaluation(model_reasoning)` followed by `if evaluation is
None:` (lines 2651-2676) returning early with an honest
`"evaluation_unavailable"`/`satisfied: False` result whenever that
second call also fails - which it always will under total provider
unreachability, since it uses the same `_run_model_reasoning()`
mechanism already shown to fail. **`_run_acceptance_retention_step`
is never reached under the reproduced condition, and is unrelated to
this defect.** No related fallback/default logic was found in this
function or its caller that bears on the actual defect (§1) - the
defect is fully contained within the *first* plan-selection cascade
described above, well before any re-evaluation loop could run.

## 3. Where `user_provided` consent/provenance is assigned

`uri_core/tools/remember_fact.py` (module docstring, lines 6-16):
writes only via `MemoryStore.add()`, which is `consent="user_provided"`
**by construction, unconditionally** - the tool's own documented
design premise is "the user directly told URI to remember this;
consent is inherent in the request," and explicitly states
"`capability_planner.py`'s scoring keeps that narrow" as its assumed
safety boundary. **`remember_fact.py` itself is not defective** - it
correctly implements "if I am called, an explicit disclosure already
occurred," a premise that was true for every route into it the tool's
own author accounted for (Brain proposal, `capability_planner.py`
scoring) but not for the `learned_skill` direct-execution branch found
in §1, which the tool's own documentation does not mention and was
evidently not built to anticipate.

## 4. The invariant to enforce (binding on the repair, User-refined)

**Architectural clarification from the User, superseding this
section's earlier draft:** the canonical invariant to restore is
**"learned skills must not have independent direct execution
authority"** during a genuine model-failure state - not a blanket ban
on the existing, intentional learned-skill fast-path.

**Why not a blanket ban - a real conflict found and reported before
implementation, per the User's own instruction:** `test_orchestrator_
skill_memory_execution.py` (6 tests, currently passing, independently
re-run this round: 6/6) exists specifically to prove learned skills
*do* genuinely execute with no fresh Brain proposal - its own docstring:
"a learned skill only ever accelerates tool SELECTION - it must never
substitute for actually executing the tool" (the prior "Issue-1" bug
was a *fake* execution, not real skill-driven execution itself, which
is the intentional, tested feature). Unconditionally removing
`learned_skill`'s execution authority would reverse this intentional
behavior and break all 6 tests - reported to the User as this exact
architectural consequence; the User then specified the precise,
narrower condition below instead of the blanket removal.

**Final, User-specified condition - "model-failure state":** the
`elif learned_skill:` fast path (`orchestrator.py` lines 4742-4762)
may fire only when the current turn is **not** in a model-failure
state, defined as: URI attempted a required model call for this turn,
that call did not return a successful result, and the failure was
explicit/unreachable/timeout/fallback-exhausted. **Explicitly not**
model-failure state: a model role that was never attempted at all
(e.g. `enable_model_reasoning_shadow=False`, which returns `status:
"reasoning_disabled"` immediately - `orchestrator.py` lines 693-698 -
without ever calling the model; confirmed this is exactly what all 6
existing tests' fixtures do, via `_FixedSemanticInterpreter` and
`enable_model_reasoning_shadow=False`). "Disabled" (never attempted)
and "failed" (attempted, then unreachable) are categorically different
per the User's own three-part test, and only the latter triggers this
gate - **verified this distinction directly against the 6 existing
tests' real fixtures before finalizing, not assumed:** none of them
attempt a real model call for either semantic interpretation (fake
interpreter, returns a canned dict, never raises) or reasoning
(explicitly disabled) - so none trigger the gate, and all 6 remain
green under this condition.

**Precision required in implementation, flagged now rather than left
implicit:** `orchestrator.py`'s current semantic-interpretation
except-handler (lines 379-392) catches *all* exceptions from
`interpret()` identically - it does not currently distinguish genuine
unreachability (`AllProvidersUnreachableError` → `ValueError`, per
`provider_semantic_interpreter.py` lines 171-174) from a reached-but-
malformed response (`_parse()`'s own `ValueError` for bad JSON/missing
keys). Only the former is "explicit/unreachable/timeout/fallback-
exhausted" per the User's own definition - a malformed-but-reached
response means a model *was* consulted, just badly, which is not the
same failure class. The repair must distinguish these two cases (e.g.
a small, additive marker on the degraded dict, such as
`"interpretation_unreachable": True`, set only for the genuine-
unreachability branch) rather than treating every exception path
identically.

## 5. Provider-failure degradation requirement (binding on the repair, broadened per 2026-09-13 product review)

In a genuine model-failure state (§4's precise definition): **do not
execute `learned_skill`, do not execute `remember_fact`, do not
perform any persistent side effect, do not execute any approval-gated
action, do not execute any other side-effecting capability** - the
last two broaden this section's original wording per the User's own
explicit product review (`docs/plans/M30_8_BLOCKER_DISPOSITION_PLAN.md`
§ Product Decisions item 1). **Checked directly - already structurally
satisfied, no additional source change implied:** the only *other*
route into approval-gated/side-effecting execution besides
`learned_skill` is `capability_planner_plan`, which is already
independently verified (tested empirically this session) to return
`"planning_required"`/`tool_name: None` for the exact degraded input -
it cannot select an approval-gated or side-effecting capability from a
genuinely empty/degraded classification. **Recommend one additional
test** (§6 below, within the already-approved test budget) confirming
this explicitly rather than leaving it merely inferred. Return a
deterministic,
honestly-worded model-unavailable response instead of `capability_
planner.py`'s generic "no capability confidently matches" message
(which is accurate for a genuine capability gap, but misleading here -
the real reason nothing happened is model unavailability, not a
missing capability). Reuse the existing, already-proven honest-
degradation pattern this session's own audit found in `response_
drafting.py` (`narrative_unavailable_reason: "drafting_provider_
unreachable"`) as the template for this response's wording/shape,
rather than inventing a new mechanism - the migration plan's own
failure-handling table (§11) already names "Model provider
unavailable" as a case with its own honest template. `capability_
planner.py` itself needs no change - it is already independently
verified to return `"planning_required"`/`tool_name: None` for the
exact degraded input (tested directly this session); it simply must
not be the *only* thing standing between a model-failure turn and an
honest response once `learned_skill` is correctly gated off.

## 6. Required tests (specification only - not written here)

All new, all real (constructing the exact degraded `semantic_result`
shape and a real or fake `SkillMemory`/`CapabilityPlanner`/reasoning
gateway, per this repository's own existing test conventions - e.g.
`test_orchestrator_skill_memory_execution.py`'s and `test_m20_
semantic_interpreter_resilience.py`'s own patterns):

1. **Total provider failure + unrelated request cannot execute
   `remember_fact`:** a genuinely-unreachable semantic interpreter
   (raises `AllProvidersUnreachableError`-shaped failure, not a fake
   canned dict) plus a `SkillMemory` containing the real, confirmed
   problem shape (an empty-`task_type`/`domain` entry with
   `tool_name="remember_fact"`) must **not** result in `remember_fact`
   executing - matches §5's honest model-unavailable response instead.
2. **No persistent memory side effect occurs:** same scenario, zero
   calls into `ApprovalGate.execute_tool("remember_fact", ...)` and
   zero `MemoryStore.add()` calls - verified via a fake/spy dispatcher
   or `MemoryStore`, not by inspecting real files.
3. **No false `user_provided` provenance is created:** explicit,
   separate assertion that `MemoryStore.add()` is never called at all
   for this scenario - the consent tag is never even in question.
4. **Empty degraded task/domain cannot resolve to an executable
   learned skill:** a direct unit test of `SkillMemory.find_matching_
   skill()` (or the gated call site) confirming an empty-vs-empty
   classification never resolves to a usable match, independent of
   the model-failure-state gate - defense-in-depth per Option B,
   bounded to this one matching function.
5. **Learned skills cannot independently bypass live-turn decision
   authority:** a model-failure-state turn (per §4's precise
   definition - a real attempted-and-failed call, not a disabled one)
   with a `SkillMemory` that *would* otherwise match confidently (a
   genuine, non-empty `task_type`/`domain` entry, success_count > 0)
   must still not execute via the learned-skill path - proving the
   gate keys on turn state, not on the emptiness of the match alone.
6. **Genuine explicit memory requests still work when the provider
   path is healthy:** a real or faked *successful* reasoning/semantic-
   interpretation call for "I work at NIT Sikkim."-shaped text must
   still route to `remember_fact` and persist exactly as today.
7. **Existing legitimate learned-skill behavior is not silently
   broken:** re-run `test_orchestrator_skill_memory_execution.py`
   unchanged and confirm all 6 still pass exactly as today (their
   fixtures never attempt a real model call, so the new gate must not
   fire for them) - this is the direct regression proof for the
   conflict identified and reported in §4, not merely assumed resolved.
8. **Exact previously reproduced failure, re-run against the same real
   server, after the repair:** the literal scenario from `docs/plans/
   M30_7C_CLAUDE_AUDIT.md` (`OLLAMA_BASE_URL` unreachable, real
   authenticated `/ask`, "What is the weather in Delhi today?") must
   return an honest model-unavailable response with zero new memory
   entries - the live proof this defect is actually closed, not only
   unit-proven.
9. **No approval-gated or other side-effecting capability executes
   either, during a model-failure-state turn** (added per 2026-09-13
   product review, §5): confirms `capability_planner_plan`'s own
   already-correct behavior explicitly, for a capability that *would*
   require approval (e.g. `create_draft`) or otherwise have a side
   effect, using the same degraded `semantic_result` as test #1 - not
   expected to require any source change to pass, given §5's own
   analysis, but must be proven, not assumed.

## 7. Bounded repair - explicitly scoped, no architecture redesign, User-approved direction

**Approved repair, exactly as specified by the User (supersedes this
section's earlier "either/both" framing):**

- **Primary - gate `orchestrator.py`'s `elif learned_skill:` branch
  (lines 4742-4762) on "not in model-failure state"** (§4's precise
  definition). This restores "learned skills must not have independent
  direct execution authority" specifically for the case that actually
  caused the defect (a turn where a real model call was attempted and
  failed) while leaving the intentional, tested fast-path
  (`test_orchestrator_skill_memory_execution.py`) fully intact for its
  real use case (no fresh Brain call attempted/needed, not "attempted
  and failed"). Requires: (i) the semantic-interpretation except-
  handler distinguishing genuine unreachability from a malformed-but-
  reached response (§4's "precision required" note), (ii) checking
  `model_reasoning.get("status")` for `"reasoning_failed"` (attempted,
  raised) as the reasoning-side half of the same signal.
- **Defense-in-depth - fix `SkillMemory.find_matching_skill()`'s
  matching criterion** (`skill_memory.py` lines 129-177): require at
  least one of `task_type`/`domain` to be genuinely non-empty before
  considering it a match. Bounded (single function), does not change
  legitimate learned-skill retrieval for any real, specifically-
  classified request (verified: none of the 6 existing tests use an
  empty-`task_type`/`domain` fixture). Closes the data-side root cause
  for *any* future degraded-classification scenario, not only this
  provider-failure path - real value beyond just this one defect.

**Neither touches `remember_fact.py`, `MemoryStore`, `user_memory.py`,
or any consent/provenance model (§3, unchanged by User direction) -
those remain exactly as designed.** Neither touches `capability_
planner.py` (already correct, independently verified). **This is not
a memory-architecture redesign** - it is a precise, narrow gate on one
existing branch's precondition plus one matching function's
correctness, both scoped and verified against the existing test suite
before being finalized here, per the User's own explicit "stop and
report before implementation" instruction (§4's conflict-and-
resolution narrative is the record of that check having been done).

## 8. Live verification and regression requirements

- **Live verification:** re-run the exact reproduction from `docs/
  plans/M30_7C_CLAUDE_AUDIT.md` (real loopback server,
  `OLLAMA_BASE_URL` pointed unreachable, real authenticated `/ask` for
  "What is the weather in Delhi today?" or an equivalent unrelated
  statement) after the fix - confirm no `remember_fact` execution, no
  new memory entry, and an honest visible response. Confirm the
  companion healthy-path disclosure case (§6 item 4) still works live,
  not only in unit tests, on the same server.
- **Regression:** full repository suite, compared against the session's
  known 8-failure baseline (`step3_test.py::test_drive`, `step4_
  test.py::test_download`, `test_m20_feasibility_validation.py`,
  `test_m20_recovery_loop.py` x2, `test_m20_semantic_interpreter_
  resilience.py` x2, `test_usage_import_boundary.py`) - allowed to
  finish to a real terminal state, never reported from a killed or
  partial run (this session's own established discipline). Particular
  attention to `test_orchestrator_correction_part1.py`,
  `test_orchestrator_skill_memory_execution.py`, and every M20
  resilience/recovery suite, since they exercise the exact mechanisms
  this repair touches.
- **New tests (§6)** must all be written and passing before this is
  considered closed - not deferred.

## 9. M30.8 status

**M30.8 must remain blocked until this repair is accepted, independent
of M30.7C's own separate evidence-closure status.** This defect is a
real, confirmed, privacy-relevant correctness failure in a mechanism
(`learned_skill` plan authority, `skill_memory` matching) that is
*not* behind the `CANONICAL_EXECUTION_ALLOWLIST` at all - it lives
entirely in the **legacy fallback path** M30.8 would make the
*primary* fallback for every capability, not only the two currently
allowlisted ones. Shipping M30.8 before this is fixed would give this
exact defect a larger blast radius (every capability's fallback path,
not a corner case), not a smaller one. This is independent of, and in
addition to, the six evidence-closure gaps already tracked in `docs/
plans/M30_8_BLOCKER_DISPOSITION_PLAN.md`.

---

Stopping here. No production source modified. No repair implemented -
this plan defines the required investigation-confirmed root cause and
repair scope for the User's review and separate implementation
authorization.

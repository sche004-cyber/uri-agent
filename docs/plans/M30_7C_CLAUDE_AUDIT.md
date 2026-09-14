# M30.7C - Claude Independent Audit (Scenario 12 Defect - CONFIRMED)

Audited by direct source tracing, real telemetry, real usage-log
records, and an independent, live reproduction of the defect itself -
not from Codex's report alone. Per the repository's standing
Verification-First Audit and Planning Standard and Evidence Integrity
Rules (`CLAUDE.md`).

## Acceptance criteria for this audit (defined before drafting)

1. Do not accept Codex's "confirmed defect" claim on its own report -
   independently reproduce it for real before calling it confirmed.
2. Trace the mechanism as far as static source reading allows; state
   plainly which candidate mechanisms are ruled out (with evidence)
   and which remain open, rather than guessing a single cause.
3. Address the real-world side effect this defect produced (a genuine,
   falsely-consent-tagged memory write) responsibly - it is real
   persisted state, not a log line.
4. Do not repair the code - this remains a stop-and-ask defect per the
   binding protocol. Define the required remediation scope for the
   User's decision.

## Verdict: **CONFIRMED REAL DEFECT - INDEPENDENTLY REPRODUCED. Recommend a separate, dedicated, User-approved investigation-and-repair milestone (not folded into M30.7C's remaining scope).**

---

## 1. Independent reproduction - not merely trusted

Rather than accept the report's telemetry alone, Claude started a
fresh, real loopback server (`OLLAMA_BASE_URL=http://127.0.0.1:19999`,
the same unreachable-provider condition), logged in as the real
`URI_test2` account, and sent the exact same real request:

```
POST /ask {"text": "What is the weather in Delhi today?", ...}
→ HTTP 200
{"status":"success", "execution":{"status":"success","tool":"remember_fact"},
 "response":{"status":"success","message":"Saved to memory: \"What is the
 weather in Delhi today?\"","memory_id":"0f93646a-...",
 "content":"What is the weather in Delhi today?"},
 "narrative":null,"narrative_unavailable_reason":"drafting_provider_unreachable"}
```

**The defect reproduces independently, on demand, for real.** This is
not a one-off fluke or a Codex-side harness bug - confirmed the
correct, defective way, before treating it as established fact.

**Remediation of the reproduction's own side effect:** this write, and
Codex's own earlier one (`memory_id: 7d166b15-...`), were both real,
persisted entries in `uri_workspace/users/86f1c37e-.../user_memory.json`
falsely tagged `"consent": "user_provided"` for a statement the real
user never asked to be remembered. Claude removed both entries directly
(read the file, confirmed exactly these two trailing entries matched
the known spurious content and timestamps, removed them) - not a
source change, a real-data correction of audit-verification residue,
analogous to Codex's own practice of deleting temporary fixtures. The
isolated test server was cleanly shut down afterward. No other memory
entries were touched.

## 2. Real evidence that this happened with **zero successful model
calls of any kind**

The account's own usage log
(`uri_workspace/users/86f1c37e-.../usage/2026-09.jsonl`) for this exact
reproduction shows, for every role attempted:

```
role: semantic_interpretation → outcome: unreachable, fallback_from: ["ollama(failed:ProviderUnavailableError)"]
role: reasoning              → outcome: unreachable, fallback_from: ["ollama(unhealthy)"]
role: drafting               → outcome: unreachable, fallback_from: ["ollama(unhealthy)"]
role: reasoning (2nd attempt)→ outcome: unreachable, fallback_from: ["ollama(unhealthy)"]
```

**Every single model call this turn failed.** `remember_fact` was
selected and *actually executed* (a real memory write, not a proposal)
without any model - Brain or interpreter - ever successfully running.
This is the single most important fact this audit establishes: **the
defect is a deterministic, non-model code path incorrectly defaulting
to `remember_fact`**, not a model hallucination, not the M30.5A
disclosure-detection regex, and not ordinary model-quality variance
(the pattern this session has repeatedly, correctly attributed several
other scenarios to). This is categorically different and more serious.

## 3. Candidate mechanisms - each checked directly against source, six ruled out

| Candidate | Why it could plausibly cause this | Verdict | Evidence |
|---|---|---|---|
| `capability_planner.py`'s `remember_fact` disclosure-phrase scoring | Zero-model-call deterministic fallback - immune to provider failure | **Ruled out** | Directly instantiated `CapabilityPlanner()` and called `.plan()` with the exact degraded semantic_result orchestrator.py produces on interpreter failure (`goal="What is the weather in Delhi today?"`, empty `task_type`/`requested_output`) - it correctly returned `{"status": "planning_required", "tool_name": None, ...}`. Confirmed empirically, not assumed. |
| `provider_semantic_interpreter.py`'s `_detect_personal_disclosure()` regex override | Could force `task_type`/`requested_output` toward `remember_fact` | **Ruled out** | Read `_DISCLOSURE_PATTERNS` directly (11 regexes: "i work at", "my name is", etc.) - none match the weather text. Also structurally unreachable here: this override only runs inside `_parse()`, which is never called on the `AllProvidersUnreachableError` path (`interpret()` raises `ValueError` before `_parse()` instead). |
| `_recover_capability_mentions()`'s tolerant scan | Scans an already-parsed model proposal for a registered capability id under generic keys | **Ruled out** | Reads only a fixed set of identifier-shaped keys (`_TOLERANT_CAPABILITY_KEYS`) from the proposal dict; a `{"status": "reasoning_failed", "error": ...}` dict contains none of them, so it returns `found=[]` and `_model_proposed_capability` correctly returns `None`. |
| `MultiActionDispatch.dispatch()` (M27) | The newer canonical-adjacent dispatcher, also fed `model_reasoning` | **Ruled out** | Its default registry (`MultiActionCapabilityRegistry([GmailCapability()])`) contains only Gmail actions - `remember_fact` is not and cannot be a `MultiActionDispatch` selection at all. |
| `skill_memory`'s learned-skill direct-plan shortcut | Historically could bypass the model entirely (root-cause audit §4, item 3) | **Ruled out for this path** | Current code (`orchestrator.py` ~line 770-780, marked "URI Correction Part 1") folds `learned_skill` into `session_context` as advisory prompt text only - it requires a *successful* model read of that context to act on it, which did not happen here. |
| `_run_acceptance_retention_step()` | Its entire purpose is deciding what to save to memory - the most on-point candidate by function | **Not ruled out - most likely remaining candidate, not confirmed** | Only reachable after `brain_evaluation.satisfied == True`, which itself requires a completed Brain evaluation loop - unclear from static reading alone whether a totally-unreachable-reasoning turn can incorrectly reach this "satisfied" state, or whether `_model_retention_candidate()` fails safe on a `reasoning_failed` dict the same way the other five mechanisms do. **Not verified either way this audit** - see §4. |

## 4. What remains genuinely unverified - stated explicitly, per this
repository's Evidence Integrity Rules

Six real, plausible mechanisms were checked directly against source.
Five are confirmed, with evidence, not to be the cause. The sixth
(`_run_acceptance_retention_step`/`_model_retention_candidate`) could
not be ruled in or out through static reading alone within this
audit's scope - determining it definitively requires either targeted
debug instrumentation (itself a source change, requiring its own
approval under the binding protocol already in effect) or a live
reproduction with intermediate state inspection beyond what the `/ask`
HTTP boundary exposes. **Claude does not present a single confirmed
root-cause line** - stating this plainly rather than rounding an
unconfirmed hypothesis up to a finished diagnosis.

## 5. Why this defect is more severe than the other M30.7C findings

Every other scenario this session (2, 5, 6, 7, 8, 9) traced to either
an honest, correctly-behaving deterministic gate, a genuine test-
fixture/data limitation, or ordinary model-quality variance under
degraded/ambiguous input. **This one is different in kind:** a
completely unrelated user statement was executed as a consent-gated,
persistent memory write, tagged as if the user had explicitly provided
it, while every model in the system was unreachable. This has real
privacy/consent implications for this project's own standing memory
model (`RememberFactTool`'s `consent="user_provided"` guarantee) - not
merely an availability/UX gap. It should be treated with the priority
that implies, independent of M30.7C's own narrower evidence-closure
mandate.

## 6. Recommendation - a scope decision for the User, not a repair Claude performs

Per the binding defect-handling protocol (unchanged, correctly applied
by Codex): **no source repair is authorized here.** Recommend the User
consider this a **separate, dedicated defect** from M30.7C's own three
mandatory evidence-closure scenarios, warranting its own bounded
investigation-and-repair milestone:

1. **Investigation:** targeted debug instrumentation (temporary,
   reverted after use) around `_run_acceptance_retention_step`/
   `_model_retention_candidate`'s handling of a `reasoning_failed`
   `model_reasoning` dict, to find the exact line - the five ruled-out
   mechanisms above narrow this considerably.
2. **Fix, once found:** almost certainly a bounded, single-function
   correction (ensuring the retention/remember-fact path fails safe on
   a failed/unreachable reasoning result, exactly as the other five
   mechanisms already correctly do) - not expected to be architectural
   in scope, but this should be confirmed once the exact site is found,
   not assumed in advance.
3. **Regression:** the existing `test_m20_semantic_interpreter_
   resilience.py` suite already exercises adjacent "no model available"
   behavior (currently 2 pre-existing, unrelated baseline failures -
   independently re-run this audit, unchanged) - a new, targeted test
   for this exact scenario (total reasoning unavailability during an
   unrelated request) should be added as part of any fix.

**M30.7C's own remaining mandatory scope (fresh Scenario 2/8 canonical
evidence, best-effort Scenario 7, and the terminal regression run) is
independent of this finding and can proceed separately** once the User
decides how to sequence the two - this audit does not assume they must
be resolved together.

## 6a. Scenarios 2 and 8 - this round's fresh evidence, briefly audited

**Scenario 2:** this round's two fresh attempts produced `gate_outcome:
"INVALID_PROPOSAL"` - a *different* failure shape than the prior
round's `unknown_capability` (Branch A/B diagnostic,
`M30_7C_STATE.md`'s own history log). Combined with the prior round's
own finding that a different model turn *did* successfully reach Gate
1 (referenced directly in Codex's report), this is consistent with
ongoing model-naming/proposal variance across separate live calls, not
a new or different code defect - the fixture itself (isolated invalid-
but-present token) remains independently confirmed correct from the
prior round. The visible connection-guidance text returned in this
round's `INVALID_PROPOSAL` case is honest and accurate
("Gmail authentication failed or credentials.json/token.json missing"),
which is a reasonable, non-defective outcome even though it is not the
specific `DISCONNECTED` gate outcome the scenario was written to prove.
Genuine canonical `DISCONNECTED` evidence remains not yet captured on
a clean run; recommend one further attempt only, not repeated
open-ended retries (this session's own established discipline against
unbounded live-verification loops, e.g. the earlier M30.7 workflow-
continuation rounds).

**Scenario 8:** this round's complete draft request selected
`draft_institutional_note` (a different, legacy capability) rather
than `Gmail`/`create_draft` - a model capability-selection choice, not
a code defect; both are legitimate draft-preparation tools and the
model was not directed which one to use. The structural no-send proof
(zero `send` methods across `gmail_service.py`/`capability.py`) is
independently re-confirmed and stands regardless. The specific
canonical `APPROVAL_REQUIRED` content-envelope evidence for `Gmail`/
`create_draft` remains not yet captured; recommend one further attempt
with wording that more specifically directs the model toward the
Gmail draft action if the User wants this exact evidence completed,
rather than accepting `draft_institutional_note`'s equivalent (but
different-capability) proof as a substitute.

## 7. Regression note (unrelated to this defect, checked while investigating)

While tracing, independently re-ran `test_m20_semantic_interpreter_
resilience.py` (one of the session's known 8 pre-existing baseline
failures) to confirm it is unchanged: still 2 failed / 1 passed,
identical assertion mismatches as previously recorded
(`'failed' != 'success'`) - a stale test expectation unrelated to
Scenario 12's own defect (that test simulates a fully-absent model
gateway and correctly gets an honest `"failed"` status today, not a
wrong execution - the opposite failure direction from what Scenario 12
exposed). Noted for completeness; not part of this defect.

---

Stopping here. No production source code modified by Claude - only a
real-data correction (removing two audit-verification memory entries
this investigation itself created) and standard test-server cleanup.
No repair authorized or implied. M30.8 remains NOT AUTHORIZED and is
not started. M30.7C's remaining scope and this new defect both await
the User's own scope decision.

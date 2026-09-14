# M30.7 Workflow Continuation & Active Pointer - Implementation Report

**Date:** 2026-09-13

## Implemented changes

- Added the default-off `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` gate.
- Added durable clarification proposal metadata and `active_pointer` projection
  without guessing missing values from free text.
- The enabled continuation gate resolves the durable capability/action, merges
  the pending answer, and applies the existing authority checks.
- A ready continuation uses the existing allowlisted canonical executor.
- `/ask` now has a guarded pending-workflow precedence path: execute ready
  continuation early, clear a model-rejected stale workflow, otherwise fall
  back unchanged.
- Added a shared orchestrator pending-interaction accessor. The three pause
  call sites were audited; none has an existing capability/action/input/field
  value at its pause point, so no metadata was fabricated.

## Automated verification

`python -m unittest test_workflow_continuation test_decision_engine test_decision_gates test_turn_state test_canonical_execution test_multi_action_capabilities test_gmail_connection_truth -v`

Result: **123 passed, 0 failed**.

New coverage includes durable projection, enabled active-pointer gate
resolution, flag-off preservation, ready early continuation, topic-change
clearing, and non-ready fallback.

## Mandatory live verification status

| Scenario | Status | Live proof |
|---|---|---|
| 4: authenticated continuation and grounded real execution | Pass | `workflow_continuation` → `Gmail`/`search_messages` → `READY` → `success`; execution evidence and grounded response were returned. |
| 11: authenticated topic change and pointer clear | Pass | Pending workflow was cleared before the fresh weather turn was processed; no legacy resume occurred. |

### Verification method and evidence

The application was exercised through its real FastAPI `/auth/login`,
`/auth/me`, and `/ask` routes with a fresh token from the persisted
`URI_test2` account. The three M30.7 feature flags were enabled for the
verification process. This used the real persisted account, token store,
grant-resolution path, Gmail connection, Decision Engine, deterministic gate,
canonical executor, session store, and append-only canonical telemetry. No
principal, capability grant, service, executor, or model result was mocked or
bypassed. Bearer tokens, token contents, and Gmail content are intentionally
omitted.

**Scenario 4 — continuation and execution.** A pending interaction was set up
with durable, action-specific metadata (`Gmail`, `search_messages`, missing
`query`) and the real authenticated `/ask` answer turn supplied `is:unread`.
The HTTP route returned 200 and a successful result with a successful Gmail
execution, response, and narrative. The matching telemetry record for
`m30-7-live-s4-20260913-c` reports:

- `canonical_mode: workflow_continuation`
- `selected_capability: Gmail`; `selected_actions: [search_messages]`
- `gate_outcome: READY`
- `canonical_execution_attempted: true`; `canonical_execution_result: success`
- `execution_evidence_returned: true`; `grounded_final_response: true`

This proves the active pointer was resolved to its durable action, the gate
authorized the continuation, and the existing canonical execution path
returned grounded evidence.

**Scenario 11 — fresh intent clears a pending workflow.** A real pending
workflow (`Gmail`, status `waiting_for_input`) was set up, then the authenticated
`/ask` route received `What's the weather like?`. The first canonical telemetry
record for `m30-7-live-s11-20260913-a` was a non-continuation
`unsupported` decision with `gate_outcome: INVALID_PROPOSAL`; therefore the
guarded `/ask` branch cleared the active workflow and fell through. The fresh
turn completed with HTTP 200, response, and narrative. Persisted session state
after the request had `active_workflow: null` and
`active_workflow_status: null`; a second canonical record was then emitted for
the fresh turn. This is the required early model judgment, clear, and fresh
processing path rather than a blind legacy resume.

## Revision v3 organic live verification (2026-09-13)

The prescribed loopback server was started with all three flags enabled:
`URI_ENABLE_WORKFLOW_CONTINUATION_MODE=1`,
`URI_ENABLE_DECISION_ENGINE_LIVE=1`, and
`URI_ENABLE_DECISION_ENGINE_SHADOW=1`. Authentication used a fresh bearer
token obtained from the real `/auth/login` route for `URI_test2`. No session
fixture, direct state mutation, or substitute principal was used. Student
record contents, bearer tokens, and raw telemetry are intentionally omitted.

| Scenario | Result | Sanitized live evidence |
|---|---|---|
| Organic first turn: `Find the student.` | Partial / blocker | `/ask` returned `success` with `execution.status: waiting_for_input` and a real missing-student-identifier question. The persisted session then had `active_workflow: null`, `active_workflow_status: null`, and zero current facts. |
| Organic second turn: `B250012CS.` on same session | Failed acceptance condition | The request again returned `waiting_for_input`; no persisted active workflow existed for the guarded `/ask` continuation branch to project, so no `workflow_continuation`/`READY`/canonical-success proof was produced. |
| Organic topic switch: `Find the student.` then unread-email question | Pass | First turn returned `waiting_for_input`; second turn returned execution `success`, response text identified the Gmail/unread-email intent, and persisted state had no active workflow or status after the turn. |

This is a reproducible evidence-completeness failure, not a seeded substitute
for the required primary proof. The new `turn_state.py` projection and its
focused test are complete, and the required regression suite passed 124/124,
but M30.7 cannot honestly advance to `VERIFICATION_READY` until the organic
first turn persists the canonical `active_workflow` continuation state under
the mandated live flags.

## Revision v4 implementation and live verification (2026-09-13)

The bounded `post_execution_reevaluation` repair is implemented: when the
final real attempt-history proposal is a capability, its capability is now
passed to `_apply_clarification_pause` as `capability_id`. The focused
regression proves the resulting pause retains `extract_student_records`; it
passed 1/1, and the mandated regression invocation passed **124/124**. No
execution allowlist was changed.

The authenticated, unseeded Gmail scenario was attempted against a fresh
loopback backend with all three required flags. The environment cannot produce
the required allowlisted execution path: read-only `/connections` reports
Gmail as `needs_authorization` (client secret exists; usable server-host
sign-in is absent). Natural fresh-session Gmail requests returned real
`waiting_for_input` pauses, but their persisted clarification proposals have
`capability_id: null` because they occur before a Gmail action is proposed or
executed. Matching sanitized canonical telemetry records are `clarification`,
with no selected capability and no canonical execution.

The authenticated organic topic-switch regression was re-run: after the email
search clarification, a weather request produced a fresh `conversation`
canonical decision. Persisted state had `active_workflow: null` and
`active_workflow_status: null`. No content, bearer token, credential, or raw
telemetry is recorded here.

This is a live-environment prerequisite blocker, not a substitute proof. The
report therefore does **not** claim `VERIFICATION_READY`; completing the
organic Gmail continuation evidence requires usable Gmail authorization on the
server host, then rerunning the same unseeded two-turn scenario.

## Revision v4 re-verification after Gmail refresh (2026-09-13)

The live backend was restarted on loopback with all three required feature
flags. A fresh `URI_test2` bearer token was obtained through `/auth/login`;
authenticated `/connections` reported Gmail as `connected` before the test.
No token, email content, or raw telemetry is recorded here.

| Scenario | Result | Sanitized live evidence |
|---|---|---|
| Organic Gmail turn 1: `Search my email.` | Did not meet primary precondition | `/ask` returned `success` with `execution.status: waiting_for_input` and a real question, but the persisted clarification proposal was `type: clarification`, with no prior capability and `capability_id: null`. The pause occurred before the Brain proposed Gmail, so it was not the fixed post-execution-reevaluation path. |
| Organic Gmail continuation | Not runnable without fabrication | No real Gmail-bearing pending pointer was created on turn 1, so a search-term answer could not truthfully demonstrate continuation. No state was seeded or edited. |
| Organic topic switch | Pass | A same-session weather request returned `success` with execution and narrative. Persisted active-workflow fields were null; sanitized telemetry recorded a fresh non-continuation decision. |

The direct focused regression for the repaired call site passes, and the
required suite now passes **125/125**. The source fix is complete, but the
mandatory allowlisted organic continuation remains unproven; this report does
not claim `VERIFICATION_READY`.

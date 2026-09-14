# M30.6A Final Live Acceptance Verification

**Date:** 2026-09-13  
**Result:** LIVE VERIFIED — mandatory canonical Gmail `/ask` path passed.

## Verification boundary

This was a real loopback HTTP verification against `POST /ask`, using a fresh
token issued by the normal `POST /auth/login` endpoint for `URI_test2`. It used
the existing persisted account, grant store, shared `token.json`, production
`MultiActionDispatch`/`GmailCapability`, and live Gmail API. No executor was
called directly, no principal/service was mocked, and no grant or connection
state was bypassed. Raw bearer tokens, token contents, message bodies, and
message identifiers are intentionally omitted.

The verification server was started through the sanctioned
`scripts/run_uri_server.py` launcher on loopback with
`URI_ENABLE_DECISION_ENGINE_LIVE=1` and
`URI_ENABLE_DECISION_ENGINE_SHADOW=1`.

## Mandatory proof chain

| Point | Live evidence | Result |
|---|---|---|
| 1. Authorization accepted | Fresh login returned HTTP 200; `GET /auth/me` with the bearer header returned HTTP 200. | Pass |
| 2. Principal identity | `/auth/me` confirmed the resolved authenticated principal contained a non-empty `user_id`. | Pass |
| 3. Resolver sees real identity | The same persisted account was resolved through `UserAccountStore`; its constructed production `PrincipalContext` had a non-empty `user_id`. | Pass |
| 4. Grant lookup | `CapabilityGrantsStore.get_grants(user_id, registry_ceiling)` included `gmail_search`; `CapabilityResolver.is_allowed("gmail_search", principal)` returned `True`. This account has no explicit grant row, so the documented M22.4 migration-default registry ceiling was the actual existing-store result. | Pass |
| 5. Canonical decision | The canonical telemetry record for `canonical-live-verify-m30-6a` selected mode `single_action`, capability `Gmail`, action `list_labels`. | Pass |
| 6. Deterministic gate | The same record reports `gate_outcome: READY`. | Pass |
| 7. Real execution | The record reports `canonical_execution_attempted: true` and `canonical_execution_result: success`; the real HTTP envelope reported `status: success`, `execution.status: success`, and `execution.capability: Gmail`. | Pass |
| 8. Evidence created | The canonical telemetry record reports `execution_evidence_returned: true`. | Pass |
| 9. Evidence returned to reasoning | The canonical envelope reached the existing `_draft_narrative_safely` path; the HTTP result contained both `response` and `narrative`, while telemetry reports grounded final response. | Pass |
| 10. Grounded final response | The returned response/narrative contained the live unread-count evidence (`533`); no raw response text is retained here. Telemetry reports `grounded_final_response: true`. | Pass |

The mandatory request was:

```json
{"text":"How many unread emails do I have?","session_id":"canonical-live-verify-m30-6a"}
```

It returned HTTP 200 and canonical `success` through the real `/ask` route.

## Follow-up grounding

The optional first follow-up, `Find the latest insurance email.`, was sent in
the same session. It returned HTTP 200 with `waiting_for_input`; it did not
claim or fabricate an email identity. Canonical telemetry recorded mode
`clarification`, `gate_outcome: READY`, and no attempted execution because a
clarification decision is not executable. Consequently, requests 3 and 4 were
not sent: there was no resolved message identity on which to safely perform a
read or attachment lookup.

This is an honest optional-follow-up divergence, not a failure of the mandatory
M30.6A acceptance chain.

## Assessment

All ten mandatory acceptance points succeeded with a genuine authenticated
principal and real Gmail execution. M30.6A moves from `VERIFICATION_READY` to
`LIVE_VERIFIED`.

M30.7 may now be considered for approval, but remains **NOT AUTHORIZED** until
the User explicitly authorizes it. This verification neither opens nor begins
M30.7.

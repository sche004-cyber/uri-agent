# M30.7B Canonical Readiness Closure Report

**Date:** 2026-09-13. No source change, global cutover, M30.8 work, legacy retirement, `uri_ui/` work, commit, or push occurred.

## Authentication boundary

A fresh loopback server with `URI_ENABLE_DECISION_ENGINE_LIVE=1` and `URI_ENABLE_DECISION_ENGINE_SHADOW=1` accepted `URI_test2` / `URI_test2` at `POST /auth/login` (200). Its new bearer token returned `authenticated: true` and a non-empty user id from `GET /auth/me`. All retries used this real principal. The isolated-disconnected server used a new empty temporary `URI_GOOGLE_CREDENTIALS_DIR`; the real credential/token files were untouched.

## Repair evidence

| Scenario | Result | Disposition |
|---|---|---|
| 2 Gmail disconnected | Three real isolated `/ask` attempts yielded invalid/unsupported proposals before the Gmail gate, not `DISCONNECTED`. | `LIVE_FAIL`; no connection-truth defect established. |
| 5 Recurring job | First request: gate `UNSUPPORTED` plus one clarification. Explicit daily-automation follow-up performed one-time `web_search`, not an honest refusal. | `LIVE_FAIL`; remediation is outside the two authorized source boundaries. |
| 6 Remember fact | Exact wording: three canonical `remember_fact` `READY`/success/evidence/grounded results; one independent call classified conversation. | Model variance documented; no preselection fix justified. |
| 7 Gmail chain | Real Gmail attachment search selected `search_messages`, gate `READY`, and succeeded with grounded evidence; no safe attachment-bearing id was returned for read/attachment follow-up. | `LIVE_FAIL`; no synthetic data created. |
| 8 Draft/no-send | Complete request selected `create_draft` and `APPROVAL_REQUIRED`; canonical execution did not run pre-approval. `GmailService.create_draft()` only calls `users().drafts().create()`; it has no `send` method or `.send(` call. | Approval/no-send boundary proven; pre-approval content-return evidence remains unavailable. |
| 9 Convert PDF | Previously-audited Layer-3 trace remains sound: no result/action schema and no canonical executor branch. | `BLOCKED_BY_CURRENT_SCOPE`; allowlist unchanged. |
| 12 Provider failure | Unreachable `OLLAMA_BASE_URL=http://127.0.0.1:19999` yielded canonical `invalid_contract:unavailable` with no execution. The visible legacy result did not reliably disclose provider unavailability. | `LIVE_FAIL`; honest visible fallback unproven. |

## Twelve-scenario matrix

| # | Result |
|---|---|
| 1 | `PRESERVED_LIVE_PASS` (M30.7A) |
| 2 | `LIVE_FAIL` — no valid Gmail proposal reached `DISCONNECTED` |
| 3 | `PRESERVED_LIVE_PASS` (M30.7A) |
| 4 | `DOCUMENTED_ACCEPTED_RESIDUAL` — not reopened |
| 5 | `LIVE_FAIL` — one-time search instead of recurrence refusal |
| 6 | `LIVE_VARIANCE_DOCUMENTED` — three canonical successes, one conversation |
| 7 | `LIVE_FAIL` — no safe attachment-chain id |
| 8 | `APPROVAL_BOUNDARY_PROVEN`; draft-content envelope pending |
| 9 | `BLOCKED_BY_CURRENT_SCOPE` |
| 10 | `PRESERVED_LIVE_PASS` (M30.7A) |
| 11 | `PRESERVED_LIVE_PASS` (M30.7A) |
| 12 | `LIVE_FAIL` — visible provider-unavailable fallback unproven |

## Regression

Fresh `.venv\\Scripts\\python.exe -m pytest -q` was allowed to process completion. Follow-up `.venv\\Scripts\\python.exe -m pytest -q --last-failed` reported **8 failed, 10 deselected**: the established two Drive stubs, M20 deterministic-behavior expectations, and orchestrator newline boundary. No M30.7B source change exists. This matches the known **1,726 passed / 8 existing failures / 0 new M30.7B failures** baseline.

## Final disposition

**M30.8 NOT READY - Scenario 2 lacks real DISCONNECTED/guidance proof; Scenario 5 performs a one-time web search instead of honestly refusing recurring automation; Scenario 7 has no safe grounded attachment id; Scenario 8 has no observable pre-approval draft-content envelope; Scenario 9 is BLOCKED_BY_CURRENT_SCOPE; and Scenario 12 lacks an honest visible provider-unavailable fallback message.**

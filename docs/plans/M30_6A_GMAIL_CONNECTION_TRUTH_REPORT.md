# M30.6A — Gmail Connection Truth Unification Report

## 1. Root cause summary

Fresh `GmailService` instances treated `self.service is None` as a Gmail
disconnection even when the shared durable `token.json` was usable.  The
legacy `GmailSearchService` separately parsed and refreshed that token, while
the Connections view separately parsed it without refreshing.  The resulting
false negative propagated through `GmailCapability` availability and the
deterministic gate.

## 2. Authoritative source chosen

`google_auth_common.load_usable_credentials()` is the sole stateless token
loader.  `GmailService.ensure_connected_from_token()` is the authoritative
non-interactive client-establishment probe for `GmailCapability`.  The only
interactive OAuth flow remains `GmailService.connect()`.

## 3. Files created and modified

- Created `uri_core/core/google_auth_common.py`.
- Created `test_gmail_connection_truth.py`.
- Modified `uri_core/services/gmail_service.py`.
- Modified `uri_core/services/gmail_search_service.py`.
- Modified `uri_core/core/connection_status.py`.
- Updated the affected existing mock in `test_gmail_search_service.py`.
- Updated `docs/plans/M30_6A_STATE.md`.

## 4. Before/after divergence matrix

| Consumer | Before | After |
|---|---|---|
| `GmailSearchService` | Its own parsing/refresh logic | Shared loader with refresh, then builds its client |
| `GmailService` / capability | In-memory client flag only | Shared-loader probe builds a client from the stored token |
| Connections status | Its own parse-only logic | Shared loader with refresh explicitly disabled |

## 5. Unified architecture

The helper resolves `URI_GOOGLE_CREDENTIALS_DIR` identically to the existing
repository-root convention, parses only `token.json`, refreshes only when its
caller permits refresh, and returns credentials or `None` without raising.
`GmailService` maps probe failures to the closed reasons `no_token`,
`invalid_token`, `scope_missing`, and `auth_error`; no consent flow is called.
`get_connection_status()` now probes before reporting a fresh instance as
disconnected.

## 6. Capability Directory result

Live verification with the existing token returned `available: true` for the
Gmail Capability Directory detail.  This came from `GmailCapability` calling
the newly truthful `GmailService.get_connection_status()`.

## 7. Deterministic gate result

For the live `Gmail` / `list_labels` decision contract, the deterministic gate
returned `READY` with reason `all_gates_passed` (using the normal permission
checker seam, which reported the read permission granted for this check).

## 8. Live real Gmail canonical trace evidence

The canonical decision trace for “How many unread emails do I have?” selected
`Gmail` / `list_labels`, recalled Gmail as a candidate, and recorded gate
`READY`.  Its actual canonical execution then stopped at the existing runtime
permission boundary with `permission_denied`; no Gmail data was returned by
that canonical invocation.  This is not a token/availability failure and was
not bypassed or changed by M30.6A.

The real read-only execution path was separately exercised with an explicitly
granted `gmail.readonly` test principal: `GmailCapability` executed
`list_labels` successfully against the live account and returned a real unread
count of **533**.  This proves the M30.6A connection truth, service client,
and Gmail read path; it does not substitute for resolving the canonical
principal/grant configuration.

## 9. Grounded follow-up trace evidence

Using the same real Gmail read-only execution boundary and an explicitly
granted test principal, “Find the latest insurance email” returned one result;
“Read that one” succeeded with the same resolved message identifier; “Check
its attachment” succeeded and returned an attachment inventory of zero items.
No message content, identifiers, headers, or token data were recorded here.

## 10. Test commands and outputs

The global `python` environment lacks `pytest` and Google dependencies, so
the project virtual environment was used for the specified commands:

```text
.venv\Scripts\python.exe -m pytest test_gmail_connection_truth.py
7 passed in 0.50s

.venv\Scripts\python.exe -m pytest test_gmail_search_service.py test_gmail_search_shape.py
6 passed in 0.43s

.venv\Scripts\python.exe -m pytest test_multi_action_capabilities.py
12 passed in 0.72s
```

`git diff --check` reported only pre-existing whitespace findings in unrelated
dirty files; none were introduced by this milestone.

## 11. Security and privacy verification

The shared loader catches and discards all parse/refresh exceptions and never
logs credential values or exception text.  It never creates an
`InstalledAppFlow`; the OAuth consent flow and single `token.json` handling
remain unchanged.  Gmail permission declarations and `create_draft` approval
gates were not modified.  Live evidence records only statuses, counts, and
non-sensitive aggregate outcomes.

## 12. M30.7 safety assessment

**Not safe to begin.** M30.6A fixes the false Gmail disconnection and proves a
live Gmail client/read path, but the required full canonical execution remains
blocked by the pre-existing runtime permission/grant resolution for the
anonymous direct canonical invocation.  That authorization configuration must
be verified with an authenticated principal before M30.7 is considered.

## 13. Rollback instructions

Revert only this milestone’s new helper, the three Gmail/status delegations,
the focused tests, and this report/state update.  This restores the former
in-memory-only `GmailService` status behavior while leaving unrelated dirty
worktree changes untouched.  Do not delete `token.json`, `credentials.json`,
or any user data.

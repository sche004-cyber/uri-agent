# M30.6A - Gmail Connection Truth Unification (Plan)

STATE: ACCEPTED (plan only) - implementation NOT yet performed by
Codex/Gemma. This document is Claude's Architect/Pre-Auditor output per
the standing AO-4 development cycle (`ORCHESTRATION.md`), produced from
direct inspection of the real repository state (not assumed). It
defines the required remediation; it does not implement it. Sibling
state file: `docs/plans/M30_6A_STATE.md`.

Scope authority: this plan addresses ONLY the single prerequisite
M30.6 (§16-17 of `M30_6_CONTROLLED_CANONICAL_EXECUTION_REPORT.md`)
named as blocking M30.7 - Gmail connection/availability truth. M30.7
itself is out of scope and must not be started from this plan.

---

## 1. Root cause (traced directly from source, not assumed)

Three independent code paths currently answer "is Gmail connected?"
with three different, non-shared truth sources:

**A. Legacy path - `GmailSearchService`**
(`uri_core/services/gmail_search_service.py`, used by the pre-M27
production Gmail answers, e.g. the real "533 unread" answer in
M30.6 §9). `authenticate()`:
- reads `token.json` from `_repo_root()` (same resolved root
  `connection_status.py` uses, honoring `URI_GOOGLE_CREDENTIALS_DIR`
  since the 2026-09-12 fix documented in its own docstring)
- loads `Credentials.from_authorized_user_file(...)`
- refreshes via `Request()` if expired and a refresh token exists
- builds a real `googleapiclient` service object
- never launches an interactive consent flow; honestly returns
  `False` if no usable token exists
- called fresh, non-interactively, on every `get_unread_count()`/
  `search_emails()` call if `self.service` is not already set

This path is real, working, and non-interactive. It is the one this
dev environment's Gmail is genuinely reachable through.

**B. Canonical/M27 path - `GmailCapability` -> `GmailService`**
(`uri_core/capabilities/gmail/capability.py` ->
`uri_core/services/gmail_service.py`). `GmailCapability._availability()`
calls `self.gmail_service.get_connection_status()`, which is:

```python
def get_connection_status(self) -> dict:
    return {"connected": self.service is not None, "mode": "READ_ONLY"}
```

`self.service` is set **only** inside `GmailService.connect()`, which
is interactive-capable (`InstalledAppFlow.run_local_server(port=0)`
when no valid token exists) and is only ever invoked from
`POST /connections/{id}/authorize`. A freshly constructed
`GmailCapability()` - which is what every per-request capability
lookup produces - has `gmail_service.service is None` unconditionally,
regardless of whether `token.json` is genuinely valid. This is a
false negative, not a real disconnection: the class never attempts a
non-interactive token load on its own, unlike path A.

**C. Settings/UI path - `connection_status.py`**
(`uri_core/core/connection_status.py`, used by
`list_connection_status()` for the client's Connections screen).
`_token_is_usable()` reads the same `token.json` via the same
`_repo_root()`, parses it with
`Credentials.from_authorized_user_file(token_path, scopes)`, and
reports `connected` if that parses without error. Deliberately never
refreshes and never builds a service (explicitly documented as
non-interactive and read-only, so an HTTP status query can never
trigger a server-side browser consent flow). This path is honest but
answers a narrower question ("does a parseable token file exist") than
what `GmailCapability` needs ("can I actually get a working client").

**The divergence, summarized:**

| Path | Token source | Builds client | Refreshes | Interactive fallback | Result in this env |
|---|---|---|---|---|---|
| A. `GmailSearchService.authenticate()` | `token.json` via `_repo_root()` | yes | yes | no (`False`) | connected, real data |
| B. `GmailService.get_connection_status()` | in-memory `self.service` flag only | n/a | n/a | via `.connect()`, never auto-invoked | **always disconnected** for a fresh instance |
| C. `connection_status._token_is_usable()` | `token.json` via `_repo_root()` | no | no | no | connected (UI-only, informational) |

`CapabilityFeasibility`/`decision_gates.evaluate_gates()` both consume
path B's answer (via `GmailCapability`'s `availability_check`), so the
deterministic gate inherits path B's false negative and returns
`DISCONNECTED` (`decision_gates.py:250-253`) even when Gmail is
genuinely reachable. This is a real, pre-existing (M27) gap, not a
regression, first made consequential by M30.6 because it is the first
milestone whose execution decision depends on this signal (M30.6
report §9/§16, independently confirmed here by direct source reading).

No user/session-scoping issue was found: all three paths resolve the
same single-user, single-token-file install (`_repo_root()`/
`token.json`), so this is not a user-context mismatch - it is purely
an in-memory-flag-vs-durable-token-truth mismatch inside `GmailService`
itself.

## 2. Design rule applied

Per the task's own constraint, this plan does not create a second
token loader or a second credentials path. `GmailService` is already
the sole boundary `GmailCapability` is documented to depend on (its
own module docstring: "It uses `GmailService` as the sole connection/
service boundary"). The unification therefore happens **inside
`GmailService`**, reusing the exact non-interactive logic path A
(`GmailSearchService.authenticate()`) and path C
(`connection_status._token_is_usable()`) already independently prove
safe and correct, rather than inventing a fourth implementation.

**Authoritative source chosen:** a new non-interactive,
token-only authentication routine on `GmailService` itself -
functionally identical to `GmailSearchService.authenticate()` (parse
`token.json`, refresh if expired-with-refresh-token via `Request()`,
build the client) but **never** constructing an `InstalledAppFlow` and
never calling `run_local_server`. This keeps the one real interactive
consent flow exactly where it is today (`GmailService.connect()`,
reachable only from `POST /connections/{id}/authorize`) and gives
`GmailCapability` a second, safe entry point for a read-only
connection probe.

To satisfy "prefer reuse over duplication" precisely (three
near-identical token-parsing implementations already exist across A/B/
C), extract the shared, stateless piece - "parse `token.json` into
`Credentials`, refresh non-interactively if possible, return
`Credentials` or `None`, never raise" - into one function, e.g.
`uri_core/core/google_auth_common.load_usable_credentials(token_path,
scopes, allow_refresh=True) -> Optional[Credentials]`. This becomes the
single place token-parsing logic lives going forward:
- `connection_status._token_is_usable()` calls it with
  `allow_refresh=False` (preserves its documented "never refreshes"
  guarantee exactly - a behavior-preserving refactor, not a behavior
  change).
- `GmailSearchService.authenticate()` calls it with
  `allow_refresh=True`, then builds its own service object exactly as
  today (preserves the legacy path byte-for-byte in effect).
- The new `GmailService` non-interactive method calls it with
  `allow_refresh=True`, then builds `self.service` exactly as
  `connect()`'s own non-interactive branch already does.

This is a consolidation (one shared helper replacing three duplicated
parsing blocks), not a new subsystem, and each caller's observable
behavior is unchanged except `GmailService` gaining the capability it
previously lacked.

## 3. `GmailService` changes (for Codex to implement)

Add one new method, non-interactive, never raising:

```python
def ensure_connected_from_token(self) -> dict:
    """Non-interactive connection probe/establish. Never launches
    InstalledAppFlow. Returns {"connected": bool, "reason": <one of
    "connected"/"no_token"/"invalid_token"/"scope_missing"/
    "auth_error">}. Sets self.service on success so subsequent calls
    on this instance reuse the real client."""
```

Implementation: reuse `google_auth_common.load_usable_credentials()`
(§2) with `allow_refresh=True`; on success, `build("gmail", "v1",
credentials=creds)` into `self.service` exactly as `connect()` already
does; on any failure, leave `self.service` as `None` and return a
specific, non-secret reason (never token/credential contents - see
§8).

Update `get_connection_status()` to call this probe when
`self.service` is not already set, so its answer reflects real,
current token state instead of only the in-memory flag:

```python
def get_connection_status(self) -> dict:
    if self.service is None:
        self.ensure_connected_from_token()
    return {"connected": self.service is not None, "mode": "READ_ONLY"}
```

This one change is what fixes `GmailCapability._availability()`,
`CapabilityFeasibility`, and `decision_gates.evaluate_gates()`
simultaneously, since all three consume `get_connection_status()`
transitively through the same `availability_check` - exactly the
single-authoritative-source requirement in the task's DESIGN RULE.

No change is needed inside `GmailCapability.capability.py` itself:
`_availability()` already calls `get_connection_status()` and already
falls back safely (`except Exception: connected = bool(getattr(...,
"service", None))`) - it inherits the fix for free once `GmailService`
tells the truth. `_client_or_none()`/action handlers also inherit a
real, usable `self.gmail_service.service` after a successful
availability probe within the same request-scoped `GmailCapability`
instance (verify this instance lifetime assumption against
`capability_directory.py`'s construction site before implementing -
if capability instances are pooled/reused across requests rather than
built fresh per request, note that explicitly in the completion
report rather than silently relying on it).

## 4. `connection_status.py` changes

None required to its public behavior or return shape. Only its
internal token-parsing block is expected to delegate to the new shared
`google_auth_common.load_usable_credentials(..., allow_refresh=False)`
helper (§2) as a pure refactor - same non-interactive, non-refreshing,
non-building guarantee, same three-state output
(`connected`/`needs_authorization`/`not_connected`), unchanged.

## 5. Capability Directory expectations

After the fix, for a genuinely valid `token.json`:
- `availability_known` -> `true` (an `availability_check` ran and
  returned a real boolean, same as today's mechanism - only the
  boolean's correctness changes).
- `connection_state` -> reflect actual state: `None`/absent when
  connected, `"gmail_connected"` (from `missing_preconditions`, per
  `capability.py`'s existing `_availability()` shape) when genuinely
  disconnected.
- `reason`/`availability_reason` -> explicit, never `"unavailable"` as
  a bare catch-all when a more specific reason (`no_token`,
  `invalid_token`, `scope_missing`, `auth_error`) is available from
  `ensure_connected_from_token()`.
- Unsupported actions (`apply_label`, `archive_message`) remain
  visible and still return `status: "unsupported"` - untouched by this
  plan, per the task's explicit "do not hide unsupported Gmail modify
  actions."

## 6. Deterministic gate expectations (`decision_gates.py`, unchanged code)

No changes to `decision_gates.py` itself are anticipated - it already
correctly derives `DISCONNECTED`/`READY`/`UNAVAILABLE` from
`availability_known`/`available`/`availability_reason` (lines 234-264).
This plan only fixes the truth value those fields carry. Required
post-fix behavior to verify live:
- connected Gmail + read-only action (`list_labels`, `search_messages`,
  `read_message`, `read_thread`, `read_attachment`) -> `READY`.
- disconnected Gmail (token genuinely absent/invalid) -> `DISCONNECTED`.
- connected Gmail + `create_draft` (approval-required) ->
  `APPROVAL_REQUIRED`.
- `apply_label`/`archive_message` -> existing `UNSUPPORTED` path
  (`availability_reason == "not_implemented"`) or equivalent existing
  deterministic outcome - not a new one.
- The Brain/model must not be able to influence any of this -
  unchanged, since `decide_fallback_reason()`/`evaluate_gates()` never
  read the Brain's own claims as ground truth (M30.6 §6).

## 7. Live canonical verification required (Codex/User, not fabricated by Claude)

With `URI_ENABLE_DECISION_ENGINE_LIVE=1` and a real, valid `token.json`
in this environment, repeat the exact M30.6 canonical trace for:

> "How many unread emails do I have?"

Required evidence chain (mandatory, real, not a double this time):
user request -> Turn State -> candidate selection -> Brain Decision
Contract -> `GmailCapability` availability=true -> deterministic gate
= `READY` -> real `MultiActionExecutor`/`GmailCapability` execution
against the real Gmail account -> real execution evidence (`labels`
with real `messages_unread`) -> `_draft_narrative_safely()` feedback ->
grounded final response.

Follow-up grounding chain (live, if supported by available real data):
"Find the latest insurance email." -> "Read that one." (same real
`message_id`) -> "Check its attachment." (real attachment reference,
never fabricated if none exists).

## 8. Security constraints (unchanged, explicit)

Never log: access tokens, refresh tokens, `credentials.json` contents,
OAuth client secrets, raw `Authorization` headers. All new
reason/status strings introduced by `ensure_connected_from_token()`
must be drawn from the closed set `{connected, disconnected, unknown,
scope_missing, auth_error, no_token, invalid_token}` - no exception
message or credential fragment is ever surfaced in a reason string or
log line. `google_auth_common.load_usable_credentials()` must catch
and discard the underlying exception detail, returning only `None` on
any parse/refresh failure (mirrors `connection_status._token_is_usable`'s
existing `except Exception: return False` discipline exactly).

## 9. Regression requirements

Preserve unchanged: legacy `GmailSearchService` path and its own tests
(`test_gmail_search_service.py`, `test_gmail_search_shape.py`); OAuth
login flow and `POST /connections/{id}/authorize`; `credentials.json`/
`token.json` handling and paths; Gmail search behavior; approval rules
(`create_draft` stays `USER_APPROVAL_REQUIRED`); permission scopes
(`gmail.readonly` only for `GmailCapability`'s own declared
`permissions`); M30.1-M30.6 tests (168/168 baseline, plus the 8
pre-existing unrelated failures documented in the session's baseline
note - no new failures beyond that known set); flag-off
(`URI_ENABLE_DECISION_ENGINE_LIVE` unset) behavior byte-for-byte
identical to before this milestone.

## 10. Files expected to change (for Codex, not yet touched)

**New:**
- `uri_core/core/google_auth_common.py` - `load_usable_credentials()`
  shared helper (§2).
- A focused test module for it plus `GmailService.
  ensure_connected_from_token()` (naming at Codex's discretion,
  following this repo's `test_gmail_service_*.py`/
  `test_gmail_search_service.py` convention).

**Modified:**
- `uri_core/services/gmail_service.py` - `ensure_connected_from_token()`
  added; `get_connection_status()` updated to probe (§3).
- `uri_core/services/gmail_search_service.py` - `authenticate()`
  delegates to the shared helper (§2), behavior-preserving.
- `uri_core/core/connection_status.py` - `_token_is_usable()` delegates
  to the shared helper with `allow_refresh=False` (§2/§4),
  behavior-preserving.

**Not expected to change:** `uri_core/capabilities/gmail/capability.py`
(inherits the fix, §3), `uri_core/core/decision_gates.py` (§6),
`uri_core/core/capability_directory.py` (inherits corrected
`availability_known`/`available`/`availability_reason` values from the
existing `availability_check` mechanism), `orchestrator.py`,
`canonical_execution.py`.

## 11. Output required from Codex on completion

`docs/plans/M30_6A_GMAIL_CONNECTION_TRUTH_REPORT.md`, covering exactly
the 13 numbered items in the User's own M30.6A task instructions
(root cause, authoritative source chosen, files changed, before/after
divergence, unified architecture, Capability Directory result,
deterministic gate result, live real Gmail canonical trace, grounded
follow-up trace, tests/results, security/privacy verification, whether
M30.7 is safe to begin, rollback instructions).

## 12. Process note (why this plan does not implement)

Per the standing AO-4 development cycle (`ORCHESTRATION.md`, pinned
memory `uri-ao4-development-cycle`), Claude's role for a fresh
milestone is Architect/Pre-Auditor, not implementer - this is
substantial, multi-file remediation (a new shared module plus edits
across three service/status files), not a bounded fix discovered
during Claude's own final audit of an already-implemented milestone.
Claude therefore defines the required remediation here and hands it to
Antigravity for routing to Codex (the preferred worker for this class
of security-adjacent, production-call-path work per the 2026-09-11
role revision), rather than implementing it directly in this session.
Marked ACCEPTED under the standing auto-approval rule
(`ORCHESTRATION.md` §1.5) - this is routine engineering remediation of
an already-disclosed, already-scoped gap, not a change to URI's core
project structure, product identity, or security/authority model.

Per the 2026-09-12 live-verification-gate revision, Claude's own
independent final audit of Codex's implementation happens after the
User has personally live-tested the result and explicitly directed
Claude to proceed to commit/push - not immediately upon Codex's
completion report.

---

Stopping here. M30.6A implementation is now ready for Antigravity to
route to Codex. M30.7 is not started.

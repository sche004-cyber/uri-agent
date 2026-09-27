# M33.3-R S11 — Result-Version Ownership: Discovery and Plan

**Status:** plan written before implementation (2026-09-27, implementer). Auto-accepted under the M33.3-R task package; discovery did not change the required architecture, so no User stop was needed (§3).

## 1. Discovery (repository evidence)

| Question | Finding | Evidence |
|---|---|---|
| Are results editable in `uri_ui`? | **No.** Turn results are display-only (`turn_card.dart`). The only in-app edit path is memory entries (`PUT /memory/{id}`, `uri_client.dart:332`). | `uri_ui/lib/widgets/turn_card.dart`, `uri_ui/lib/services/uri_client.dart` |
| Can results be edited at all? | **Yes, outside URI.** A Gmail draft created by `gmail_create_draft` (D1: `RECOVERABLE`) can be edited in Gmail; files URI writes can be edited on disk. URI is not notified of either. | `uri_core/capabilities/gmail/capability.py:225`, D1 |
| How are results persisted? | Drafts live in Gmail; files in the user's `file_store`; turn text in session history. No record links a result to the binding that produced it. | `uri_core/core/file_store.py`, `session_store` |
| Does a revision/version concept exist? | **No.** `file_store.py` has only a schema version. No result, artifact or draft versioning anywhere in `uri_core` or `uri_v1`. | repository search for `revision`, `parent_version`, `result_version` |
| Legacy URI? | **No** mechanism in the protected legacy worktree (`uri-agent`). | search of `C:\Users\cheta\Development\uri-agent` (only vendored `.venv` hits) |
| Existing seam? | S1 `BindingService.authorize_redo(ambiguity_id, fresh_authorized, edited_result_status)` accepts an injected edited status. Any value other than `UNEDITED` yields `REDO_NOT_EXECUTED` with reason "result-version owner (S11) required"; S1 has no redo executor. S1 is frozen. | `uri_v1/reference_clarification/binding.py:380-392` |

## 2. External patterns

Append-only revision logs (Git objects; CouchDB `_rev`; Google Docs revision history) and content addressing (a version is identified by the hash of its content, so any out-of-band edit is detected by comparing hashes). Event-sourced history (versions are appended, never updated).

**Decision:** clone the concept. A result's versions are an append-only list; each version is identified by the SHA-256 of its content; edited content is stored in a content-addressed blob store so it is kept, not only detected.

## 3. Architecture impact check

Discovery shows that edits happen **outside URI** (Gmail, disk), not in `uri_ui`. This does not change the planned architecture: content-hash comparison detects both in-app and out-of-band edits through a caller-supplied content reader. No production persistence system is redesigned; the ledger is new, unwired, per-user state. No stop condition applies.

## 4. Design

**Module:** `uri_v1/results/version_ledger.py` (new), `uri_v1/results/redo.py` (new). Frozen S1 files are not modified.

- `ResultVersion(result_id, version, content_sha256, origin, parent_version, binding_id, candidate_id, trace_id, created_at)`; `origin` ∈ {`GENERATED`, `USER_EDIT`, `REDO`}.
- `ResultVersionLedger(user_id, root)`:
  - `record_generated(result_id, content, …)` → version 1, `GENERATED`.
  - `edited_status(result_id, current_content)` → `UNEDITED` when the current hash equals the head hash; `USER_EDITED` otherwise; `UNKNOWN` when no record exists or the content cannot be read (fail closed).
  - `observe(result_id, current_content)` → appends a `USER_EDIT` version holding the edited content when the hash changed.
  - `append_redo(...)` → appends a `REDO` version. Prior versions are never mutated or deleted; blobs are write-once.
- `RedoCoordinator(binding_service, ledger)`:
  1. reads the current result content through a caller-supplied reader; a reader failure is `UNKNOWN`;
  2. calls the frozen S1 `authorize_redo` with the true edited status;
  3. **UNEDITED + fresh authorization** → S1 returns `REDO_AUTHORIZED`; the coordinator produces the new content through the caller's executor and appends a `REDO` version → outcome `REDONE`;
  4. **USER_EDITED or UNKNOWN** → S1 returns `REDO_NOT_EXECUTED`; the coordinator snapshots the current (edited) content as a `USER_EDIT` version and returns `REDO_BLOCKED_EDITED` with the preserved version number. Nothing is overwritten.
  5. **Explicit versioned redo** (`create_new_version`): only on a separate, explicit user request with fresh authorization, and only for a binding in `REDO_NOT_EXECUTED` because of an edit. It appends the redo as a new `REDO` version whose parent is the preserved edited version → outcome `VERSIONED`. The edited version stays in history.

**Decision D-S11-1 (disclosed for the independent audit).** Plan A R1.5 describes an automatic redo that becomes a new version when the old result was edited. The frozen S1 `authorize_redo` refuses any redo whose status is not `UNEDITED`, and S1 may not be modified. S11 therefore makes the edited-result case explicit: the automatic Change redo stops and preserves the edit; a new version is created only through an explicit, freshly authorized user request. This is the more conservative reading of the same invariant ("a redo must never silently overwrite a user-edited result") and changes no frozen contract.

## 5. Tests (required)

- An edited result is never overwritten: the automatic redo is blocked, the edited content is preserved byte-for-byte, and the head content is still the edited content.
- Normal regeneration: an unedited result is redone and the head becomes the redo version (`REDONE`).
- Out-of-band edit detection by hash; reader failure and missing record fail closed (`UNKNOWN`, no redo).
- Explicit versioned redo appends a new version with the edited version as parent; history keeps every version; blobs are content-addressed and write-once.
- The redo requires the frozen S1 preconditions (confirmed Change rebind, fresh authorization).
- The ledger rejects path-traversal result IDs and unknown origins.

## 6. Out of scope

Production wiring (which results get recorded at execution time) is S13 / INT-*. No UI editing surface is added.

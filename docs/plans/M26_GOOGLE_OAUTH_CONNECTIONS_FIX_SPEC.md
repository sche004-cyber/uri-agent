# M26 — Google OAuth Configure-Credentials Flow: Root Cause & Exact Fix Spec

**Status:** IMPLEMENTED by Claude directly, per the User's explicit follow-up instruction ("Please fix it here only") superseding the original Codex-only restriction below. §0 is kept verbatim as the record of that restriction and why it was initially not implemented.
**Author:** Claude (AO-4 Architect / Pre-Auditor)
**Date:** 2026-09-12

---

## §0. Why nothing is implemented yet

The User's request explicitly restricts implementation to Codex ("Use Codex as the implementation agent. No other implementation agent."). Claude cannot directly invoke or drive Codex from this session — `ListAgents` shows no reachable Codex or Antigravity session (only offline Remote Control sessions of Claude itself). This document is the complete investigation and exact fix specification Codex needs; the User (or Antigravity, once reachable) must hand it to Codex to execute.

---

## §1. Governing docs checked

`AGENTS.md`, `PROJECT_MEMORY.md`, `ARCHITECTURE.md` were checked for Google-OAuth-specific guidance — none exists; this flow is governed only by the M16/M22.3 code and its own docstrings (cited below), not by a separate architecture doc.

## §2. Full trace, with confirmed root causes at each step

**Backend save path (`upload_google_credentials`, `uri_core/app/server.py:1998-2030`, `_repo_root_for_credentials` → `connection_status.py:_repo_root()`): correct, no bug found.**
- Validation (`_google_client_credentials`, `server.py:1943-1995`) returns clear, specific `HTTPException(400, detail=...)` for every real failure mode (invalid JSON, not an object, missing `installed`/`web` client_id/client_secret) - already informative enough to show the user, once actually surfaced (see §2.3).
- Write is atomic (`tempfile.NamedTemporaryFile` + `fsync` + `os.replace`) to `credentials_root/credentials.json`.
- `credentials_root` = `connection_status._repo_root()`, which (as of the M25 batch, same session) checks `os.environ["URI_GOOGLE_CREDENTIALS_DIR"]` first, falling back to the actual repository root. **Confirmed via direct filesystem search: no `credentials.json` exists anywhere on this machine** (repo root, user home, `uri_workspace/`) - so the User's belief that "credentials.json actually exists on the machine" does not hold; nothing has ever been successfully saved. `POST /connections/gmail/authorize` returning 200 (item 2 in the report) is expected and correct: it is a read-only status/instruction endpoint (see its own docstring, `server.py:2246-2273`) that deliberately never launches the interactive consent flow itself - a 200 here only means the request was authorized and answered honestly, not that a client secret exists.
- Endpoint is USER-authenticated (`_resolve_authenticated_principal`, added this same session's M25 batch) - 401 anonymous, never 403 for a non-admin. This is correct and already fixed; not a cause of the current failure.

**Authentication headers (`_jsonHeaders`, `http_uri_client.dart:116-122`): correct, no bug found.** Includes `Authorization: Bearer <token>` whenever a token is present. If the User is logged in, the request reaches the backend authenticated.

### §2.1 Root cause A — `saveGoogleCredentials` swallows every real error (`http_uri_client.dart:1871-1895`)

```dart
Future<bool> saveGoogleCredentials(...) async {
  try {
    final response = await _http.post(..., body: jsonEncode({...}))...;
    return response.statusCode == 200;   // <-- only true/false ever returned
  } catch (_) {
    return false;                          // <-- network error also collapsed to false
  }
}
```

Every 400 (bad JSON, missing fields), 401 (not logged in), or 500 the backend already returns with a specific, useful `detail` message is discarded — the caller sees only `false`. `connections_screen.dart:102`'s `_configureCredentials` then shows one fixed, generic string regardless of the real reason: `'Credentials could not be saved. Check the values and your admin access.'` — **this text is now also stale**: "admin access" no longer applies since this endpoint stopped being ADMIN-gated in the M25 batch (same session). The User has no way to learn WHY a save failed (malformed JSON, empty fields, network issue, or genuinely nothing wrong at all).

### §2.2 Root cause B — the `_dependents.isEmpty` Flutter assertion (`connections_screen.dart:_configureCredentials`, roughly lines 93-104)

```dart
onPressed: saving ? null : () async {
  setDialogState(() { saving = true; error = null; });
  final saved = await state.saveGoogleCredentials(...);
  if (!dialogContext.mounted) return;
  if (saved) {
    Navigator.of(dialogContext).pop();      // (1) pop the dialog
    await state.loadConnections();          // (2) THEN mutate AppState -> notifyListeners()
    if (mounted) messenger.showSnackBar(...);
  } else {
    setDialogState(() { saving = false; error = '...'; });
  }
},
```

`state.loadConnections()` calls `notifyListeners()`, which synchronously rebuilds `ConnectionsScreen`'s `ListenableBuilder` (the widget that is the dialog's own ancestor in the tree). Popping the dialog (1) schedules its route for removal on the next frame, but the `AppStateScope`/`Theme` inherited-widget dependents the dialog's own `StatefulBuilder`/`AlertDialog` subtree registered are not necessarily cleaned up before step (2)'s synchronous rebuild fires in the same microtask — exactly the well-known Flutter race that produces `Failed assertion: '_dependents.isEmpty': is not true` in `Element.deactivate()`/`unmount()`. **Fix: reorder — refresh the state that triggers a parent rebuild BEFORE popping the dialog, not after:**

```dart
if (saved) {
  await state.loadConnections();          // (1) mutate/rebuild FIRST, while the dialog is still mounted
  if (!dialogContext.mounted) return;
  Navigator.of(dialogContext).pop();       // (2) THEN pop
  if (mounted) messenger.showSnackBar(...);
}
```

This is the standard, minimal fix for this exact assertion pattern (reorder state-mutation-that-rebuilds-an-ancestor to happen before, not after, the dialog's own `Navigator.pop`) — no `StatefulBuilder`/dialog architecture change needed.

### §2.3 The combined effect

Because of §2.1, the User has never seen *why* a save attempt failed (or if it even reached the backend) — only a generic, now-also-inaccurate message. Because of §2.2, the dialog can crash/misbehave on what should be the *success* path, which can itself abort the flow before the user perceives success. Together these fully explain "I filled in Configure Credentials and nothing worked, with no explanation" without needing any change to the backend's already-correct validation/path/write logic.

---

## §3. Exact required changes (for Codex)

### 3.1 `uri_ui/lib/services/uri_client.dart`
Change the abstract method's return type/contract:
```dart
/// Returns null on success, or the backend's own error detail string
/// on failure (400/401/422/500 body's "detail" field, or a generic
/// network-failure message) - never collapsed to a bare bool, so the
/// caller can show the User the REAL reason a save failed.
Future<String?> saveGoogleCredentials({String? rawJson, String? clientId, String? clientSecret});
```
(Returning `String? error` — null means success — is the minimal-diff way to carry a real error message without inventing a new result type; matches this codebase's existing `submitProviderKey`/similar patterns where feasible, but check for the closest existing convention in `uri_client.dart` and prefer that shape if one already exists for "success or specific error message.")

### 3.2 `uri_ui/lib/services/http_uri_client.dart` (`saveGoogleCredentials`, ~line 1871)
```dart
Future<String?> saveGoogleCredentials({...}) async {
  try {
    final response = await _http.post(..., body: ...).timeout(...);
    if (response.statusCode == 200) return null;
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['detail']?.toString() ?? 'Save failed (HTTP ${response.statusCode}).';
    } catch (_) {
      return 'Save failed (HTTP ${response.statusCode}).';
    }
  } on TimeoutException {
    return 'URI backend did not respond in time.';
  } catch (e) {
    return 'Could not reach the URI backend: $e';
  }
}
```
Apply the identical fix to `mock_uri_client.dart`'s implementation (return `null` on its existing success path, a plausible fixed error string on its existing failure path) so both implementations satisfy the same interface.

### 3.3 `uri_ui/lib/screens/connections/connections_screen.dart` (`_configureCredentials`)
- Update the call site to use the new `String?` contract: `final error = await state.saveGoogleCredentials(...)`.
- On `error == null`: reorder exactly as in §2.2 — `await state.loadConnections()` **before** `Navigator.of(dialogContext).pop()`, guarded by the same `dialogContext.mounted` check, `messenger.showSnackBar` last.
- On `error != null`: `setDialogState(() { saving = false; this.error = error; })` — show the REAL backend/network message, not the generic stale string. Remove "and your admin access" from any remaining fallback copy — it no longer applies.
- `state.saveGoogleCredentials(...)` in `app_state.dart` (~line 610) needs its return type updated to match (`Future<String?>`), and its own call site/callers updated accordingly.

### 3.4 No backend change required
§2's trace confirms `upload_google_credentials`, `_google_client_credentials`, `_repo_root_for_credentials`/`connection_status._repo_root()` (including its `URI_GOOGLE_CREDENTIALS_DIR` override from the M25 batch) are already correct. Do not modify them beyond what's needed to keep the response body's `detail` field exactly as it already is (client-visible error surfacing is a pure client-side fix here).

---

## §4. Required tests (for Codex to add)

**Backend** (likely already adequately covered by existing `/connections/credentials` tests if any exist — verify, and add if missing):
1. Valid `raw_json` credentials → 200, `credentials.json` written atomically at the resolved canonical path.
2. Invalid JSON in `raw_json` → 400 with the exact expected `detail` string.
3. Valid `client_id`/`client_secret` pair with no `raw_json` → 200, written in the `{"installed": {...}}` shape.
4. Anonymous (no Authorization header) → 401.
5. `GET /connections` status transition: `not_connected` (no file) → `needs_authorization` (file present, no token) → `connected` (both present and token loads) — likely already covered by `connection_status.py`'s own existing tests; verify and extend only if a gap is found.

**Flutter:**
1. `saveGoogleCredentials` returns `null` on a 200 response.
2. `saveGoogleCredentials` returns the backend's `detail` string verbatim on a 400 response (mock a 400 body with a known `detail`).
3. `saveGoogleCredentials` returns a network-failure message when the mock HTTP client throws/times out.
4. `_configureCredentials` dialog: on a successful save, `state.loadConnections()` is called and the dialog closes without throwing — a regression test for §2.2 if practical (a widget test that pumps the dialog, taps Save with a mocked successful response, and asserts no exception is thrown and the dialog is dismissed - this is the most direct way to prove the `_dependents.isEmpty` assertion cannot recur).
5. On a failed save, the dialog shows the specific backend error text, not the old generic string.

Run: `flutter analyze` (0 issues), `flutter test` (full suite, no regressions), and the relevant backend `test_*.py` files (`python -m unittest discover -p "test_*.py"` for the full regression, confirming no new failures beyond the already-disclosed pre-existing ones tracked in `M24_STATE.md`).

---

## §5. What the User still needs to do (outside any code fix)

No `credentials.json` exists anywhere on this machine today. Once this fix lands, "Configure Credentials" will work reliably and show the real reason if it doesn't — but the User still needs a genuine Google OAuth Desktop-app client secret from Google Cloud Console (APIs & Services → Credentials → Create OAuth client ID → Desktop app → download the JSON) to paste in before Connect can ever succeed. This is unavoidable and outside any code fix — Google, not URI, issues that credential.

---

## §6. Manual end-to-end verification steps (once Codex implements)

1. `flutter run -d windows`; sign in.
2. Settings → Connections → "Configure Credentials" → paste a deliberately invalid string (e.g. `{}`) → Save → **expect the exact backend 400 detail text shown in the dialog**, not a generic message, and no crash.
3. Paste a real Google OAuth Desktop-app credentials JSON → Save → **expect the dialog to close cleanly (no `_dependents.isEmpty` crash), a snackbar confirming success, and the Connections list to refresh to `needs_authorization`.**
4. Click "Connect"/"Reconnect" on Gmail → follow the on-server-host consent flow the endpoint's own response describes → confirm token.json is written → refresh Connections → **expect `connected`.**
5. Repeat for Drive.

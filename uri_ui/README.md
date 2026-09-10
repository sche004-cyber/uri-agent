# URI Flutter UI

`uri_ui` is URI's Flutter client. It is a thin client of the FastAPI runtime
(`uri_core.app.server:app`): it renders state and calls HTTP endpoints, but it
does not make authorization, approval, capability, or execution decisions.

## Prerequisites

- Flutter SDK compatible with the Dart SDK declared in `pubspec.yaml`.
- A running URI backend for real-client use.

## Run locally

From this directory:

```powershell
flutter pub get
flutter run
```

Start the backend separately from the repository root with the project's
configured Python environment. The client defaults to its configured server
address; use **Settings → URI Server** to set the reachable backend address
for an emulator, desktop client, or phone.

## Test and analyze

```powershell
flutter test
flutter analyze
```

Widget and unit tests should inject `MockUriClient` or an appropriate test
client. Do not make tests depend on a live backend or platform plugins.

## Project layout

| Path | Purpose |
|---|---|
| `lib/main.dart` | Thin platform entry point and dependency wiring. |
| `lib/app.dart` | Application widget tree. |
| `lib/services/` | HTTP client, local non-secret preferences, device identity, and platform adapters. |
| `lib/screens/` | Feature screens and settings surfaces. |
| `lib/widgets/` | Reusable presentation widgets. |
| `test/` | Flutter widget/unit tests. |

## Development rules

- Keep Core authority in `uri_core`: the model proposes; the runtime validates,
  authorizes, approves, and executes. The UI never bypasses that chain.
- Do not embed API keys, secrets, or a production URL in the app or build
  assets. Device preferences are not a secret store.
- Preserve truthful UI state. Do not show an action as successful until the
  backend reports its actual result.
- Current uncommitted Windows/platform scaffolding is active, unverified work;
  do not treat it as a completed milestone or alter its scope incidentally.
- M22.3 endpoint authorization is next. Provider/secrets UI, Developer Mode,
  and broader M22 client work remain deferred; see the root
  `URI_M22_ARCHITECTURE.md` before extending those surfaces.

/// Canonical, single-source app metadata — one place to edit rather
/// than a literal duplicated across screens. Kept in sync with
/// pubspec.yaml's own `version:` field by hand (Flutter has no
/// zero-dependency way to read pubspec.yaml at runtime without adding
/// the `package_info_plus` plugin, which nothing else in this app
/// needs) — this constant is the single place that copy exists in Dart
/// source, so About and any future screen that needs it read the same
/// value instead of retyping the literal.
library;

/// Matches uri_ui/pubspec.yaml's `version: 1.0.0+1` (the `+1` build
/// number is not shown to the user).
const String kUriAppVersion = '1.0.0';

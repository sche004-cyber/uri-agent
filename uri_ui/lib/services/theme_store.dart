import 'package:shared_preferences/shared_preferences.dart';

import '../theme/uri_theme.dart';

/// Persists the user's Appearance choice (Settings → Appearance) across
/// launches — a per-device UI preference, same category as
/// [PreferencesStore], never sent to the backend.
///
/// Hybrid UI Frozen Blueprint §6 Batch 3 preference migration: the old
/// binary key (`uri.themeMode`, values `dark`/`light`/`system`) is read
/// once and mapped onto the 4 real themes — old `dark` → Graphite, old
/// `light` → Light Professional, old `system` stays `system` (still
/// follows the OS) — then the new key takes over. Any value this store
/// doesn't recognize (a stale/corrupted key, or no key at all) falls
/// back to the recorded default, [UriThemeChoice.graphite], matching
/// this app's previous "new installs open dark" default.
class ThemeStore {
  static const _key = 'uri.themeChoice';
  static const _legacyKey = 'uri.themeMode';
  static const _defaultChoice = UriThemeChoice.graphite;

  Future<UriThemeChoice> load() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(_key);
    if (stored != null) {
      for (final choice in UriThemeChoice.values) {
        if (choice.name == stored) return choice;
      }
      return _defaultChoice;
    }

    final legacy = prefs.getString(_legacyKey);
    switch (legacy) {
      case 'dark':
        return UriThemeChoice.graphite;
      case 'light':
        return UriThemeChoice.lightProfessional;
      case 'system':
        return UriThemeChoice.system;
      default:
        return _defaultChoice;
    }
  }

  Future<void> save(UriThemeChoice choice) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, choice.name);
  }
}

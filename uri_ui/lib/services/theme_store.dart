import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persists the user's Appearance choice (Settings → Appearance) across
/// launches — a per-device UI preference, same category as
/// [PreferencesStore], never sent to the backend. Stores [ThemeMode]'s
/// own name directly rather than inventing a parallel enum.
class ThemeStore {
  static const _key = 'uri.themeMode';

  Future<ThemeMode> load() async {
    final prefs = await SharedPreferences.getInstance();
    final name = prefs.getString(_key);
    return ThemeMode.values.where((m) => m.name == name).firstOrElse(ThemeMode.system);
  }

  Future<void> save(ThemeMode mode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, mode.name);
  }
}

extension _FirstOrElse<T> on Iterable<T> {
  T firstOrElse(T fallback) {
    final iterator = this.iterator;
    return iterator.moveNext() ? iterator.current : fallback;
  }
}

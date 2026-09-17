// Hybrid UI Frozen Blueprint §6 Batch 3: 4-theme persistence and the
// legacy binary ThemeMode -> UriThemeChoice migration (old 'dark' ->
// Graphite, old 'light' -> Light Professional, old 'system' stays
// system-following, unknown/garbage keys fall back to the recorded
// default).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/services/theme_store.dart';
import 'package:uri_ui/theme/uri_theme.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('a fresh device with no stored preference defaults to Graphite', () async {
    final loaded = await ThemeStore().load();
    expect(loaded, UriThemeChoice.graphite);
  });

  test('an explicit choice round-trips through the store', () async {
    final store = ThemeStore();
    for (final choice in UriThemeChoice.values) {
      await store.save(choice);
      expect(await store.load(), choice, reason: 'saved $choice did not round-trip');
    }
  });

  group('legacy uri.themeMode migration', () {
    test('old "dark" migrates to Graphite', () async {
      SharedPreferences.setMockInitialValues({'uri.themeMode': 'dark'});
      expect(await ThemeStore().load(), UriThemeChoice.graphite);
    });

    test('old "light" migrates to Light Professional', () async {
      SharedPreferences.setMockInitialValues({'uri.themeMode': 'light'});
      expect(await ThemeStore().load(), UriThemeChoice.lightProfessional);
    });

    test('old "system" stays system-following', () async {
      SharedPreferences.setMockInitialValues({'uri.themeMode': 'system'});
      expect(await ThemeStore().load(), UriThemeChoice.system);
    });

    test('an unrecognized legacy value falls back to the recorded default', () async {
      SharedPreferences.setMockInitialValues({'uri.themeMode': 'not-a-real-mode'});
      expect(await ThemeStore().load(), UriThemeChoice.graphite);
    });

    test('a new-key value takes priority over a stale legacy key', () async {
      SharedPreferences.setMockInitialValues({
        'uri.themeMode': 'light',
        'uri.themeChoice': 'slateTeal',
      });
      expect(await ThemeStore().load(), UriThemeChoice.slateTeal);
    });
  });

  group('resolveUriColors', () {
    test('an explicit theme ignores platform brightness', () {
      expect(
        resolveUriColors(UriThemeChoice.deepNavy, Brightness.light),
        UriColors.deepNavy,
      );
      expect(
        resolveUriColors(UriThemeChoice.deepNavy, Brightness.dark),
        UriColors.deepNavy,
      );
    });

    test('system follows platform brightness: dark -> Graphite, light -> Light Professional', () {
      expect(
        resolveUriColors(UriThemeChoice.system, Brightness.dark),
        UriColors.graphite,
      );
      expect(
        resolveUriColors(UriThemeChoice.system, Brightness.light),
        UriColors.lightProfessional,
      );
    });
  });
}

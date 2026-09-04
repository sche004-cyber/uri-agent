import 'package:shared_preferences/shared_preferences.dart';

import '../models/user_preferences.dart';

/// Lightweight local persistence for the small set of preferences that
/// actually change URI's behaviour (see UserPreferences). This is a
/// per-device UI convenience, not a backend: nothing here is sensitive,
/// nothing here is shared across devices, and it stores nothing the
/// Python runtime is responsible for (facts, evidence, authorization,
/// credentials all remain entirely outside Flutter).
class PreferencesStore {
  static const _keyCompletedOnboarding = 'uri.completedOnboarding';
  static const _keyFocusAreas = 'uri.focusAreas';
  static const _keyCommunicationStyle = 'uri.communicationStyle';
  static const _keyAutonomyLevel = 'uri.autonomyLevel';

  Future<UserPreferences> load() async {
    final prefs = await SharedPreferences.getInstance();

    final completed = prefs.getBool(_keyCompletedOnboarding) ?? false;
    if (!completed) {
      return const UserPreferences.initial();
    }

    return UserPreferences(
      focusAreas: prefs.getStringList(_keyFocusAreas) ?? const [],
      communicationStyle: _styleFromName(prefs.getString(_keyCommunicationStyle)),
      autonomyLevel: _autonomyFromName(prefs.getString(_keyAutonomyLevel)),
      completedOnboarding: true,
    );
  }

  Future<void> save(UserPreferences preferences) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyCompletedOnboarding, preferences.completedOnboarding);
    await prefs.setStringList(_keyFocusAreas, preferences.focusAreas);
    await prefs.setString(_keyCommunicationStyle, preferences.communicationStyle.name);
    await prefs.setString(_keyAutonomyLevel, preferences.autonomyLevel.name);
  }

  CommunicationStyle _styleFromName(String? name) {
    return CommunicationStyle.values
        .where((v) => v.name == name)
        .firstOrElse(CommunicationStyle.concise);
  }

  AutonomyLevel _autonomyFromName(String? name) {
    return AutonomyLevel.values
        .where((v) => v.name == name)
        .firstOrElse(AutonomyLevel.askEveryTime);
  }
}

extension _FirstOrElse<T> on Iterable<T> {
  T firstOrElse(T fallback) {
    final iterator = this.iterator;
    return iterator.moveNext() ? iterator.current : fallback;
  }
}

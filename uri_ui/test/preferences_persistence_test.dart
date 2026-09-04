// Covers requirement #2: onboarding completion and behaviour-changing
// preferences persist locally, so reopening the app does not restart
// onboarding unnecessarily.

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/preferences_store.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('a fresh device has not completed onboarding', () async {
    final loaded = await PreferencesStore().load();
    expect(loaded.completedOnboarding, isFalse);
  });

  test('saved preferences round-trip through the store', () async {
    final store = PreferencesStore();
    const saved = UserPreferences(
      focusAreas: ['Document drafting', 'Scheduling & meetings'],
      communicationStyle: CommunicationStyle.formal,
      autonomyLevel: AutonomyLevel.routineAutoApprove,
      completedOnboarding: true,
    );

    await store.save(saved);
    final loaded = await store.load();

    expect(loaded.completedOnboarding, isTrue);
    expect(loaded.communicationStyle, CommunicationStyle.formal);
    expect(loaded.autonomyLevel, AutonomyLevel.routineAutoApprove);
    expect(loaded.focusAreas, ['Document drafting', 'Scheduling & meetings']);
  });

  test('a returning app instance sees a prior session\'s completed onboarding', () async {
    // First "app launch": completes onboarding and persists it.
    final firstLaunch = AppState(client: MockUriClient());
    await firstLaunch.updatePreferences(
      const UserPreferences(
        focusAreas: ['Records & data lookups'],
        communicationStyle: CommunicationStyle.concise,
        autonomyLevel: AutonomyLevel.askEveryTime,
        completedOnboarding: true,
      ),
    );

    // A brand new AppState simulates the app being reopened.
    final secondLaunch = AppState(client: MockUriClient());
    expect(secondLaunch.preferences.completedOnboarding, isFalse);

    await secondLaunch.loadPersistedPreferences();

    expect(secondLaunch.preferences.completedOnboarding, isTrue);
    expect(secondLaunch.preferences.focusAreas, ['Records & data lookups']);
  });
}

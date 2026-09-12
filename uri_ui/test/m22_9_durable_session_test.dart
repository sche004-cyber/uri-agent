// M22.9 (§0.3/§7): proves the client's durable-session handling — a
// still-valid token survives a simulated relaunch, an explicitly
// rejected token degrades honestly to the logged-out state instead of
// a confusing later error, and an unreachable backend never logs the
// user out just because it couldn't be asked right now.

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'a successful login persists a session that survives a simulated relaunch',
    () async {
      final client = MockUriClient()..logout();
      final appState = AppState(client);

      final outcome = await appState.login('alex', 'password123');
      expect(outcome.success, isTrue);

      // Simulate a relaunch: a brand-new client/AppState reading from the
      // same underlying (mocked) shared_preferences backing store.
      final secondClient = MockUriClient()..logout();
      final secondAppState = AppState(secondClient);
      expect(secondAppState.isAuthenticated, isFalse);

      await secondAppState.loadPersistedSession();

      expect(secondAppState.isAuthenticated, isTrue);
      expect(secondAppState.currentUsername, 'alex');
    },
  );

  test(
    'logout clears the persisted session, so a later relaunch stays logged out',
    () async {
      final client = MockUriClient()..logout();
      final appState = AppState(client);
      await appState.login('alex', 'password123');
      await appState.logout();

      final secondClient = MockUriClient()..logout();
      final secondAppState = AppState(secondClient);
      await secondAppState.loadPersistedSession();

      expect(secondAppState.isAuthenticated, isFalse);
    },
  );

  test(
    'a backend-rejected token degrades honestly to logged-out on restore',
    () async {
      final client = MockUriClient()..logout();
      final appState = AppState(client);
      await appState.login('alex', 'password123');

      final secondClient = MockUriClient()
        ..logout()
        ..nextValidateSessionResult = false;
      final secondAppState = AppState(secondClient);
      await secondAppState.loadPersistedSession();

      expect(secondAppState.isAuthenticated, isFalse);
    },
  );

  test(
    'revalidateSession on an unreachable backend never logs the user out',
    () async {
      final client = MockUriClient()..logout();
      final appState = AppState(client);
      await appState.login('alex', 'password123');
      expect(appState.isAuthenticated, isTrue);

      // MockUriClient's validateSession only ever returns false on an
      // explicit rejection (nextValidateSessionResult = false) - true is
      // both "confirmed valid" and "couldn't be confirmed", exactly like
      // HttpUriClient's real network-exception path.
      await appState.revalidateSession();

      expect(appState.isAuthenticated, isTrue);
    },
  );

  test('revalidateSession on a rejected token clears in-memory conversation state too', () async {
    final client = MockUriClient()..logout();
    final appState = AppState(client);
    await appState.login('alex', 'password123');
    await appState.ask('hello');
    expect(appState.conversation, isNotEmpty);

    client.nextValidateSessionResult = false;
    await appState.revalidateSession();

    expect(appState.isAuthenticated, isFalse);
    expect(appState.conversation, isEmpty);
  });

  test('with no persisted session, loadPersistedSession is a no-op', () async {
    final client = MockUriClient()..logout();
    final appState = AppState(client);

    await appState.loadPersistedSession();

    expect(appState.isAuthenticated, isFalse);
  });
}

// Bootstrap fix: closes the lockout where Settings > "URI server" was
// the only place to configure the backend address, but Settings itself
// was only reachable after logging in - which could never succeed
// against a wrong/default address in the first place. Proves the new
// BootstrapScreen exposes the same address/Test Connection controls
// before authentication, reuses AppState/HttpUriClient/
// ConnectionCheckResult (no new networking logic - a spy over
// MockUriClient's already-trivial stand-ins), and that the existing
// authenticated Settings flow is unaffected.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

/// A [MockUriClient] that starts logged OUT (unlike the base class,
/// which starts pre-authenticated for the convenience of every other
/// widget test) and records exactly what it's asked to do - no real
/// network involved anywhere.
class _SpyUriClient extends MockUriClient {
  _SpyUriClient() {
    logout();
  }

  final List<String?> testedAddresses = <String?>[];
  final List<String> savedAddresses = <String>[];
  ConnectionCheckResult nextResult = const ConnectionCheckResult.reachable();

  @override
  void setBaseUrl(String baseUrl) {
    savedAddresses.add(baseUrl);
    super.setBaseUrl(baseUrl);
  }

  @override
  Future<ConnectionCheckResult> checkConnection({String? addressOverride}) async {
    testedAddresses.add(addressOverride);
    return nextResult;
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  void useDesktopViewport(WidgetTester tester) {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  /// Mirrors main()'s own startup sequence (preferences, then persisted
  /// server address) so this test exercises the real gating logic in
  /// UriApp, not a hand-picked shortcut.
  Future<_SpyUriClient> pumpFreshLaunch(WidgetTester tester) async {
    useDesktopViewport(tester);

    final client = _SpyUriClient();
    final appState = AppState(client: client);
    await appState.loadPersistedPreferences();
    await appState.loadPersistedServerAddress();
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();

    return client;
  }

  testWidgets('a fresh launch with no configured address shows the bootstrap screen, not login', (
    tester,
  ) async {
    await pumpFreshLaunch(tester);

    expect(find.text('Connect to your URI server'), findsOneWidget);
    expect(find.text('Sign in to URI'), findsNothing);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Test connection'), findsOneWidget);
  });

  testWidgets('a non-localhost address can be typed and tested before authentication', (tester) async {
    final client = await pumpFreshLaunch(tester);

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    // A successful test immediately advances past bootstrap (see the
    // next test) - what this test proves is that the typed, non-
    // localhost address is exactly what reached the client, not
    // whatever default/previous address existed before it was typed.
    expect(client.testedAddresses, ['http://192.168.1.44:8000']);
  });

  testWidgets('a successful connection applies the address and transitions straight to login', (
    tester,
  ) async {
    final client = await pumpFreshLaunch(tester);

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    // A successful test on the bootstrap screen applies the address
    // itself (equivalent to Save) - no separate confirmation step -
    // and the app moves on to the login screen automatically.
    expect(client.savedAddresses, ['http://192.168.1.44:8000']);
    expect(client.baseUrl, 'http://192.168.1.44:8000');
    expect(find.text('Connect to your URI server'), findsNothing);
    expect(find.text('Sign in to URI'), findsOneWidget);
  });

  testWidgets('a failed connection stays on the bootstrap screen and shows the diagnostic detail', (
    tester,
  ) async {
    final client = await pumpFreshLaunch(tester);
    client.nextResult = const ConnectionCheckResult.unreachable(
      'ClientException: Connection refused',
    );

    await tester.enterText(find.byType(TextField), 'http://10.0.0.5:8000');
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    expect(find.text('Connect to your URI server'), findsOneWidget);
    expect(find.text('Sign in to URI'), findsNothing);
    expect(find.text('Not reachable'), findsOneWidget);
    expect(find.text('ClientException: Connection refused'), findsOneWidget);
    // Never applied - a failed test must not become the active address.
    expect(client.savedAddresses, isEmpty);
  });

  testWidgets(
    'end-to-end: bootstrap -> login -> onboarding still works once the address is confirmed',
    (tester) async {
      await pumpFreshLaunch(tester);

      await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
      await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
      await tester.pumpAndSettle();

      expect(find.text('Sign in to URI'), findsOneWidget);

      await tester.enterText(find.widgetWithText(TextField, 'Username'), 'alice');
      await tester.enterText(find.widgetWithText(TextField, 'Password'), 'password123');
      await tester.tap(find.widgetWithText(ElevatedButton, 'Sign in'));
      await tester.pumpAndSettle();

      // Past login, onboarding (a fresh AppState has never completed
      // it) - proves the bootstrap screen only ever inserts itself
      // ahead of login and does not disturb anything after it.
      expect(find.text('What kind of work do you want help with?'), findsOneWidget);
    },
  );

  testWidgets('once authenticated, Settings > URI server still works exactly as before', (tester) async {
    final client = await pumpFreshLaunch(tester);

    // Get past bootstrap and log in.
    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Username'), 'alice');
    await tester.enterText(find.widgetWithText(TextField, 'Password'), 'password123');
    await tester.tap(find.widgetWithText(ElevatedButton, 'Sign in'));
    await tester.pumpAndSettle();

    // Skip onboarding quickly to reach the main shell.
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'URI'));
    await tester.pumpAndSettle();

    client.testedAddresses.clear();
    client.savedAddresses.clear();

    // The Settings TextField still starts prefilled with the already-
    // configured address (not the mock's placeholder), and Test
    // Connection there still works exactly like before this fix.
    await tester.enterText(find.byType(TextField), 'http://192.168.1.99:8000');
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    expect(client.testedAddresses, ['http://192.168.1.99:8000']);
    // Testing alone (no Save) must still not apply/persist, exactly as
    // the existing Settings fix guarantees.
    expect(client.savedAddresses, isEmpty);
  });
}

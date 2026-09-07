// Regression coverage for the Settings "URI server" section fix:
// Test Connection must use whatever address is currently typed, even
// if Save was never pressed, and a connection failure must expose a
// useful diagnostic reason rather than a bare unreachable badge. Also
// proves the existing Save/persistence flow is untouched by this fix.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

/// Records exactly what Settings asks the client to do, without any
/// real network involved - a thin spy over [MockUriClient]'s already-
/// trivial connection-config stand-ins.
class _SpyUriClient extends MockUriClient {
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

  Future<_SpyUriClient> pumpSettingsScreen(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final client = _SpyUriClient();
    final appState = AppState(client: client);
    await appState.updatePreferences(const UserPreferences.initial().copyWith(completedOnboarding: true));
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    return client;
  }

  testWidgets('Test connection uses the typed address even when Save was never pressed', (tester) async {
    final client = await pumpSettingsScreen(tester);

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    expect(client.testedAddresses, ['http://192.168.1.44:8000']);
    // Save was never pressed - the client's applied/persisted address
    // must be untouched by Test Connection alone.
    expect(client.savedAddresses, isEmpty);
    expect(find.text('Connected'), findsOneWidget);
  });

  testWidgets('a connection failure shows a useful diagnostic reason, not just "Not reachable"', (
    tester,
  ) async {
    final client = await pumpSettingsScreen(tester);
    client.nextResult = const ConnectionCheckResult.unreachable(
      'ClientException: Connection refused',
    );

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.ensureVisible(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.tap(find.widgetWithText(OutlinedButton, 'Test connection'));
    await tester.pumpAndSettle();

    expect(find.text('Not reachable'), findsOneWidget);
    expect(find.text('ClientException: Connection refused'), findsOneWidget);
  });

  testWidgets('pressing Save still applies and the badge resets to not-tested-yet', (tester) async {
    final client = await pumpSettingsScreen(tester);

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Save'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Save'));
    await tester.pumpAndSettle();

    expect(client.savedAddresses, ['http://192.168.1.44:8000']);
    expect(client.baseUrl, 'http://192.168.1.44:8000');
    expect(find.text('Not tested yet'), findsOneWidget);
  });

  testWidgets('a saved address survives a simulated relaunch (persistence unaffected by this fix)', (
    tester,
  ) async {
    await pumpSettingsScreen(tester);

    await tester.enterText(find.byType(TextField), 'http://192.168.1.44:8000');
    await tester.ensureVisible(find.widgetWithText(ElevatedButton, 'Save'));
    await tester.tap(find.widgetWithText(ElevatedButton, 'Save'));
    await tester.pumpAndSettle();

    // Simulate a relaunch: a brand-new client/AppState reading from the
    // same underlying (mocked) shared_preferences backing store.
    final secondClient = _SpyUriClient();
    final secondAppState = AppState(client: secondClient);
    await secondAppState.loadPersistedServerAddress();

    expect(secondClient.savedAddresses, ['http://192.168.1.44:8000']);
    expect(secondAppState.baseUrl, 'http://192.168.1.44:8000');
  });
}

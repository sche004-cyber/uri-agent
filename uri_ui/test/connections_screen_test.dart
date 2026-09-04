// Covers the second required flow:
//   Home -> Connections -> inspect connection states
//
// Also exercises authorizing a not-connected / needs-authorization
// service, confirming the UI reflects the (mock) state change.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/main.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpPostOnboardingApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final appState = AppState(client: MockUriClient());
    await appState.updatePreferences(const UserPreferences.initial().copyWith(completedOnboarding: true));
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();
  }

  testWidgets('Connections shows the three distinct connection states', (tester) async {
    await pumpPostOnboardingApp(tester);

    await tester.tap(find.text('Connections'));
    await tester.pumpAndSettle();

    expect(find.text('Gmail'), findsOneWidget);
    expect(find.text('Connected'), findsWidgets);
    expect(find.text('Needs authorization'), findsOneWidget);
    expect(find.text('Not connected'), findsOneWidget);

    expect(find.widgetWithText(OutlinedButton, 'Reconnect'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Connect'), findsOneWidget);
  });

  testWidgets('authorizing a not-connected service updates its state', (tester) async {
    await pumpPostOnboardingApp(tester);

    await tester.tap(find.text('Connections'));
    await tester.pumpAndSettle();

    expect(find.text('Not connected'), findsOneWidget);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Connect'));
    await tester.pumpAndSettle();

    expect(find.text('Not connected'), findsNothing);
    expect(find.widgetWithText(TextButton, 'Disconnect'), findsWidgets);
  });

  testWidgets('reconnecting a needs-authorization service updates its state', (tester) async {
    await pumpPostOnboardingApp(tester);

    await tester.tap(find.text('Connections'));
    await tester.pumpAndSettle();

    expect(find.text('Needs authorization'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Reconnect'));
    await tester.pumpAndSettle();

    expect(find.text('Needs authorization'), findsNothing);
  });
}

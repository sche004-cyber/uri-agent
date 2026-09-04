// Smoke test: first launch -> onboarding -> Home.
//
// Verifies the app starts on onboarding (not the main shell) until
// preferences.completedOnboarding is true, and that completing the
// short onboarding flow lands on Home with the shell navigation visible.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/main.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  /// Forces the desktop-first sidebar layout (AppShell switches to a
  /// bottom nav below 900 logical px) so these tests exercise the
  /// primary navigation surface deterministically.
  void useDesktopViewport(WidgetTester tester) {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  setUp(() {
    // AppState.updatePreferences persists via shared_preferences; this
    // gives it an in-memory backend instead of a real platform channel.
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('first launch shows onboarding, not the main shell', (tester) async {
    useDesktopViewport(tester);
    final appState = AppState(client: MockUriClient());
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();

    expect(find.text('What kind of work do you want help with?'), findsOneWidget);
    expect(find.text('Good to see you.'), findsNothing);
  });

  testWidgets('completing onboarding arrives at Home with shell navigation', (tester) async {
    useDesktopViewport(tester);
    final appState = AppState(client: MockUriClient());
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();

    // Step 1: focus areas (optional) -> Continue.
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    // Step 2: communication style (default already selected) -> Continue.
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    // Step 3: approval level (default already selected) -> Get started.
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();

    expect(appState.preferences.completedOnboarding, isTrue);
    expect(find.text('Good to see you.'), findsOneWidget);

    // The persistent navigation shell is present.
    expect(find.text('Ask URI'), findsWidgets);
    expect(find.text('Connections'), findsWidgets);
    expect(find.text('Activity'), findsWidgets);
    expect(find.text('Settings'), findsWidgets);
  });
}

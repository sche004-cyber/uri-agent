import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
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

    final appState = AppState(MockUriClient());
    await appState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();
  }

  testWidgets('Edge Brain Lab renders candidates matrix and handles probe', (
    tester,
  ) async {
    await pumpPostOnboardingApp(tester);

    // Navigate to Settings
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    // Select Edge Brain Lab in settings navigation
    await tester.tap(find.text('Edge Brain Lab'));
    await tester.pumpAndSettle();

    // Verify Candidate matrix truthful data
    expect(find.text('Candidate Qualification Matrix (M33.2)'), findsOneWidget);
    expect(find.text('Needle 3'), findsOneWidget);
    expect(find.text('SmolLM2-135M'), findsOneWidget);
    expect(find.text('Faster-Whisper (STT)'), findsOneWidget);

    // Verify Needle 3 is RESIDENT and others BYPASSED / UNAVAILABLE
    expect(find.text('RESIDENT'), findsWidgets);
    expect(find.text('BYPASSED'), findsWidgets);
    expect(find.text('UNAVAILABLE'), findsWidgets);

    // Verify Live Reflex Probe
    expect(find.text('Live Reflex Probe'), findsOneWidget);

    // Tap quick action chip 'hello'
    await tester.tap(find.widgetWithText(ActionChip, 'hello'));
    await tester.pumpAndSettle();

    // Verify probe result appears with EDGE_REPLY and candidate Needle 3
    expect(find.text('EDGE_REPLY'), findsWidgets);
    expect(find.text('Candidate: Needle 3'), findsOneWidget);

    // Benchmark-only discovery is explicit and never implies promotion.
    final discoverButton = find.widgetWithText(FilledButton, 'Discover local');
    await tester.ensureVisible(discoverButton);
    await tester.pumpAndSettle();
    await tester.tap(discoverButton);
    await tester.pumpAndSettle();
    expect(find.text('Experimental Candidates'), findsOneWidget);
    expect(find.text('qwen3.5:9b'), findsOneWidget);
    expect(
      find.textContaining('never installs system software'),
      findsOneWidget,
    );
  });
}

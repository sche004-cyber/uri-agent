// Covers the core required flow:
//   Home -> Ask URI -> see a proposed action -> approve/cancel -> see result
//
// Also exercises the cancel path, and the direct-answer path (a question
// that never produces a proposal at all) to confirm the UI keeps
// understanding/proposal, approval, and execution/result visually
// distinct rather than collapsing them.

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

  Future<AppState> pumpPostOnboardingApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final appState = AppState(client: MockUriClient());
    await appState.updatePreferences(const UserPreferences.initial().copyWith(completedOnboarding: true));
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();
    return appState;
  }

  testWidgets('asking from Home surfaces a proposal that can be approved to a result', (tester) async {
    await pumpPostOnboardingApp(tester);

    await tester.enterText(
      find.byType(TextField),
      'Please draft a note about the insurance policy renewal',
    );
    await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
    await tester.pumpAndSettle();

    // Navigated to Ask URI, and a proposal — not yet a result — is shown.
    expect(find.text('Proposed action'), findsOneWidget);
    expect(find.text('Approve'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
    expect(find.text('Result'), findsNothing);

    await tester.tap(find.text('Approve'));
    await tester.pumpAndSettle();

    // The proposal block remains (what was proposed stays visible) and a
    // separate result block now appears — approval and execution/result
    // are not the same visual event.
    expect(find.text('Proposed action'), findsOneWidget);
    expect(find.text('Result'), findsOneWidget);
    expect(find.text('Approve'), findsNothing);
    expect(find.text('Cancel'), findsNothing);
  });

  testWidgets('cancelling a proposal reports no action was taken', (tester) async {
    await pumpPostOnboardingApp(tester);

    // Gmail is connected in the seed data, so this reaches a normal
    // proposal rather than the connection-gated path.
    await tester.enterText(find.byType(TextField), 'Draft a reply to that email');
    await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
    await tester.pumpAndSettle();

    expect(find.text('Cancel'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(find.text('Cancelled'), findsWidgets);
    expect(find.text('No action was taken.'), findsOneWidget);
  });

  testWidgets('a direct question is answered without any proposal or approval step', (tester) async {
    await pumpPostOnboardingApp(tester);

    await tester.enterText(find.byType(TextField), 'What is on my calendar today');
    await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
    await tester.pumpAndSettle();

    expect(find.text('Proposed action'), findsNothing);
    expect(find.text('Approve'), findsNothing);
    expect(find.text('Result'), findsOneWidget);
  });

  testWidgets('a request needing a disconnected service is gated, not proposed', (tester) async {
    await pumpPostOnboardingApp(tester);

    // Calendar is seeded as "needs authorization", not connected.
    await tester.enterText(find.byType(TextField), 'Schedule a meeting with the department');
    await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
    await tester.pumpAndSettle();

    // URI does not pretend it can proceed: no proposal, no approval
    // controls, just an honest "connection needed" state.
    expect(find.text('Proposed action'), findsNothing);
    expect(find.text('Approve'), findsNothing);
    expect(find.text('Cancel'), findsNothing);
    expect(find.text('Connection needed'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Connect Calendar'), findsOneWidget);

    // The connect action takes the user to Connections, where they can
    // actually resolve it. Pumped in explicit steps (rather than a bare
    // pumpAndSettle) so the mock's fixed-latency load is deterministically
    // flushed across the tab-switch boundary.
    await tester.tap(find.widgetWithText(OutlinedButton, 'Connect Calendar'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('Needs authorization'), findsOneWidget);
  });
}

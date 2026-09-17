import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/screens/ask/ask_uri_screen.dart';
import 'package:uri_ui/screens/home/home_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<AppState> pumpHybridApp(
    WidgetTester tester, {
    MockUriClient? client,
    Size size = const Size(1280, 900),
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mockClient = client ?? MockUriClient();
    final state = AppState(mockClient);
    await state.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: state));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    return state;
  }

  testWidgets(
    'desktop Home renders 5-destination sidebar, exactly 4 truthful metric tiles, and no embedded composer',
    (tester) async {
      await pumpHybridApp(tester);

      // 5-destination sidebar items
      expect(find.text('Home'), findsWidgets);
      expect(find.text('Chat'), findsWidgets);
      expect(find.text('Tasks'), findsWidgets);
      expect(find.text('Connections & Providers'), findsWidgets);
      expect(find.text('Settings'), findsWidgets);

      // Live UX Repair §1: the topbar's 4 theme swatches were removed
      // on the User's direct instruction - theme selection lives only
      // under Settings > Appearance now (see redesign_test.dart's
      // "appearance" group). The topbar keeps only the compact toggle.
      expect(find.byTooltip('Graphite'), findsNothing);
      expect(find.byTooltip('Deep Navy'), findsNothing);
      expect(find.byTooltip('Slate + Teal'), findsNothing);
      expect(find.byTooltip('Light Professional'), findsNothing);
      expect(find.byTooltip('Compact mode'), findsOneWidget);

      // Exactly 4 truthful metric tiles
      expect(find.text('PENDING APPROVALS'), findsOneWidget);
      expect(find.text('UNREAD EMAIL'), findsOneWidget);
      expect(find.text('CONNECTED SERVICES'), findsOneWidget);
      expect(find.text('BRAIN / PROVIDER'), findsOneWidget);

      // Explicitly omitted fabricated tiles
      expect(find.text('Upcoming Deadline'), findsNothing);
      expect(find.text('Halted Workflows'), findsNothing);

      // Suggested actions panel
      expect(find.text('SUGGESTED ACTIONS'), findsOneWidget);

      // No embedded composer on Home
      expect(find.byType(UriCommandDock), findsNothing);
      expect(find.byType(TextField), findsNothing);
    },
  );

  testWidgets(
    'Chat is reachable on route index 1 and renders canonical composer and dock',
    (tester) async {
      await pumpHybridApp(tester);

      // Navigate to Chat
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      expect(find.byType(HomeScreen), findsNothing);
      expect(find.byType(AskUriScreen), findsOneWidget);
      expect(find.byType(UriCommandDock), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
    },
  );

  testWidgets(
    'R1: Failed metric fetches render "Unavailable", never false "0"',
    (tester) async {
      final failingClient = MockUriClient()
        ..shouldFailTasks = true
        ..shouldFailConnections = true;

      await pumpHybridApp(tester, client: failingClient);

      // Both Pending Approvals and Connected Services tiles must display Unavailable
      expect(find.text('Unavailable'), findsAtLeastNWidgets(2));

      // Must never claim 0 pending or 0 services when fetch failed
      expect(find.text('0'), findsNothing);
    },
  );

  testWidgets(
    'R2: Hoisted composer draft state survives navigation across Chat -> Home -> Tasks -> Chat',
    (tester) async {
      final state = await pumpHybridApp(tester);

      // 1. Go to Chat
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      // 2. Type an unsent draft in the composer
      const draftText = 'Draft message for institutional proposal review';
      await tester.enterText(find.byType(TextField), draftText);
      await tester.pump();

      expect(state.composerDraft, draftText);

      // 3. Navigate away to Home
      await tester.tap(find.text('Home'));
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);

      // 4. Navigate to Tasks
      await tester.tap(find.text('Tasks'));
      await tester.pumpAndSettle();

      // 5. Navigate back to Chat
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      // Verify the draft was preserved intact
      expect(find.byType(TextField), findsOneWidget);
      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.controller!.text, draftText);
      expect(state.composerDraft, draftText);
    },
  );

  testWidgets(
    'Sidebar collapse toggle switches to icon rail and persists preference in SharedPreferences',
    (tester) async {
      await pumpHybridApp(tester);

      // Initially expanded: collapse button is visible
      expect(find.byTooltip('Collapse sidebar'), findsOneWidget);
      expect(find.text('URI'), findsOneWidget);

      // Tap collapse
      await tester.tap(find.byTooltip('Collapse sidebar'));
      await tester.pumpAndSettle();

      // Now collapsed: expand button is visible, full brand text hidden
      expect(find.byTooltip('Expand sidebar'), findsOneWidget);
      expect(find.text('URI'), findsNothing);

      // Check SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getBool('uri_sidebar_collapsed_v1'), isTrue);

      // Tap expand
      await tester.tap(find.byTooltip('Expand sidebar'));
      await tester.pumpAndSettle();

      expect(find.byTooltip('Collapse sidebar'), findsOneWidget);
      expect(prefs.getBool('uri_sidebar_collapsed_v1'), isFalse);
    },
  );
}

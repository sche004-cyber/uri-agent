// Coverage for the navigation/settings/Gmail/prompt-length redesign:
//   - there is exactly one conversation surface (Home), no separate
//     "Ask URI" destination
//   - Settings is organized into named categories with a working
//     master-detail selection
//   - tapping Connect/Reconnect on a Google service always shows the
//     backend's real explanation, never a faked "Connected"
//   - the composer accepts a long prompt with no truncation or
//     character-limit error
//   - Appearance actually changes the active ThemeMode

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/connection.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

/// Gmail seeded as not-yet-authorized, with the exact honest detail
/// the real backend reports when no credentials.json exists (see
/// server.py's authorize_connection) - never a fabricated "Connected".
class _GmailNeedsSetupClient extends MockUriClient {
  static const _explanation =
      'No Google client secret (credentials.json) is configured on the '
      'URI server host yet, so sign-in cannot be started.';

  @override
  Future<List<ServiceConnection>> listConnections() async {
    return const [
      ServiceConnection(
        id: 'gmail',
        name: 'Gmail',
        description:
            'Read relevant messages and prepare replies for your review.',
        status: ConnectionStatus.notConnected,
        detail: _explanation,
      ),
    ];
  }

  @override
  Future<ConnectionAuthorizeOutcome> authorizeConnection(
    String connectionId,
  ) async {
    final connections = await listConnections();
    return ConnectionAuthorizeOutcome(
      connection: connections.first,
      explanation: _explanation,
    );
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<AppState> pumpPostOnboardingApp(
    WidgetTester tester, {
    UriClient? client,
  }) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final appState = AppState(client ?? MockUriClient());
    await appState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();
    return appState;
  }

  group('navigation', () {
    testWidgets(
      'Home is the only conversation surface: dashboard and composer together, no Ask URI tab',
      (tester) async {
        await pumpPostOnboardingApp(tester);

        // The shell has Home, Tasks, Connections, Activity, Settings -
        // never a second, separate "Ask URI" destination.
        expect(find.text('Home'), findsWidgets);
        expect(find.text('Tasks'), findsWidgets);
        expect(find.text('Connections'), findsWidgets);
        expect(find.text('Activity'), findsWidgets);
        expect(find.text('Settings'), findsWidgets);
        expect(find.text('Ask URI'), findsNothing);

        // Home shows real dashboard stats...
        expect(find.text('Pending approvals'), findsOneWidget);
        expect(find.text('Connected services'), findsOneWidget);

        // ...and the actual conversation composer, in the same screen.
        expect(find.byType(TextField), findsOneWidget);
        expect(find.byIcon(Icons.arrow_upward_rounded), findsOneWidget);
      },
    );
  });

  group('settings', () {
    testWidgets(
      'Settings lists every real category and switches content on selection',
      (tester) async {
        await pumpPostOnboardingApp(tester);

        await tester.tap(find.text('Settings'));
        await tester.pumpAndSettle();

        for (final label in [
          'Profile',
          'URI',
          'Preferences',
          'Connections',
          'Memory',
          'Capabilities',
          'Diagnostics',
          'About',
        ]) {
          expect(
            find.widgetWithText(ListTile, label),
            findsOneWidget,
            reason: '$label category missing',
          );
        }

        // Defaults to Profile.
        expect(find.text('Signed in as demo-user'), findsOneWidget);

        await tester.tap(find.widgetWithText(ListTile, 'Memory'));
        await tester.pumpAndSettle();

        // Real empty state - MockUriClient starts with no memory entries.
        expect(find.text('Nothing remembered yet'), findsOneWidget);

        await tester.tap(find.widgetWithText(ListTile, 'About'));
        await tester.pumpAndSettle();
        expect(find.textContaining('URI'), findsWidgets);
      },
    );
  });

  group('Gmail connection state', () {
    testWidgets(
      'Connect never fakes success - shows the backend\'s real explanation',
      (tester) async {
        await pumpPostOnboardingApp(tester, client: _GmailNeedsSetupClient());

        await tester.tap(find.text('Connections'));
        await tester.pumpAndSettle();

        expect(find.text('Not connected'), findsOneWidget);

        await tester.tap(find.widgetWithText(ElevatedButton, 'Connect'));
        await tester.pumpAndSettle();

        // The dialog shows the real, honest reason (also already visible
        // on the card itself) - never a fabricated "Connected" - and the
        // underlying state is genuinely unchanged.
        expect(find.text(_GmailNeedsSetupClient._explanation), findsWidgets);
        expect(find.text('Not connected'), findsOneWidget);
        expect(find.text('Connected'), findsNothing);
      },
    );
  });

  group('long prompts', () {
    testWidgets(
      'the composer accepts a long prompt with no truncation or length error',
      (tester) async {
        await pumpPostOnboardingApp(tester);

        final longPrompt =
            'Please help me draft a detailed institutional note. ' *
            40; // ~2100 chars
        expect(longPrompt.length, greaterThan(2000));

        await tester.enterText(find.byType(TextField), longPrompt);
        await tester.pump();

        final field = tester.widget<TextField>(find.byType(TextField));
        // No maxLength anywhere in the composer - the full text is kept
        // verbatim, never silently cut.
        expect(field.maxLength, isNull);
        expect(field.controller!.text, longPrompt);
      },
    );
  });

  group('appearance', () {
    testWidgets('choosing Dark actually changes the active ThemeMode', (
      tester,
    ) async {
      await pumpPostOnboardingApp(tester);

      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ListTile, 'Preferences'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Dark'));
      await tester.pumpAndSettle();

      final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
      expect(app.themeMode, ThemeMode.dark);
    });
  });
}

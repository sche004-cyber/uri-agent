// M22.2/M22.3 UI parity: role/tier visibility, device/session
// management, model/provider status, human-readable capability labels,
// and the memory category picker - the UI surfaces the M22 backend
// already carries but this client previously never wired up.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

/// Wraps [MockUriClient] to report a non-admin account, so the
/// ADMIN-only Connections gating can be exercised without a real
/// backend - MockUriClient's own single fixed account is always
/// reported as ADMIN (matching the real backend's first-account
/// bootstrap rule), so a distinct role can only come from a fake like
/// this one.
class _NonAdminMockClient extends MockUriClient {
  @override
  Future<AccountInfo?> getAccountInfo() async {
    return const AccountInfo(
      userId: 'mock-user',
      username: 'demo-user',
      role: 'USER',
      experienceTier: 'BASIC',
      deviceId: 'mock-device',
      runtimeDeviceId: 'mock-runtime-device',
    );
  }
}

Future<AppState> _pumpPostOnboardingApp(
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

Future<void> _openSettingsCategory(WidgetTester tester, String label) async {
  await tester.tap(find.text('Settings'));
  await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(ListTile, label));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Profile: role and experience tier (M22.2)', () {
    testWidgets('shows the account role and lets the user change tier', (
      tester,
    ) async {
      final appState = await _pumpPostOnboardingApp(tester);
      await _openSettingsCategory(tester, 'Profile');

      expect(find.text('ADMIN'), findsOneWidget);
      expect(find.text('Experience level'), findsOneWidget);
      expect(find.text('Basic'), findsOneWidget);
      expect(find.text('Advanced'), findsOneWidget);
      expect(appState.accountInfo?.experienceTier, 'BASIC');

      // Drives the same call path the Advanced segment's tap would
      // (AppState.setExperienceTier -> UriClient.setExperienceTier ->
      // reload), verified directly rather than depending on
      // SegmentedButton's exact hit-test geometry. tester.runAsync is
      // required here: MockUriClient's simulated latency uses a real
      // Future.delayed, which testWidgets' fake-async zone never
      // advances on its own outside of a pump - awaiting it directly
      // would hang forever.
      final accepted = await tester.runAsync(
        () => appState.setExperienceTier('ADVANCED'),
      );
      await tester.pumpAndSettle();

      expect(accepted, isTrue);
      expect(appState.accountInfo?.experienceTier, 'ADVANCED');

      // M22.8 added a second SegmentedButton<String> to this same screen
      // (the work-mode picker) - disambiguate by segment values rather
      // than by type alone, since find.byType now matches both.
      final segmented = tester.widget<SegmentedButton<String>>(
        find.byWidgetPredicate(
          (widget) =>
              widget is SegmentedButton<String> &&
              widget.segments.any((segment) => segment.value == 'ADVANCED'),
        ),
      );
      expect(segmented.selected, {'ADVANCED'});
    });
  });

  group('Profile: devices (M22.2)', () {
    testWidgets(
      'lists this account\'s active devices and marks the current one',
      (tester) async {
        await _pumpPostOnboardingApp(tester);
        await _openSettingsCategory(tester, 'Profile');

        expect(find.text('Devices'), findsOneWidget);
        expect(find.text('mock-device'), findsOneWidget);
        expect(find.text('(this device)'), findsOneWidget);
        expect(find.text('1 active session(s)'), findsOneWidget);
      },
    );

    testWidgets(
      'the confirm dialog is reachable and revoking updates the list',
      (tester) async {
        final appState = await _pumpPostOnboardingApp(tester);
        await _openSettingsCategory(tester, 'Profile');

        expect(find.text('mock-device'), findsOneWidget);

        // Two distinct "Log out" TextButtons exist on this screen: the
        // account sign-out action (top of the screen) and this device's
        // own revoke action (in the Devices section, below it) - `.last`
        // is the device one, matching visual/tree order. Only reaching
        // the confirm dialog is asserted via the widget tree; the actual
        // revoke call is verified directly below against AppState, which
        // is exactly what the dialog's confirm button itself invokes.
        await tester.tap(find.widgetWithText(TextButton, 'Log out').last);
        await tester.pumpAndSettle();
        expect(find.text('Log out this device?'), findsOneWidget);
        expect(
          find.widgetWithText(ElevatedButton, 'Log out device'),
          findsOneWidget,
        );
        await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
        await tester.pumpAndSettle();

        // See the tester.runAsync note above - same reason.
        final revoked = await tester.runAsync(
          () => appState.revokeDevice('mock-device'),
        );
        await tester.pumpAndSettle();

        expect(revoked, 1);
        expect(find.text('mock-device'), findsNothing);
        expect(
          find.text('No active devices could be read from the server.'),
          findsOneWidget,
        );
      },
    );
  });

  group('Capabilities: model status and human-readable labels (M16/M22.3)', () {
    testWidgets('shows model/provider status and a humanized capability name', (
      tester,
    ) async {
      await _pumpPostOnboardingApp(tester);
      await _openSettingsCategory(tester, 'Capabilities');

      expect(find.text('Ollama · qwen3:14b'), findsOneWidget);

      // Humanized, not the raw snake_case identifier.
      expect(find.text('Draft Institutional Note'), findsOneWidget);
      expect(find.text('draft_institutional_note'), findsNothing);
    });
  });

  group('Memory: category picker matches the backend\'s valid vocabulary', () {
    testWidgets(
      'offers exactly the five backend-valid categories, no free text',
      (tester) async {
        await _pumpPostOnboardingApp(tester);
        await _openSettingsCategory(tester, 'Memory');

        await tester.tap(
          find.widgetWithText(OutlinedButton, 'Remember something'),
        );
        await tester.pumpAndSettle();

        expect(find.byType(DropdownButtonFormField<String>), findsOneWidget);
        // A free-text "Category" TextField (the old, invalid-default-prone
        // shape) must be gone.
        expect(find.widgetWithText(TextField, 'Category'), findsNothing);

        await tester.tap(find.byType(DropdownButtonFormField<String>));
        await tester.pumpAndSettle();

        for (final label in [
          'Preference',
          'Interest',
          'Interaction pattern',
          'Explicit statement',
          'Other',
        ]) {
          // The currently-selected value's label legitimately renders
          // twice (the closed field's own display, plus the open menu) -
          // findsWidgets (>=1) is the correct assertion here, not an
          // exact count.
          expect(
            find.text(label),
            findsWidgets,
            reason: '$label option missing',
          );
        }
      },
    );
  });

  group('Connections: Google Workspace access is open to every authenticated user (2026-09-12)', () {
    testWidgets(
      'a non-admin sees enabled connect/reconnect controls and no admin-only notice',
      (tester) async {
        await _pumpPostOnboardingApp(tester, client: _NonAdminMockClient());

        await tester.tap(find.text('Connections'));
        await tester.pumpAndSettle();

        expect(find.textContaining('ADMIN-only action'), findsNothing);

        final connectButton = tester.widget<ElevatedButton>(
          find.widgetWithText(ElevatedButton, 'Connect'),
        );
        expect(connectButton.onPressed, isNotNull);

        final reconnectButton = tester.widget<OutlinedButton>(
          find.widgetWithText(OutlinedButton, 'Reconnect'),
        );
        expect(reconnectButton.onPressed, isNotNull);
      },
    );

    testWidgets(
      'an admin sees enabled connect/reconnect controls and no notice',
      (tester) async {
        await _pumpPostOnboardingApp(tester);

        await tester.tap(find.text('Connections'));
        await tester.pumpAndSettle();

        expect(find.textContaining('ADMIN-only action'), findsNothing);

        final connectButton = tester.widget<ElevatedButton>(
          find.widgetWithText(ElevatedButton, 'Connect'),
        );
        expect(connectButton.onPressed, isNotNull);
      },
    );
  });
}

// M22.4: Admin capability grant administration UI tests.
// Tests that:
// 1. Admin user sees the 'Capability Grants' settings category.
// 2. Non-admin user does not see the 'Capability Grants' category.
// 3. Admin can select an account, view capability grants, and toggle them.
// 4. Optimistic UI reverts if backend rejects the update.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

class _NonAdminMockClient extends MockUriClient {
  @override
  Future<AccountInfo?> getAccountInfo() async {
    return const AccountInfo(
      userId: 'user-secondary',
      username: 'student-user',
      role: 'USER',
      experienceTier: 'BASIC',
      deviceId: 'mock-device',
      runtimeDeviceId: 'mock-runtime-device',
    );
  }
}

class _FailingGrantUpdateMockClient extends MockUriClient {
  @override
  Future<bool> updateUserGrants(String userId, List<String> grants) async {
    return false;
  }
}

Future<AppState> _pumpApp(WidgetTester tester, {UriClient? client}) async {
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

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('admin sees Capability Grants category and can toggle a grant', (
    tester,
  ) async {
    final appState = await _pumpApp(tester);
    await tester.runAsync(() => appState.loadAccountInfo());
    await tester.pumpAndSettle();

    // Navigate to Settings
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    // Verify Capability Grants is present in settings category list
    final navItem = find.widgetWithText(ListTile, 'Capability Grants');
    expect(navItem, findsOneWidget);

    // Open Capability Grants
    await tester.tap(navItem);
    await tester.pumpAndSettle();

    // Verify user selector and capability switches are rendered
    expect(find.byType(DropdownButton<String>), findsOneWidget);
    expect(find.byType(SwitchListTile), findsWidgets);

    // Toggle the first capability switch
    final firstSwitch = find.byType(SwitchListTile).first;
    final SwitchListTile initialWidget = tester.widget(firstSwitch);
    final initialValue = initialWidget.value;

    await tester.tap(firstSwitch);
    await tester.pumpAndSettle();

    final SwitchListTile toggledWidget = tester.widget(firstSwitch);
    expect(toggledWidget.value, !initialValue);
  });

  testWidgets('grant toggle reverts if backend rejects the update', (
    tester,
  ) async {
    final appState = await _pumpApp(
      tester,
      client: _FailingGrantUpdateMockClient(),
    );
    await tester.runAsync(() => appState.loadAccountInfo());
    await tester.pumpAndSettle();

    // Navigate to Settings -> Capability Grants
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'Capability Grants'));
    await tester.pumpAndSettle();

    // Find first switch
    final firstSwitch = find.byType(SwitchListTile).first;
    final SwitchListTile initialWidget = tester.widget(firstSwitch);
    final initialValue = initialWidget.value;

    // Toggle it
    await tester.tap(firstSwitch);
    await tester.pumpAndSettle();

    // Expect value reverted back to initial
    final SwitchListTile revertedWidget = tester.widget(firstSwitch);
    expect(revertedWidget.value, initialValue);

    // SnackBar or error notice should appear
    expect(find.byType(SnackBar), findsOneWidget);
  });

  testWidgets('non-admin user does NOT see Capability Grants category', (
    tester,
  ) async {
    final appState = await _pumpApp(tester, client: _NonAdminMockClient());
    await tester.runAsync(() => appState.loadAccountInfo());
    await tester.pumpAndSettle();

    // Navigate to Settings
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    // Capability Grants should NOT be in the navigation list
    expect(find.widgetWithText(ListTile, 'Capability Grants'), findsNothing);
  });
}

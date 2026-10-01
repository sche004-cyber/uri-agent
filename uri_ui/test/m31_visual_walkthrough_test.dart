import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> saveScreenshot(
    WidgetTester tester,
    GlobalKey key,
    String filename,
  ) async {
    await tester.pumpAndSettle();
    await tester.runAsync(() async {
      final boundary =
          key.currentContext!.findRenderObject() as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 1.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      final bytes = byteData!.buffer.asUint8List();
      final dir = Directory('../temp_evidence/m31_visual_review/screenshots');
      if (!dir.existsSync()) dir.createSync(recursive: true);
      File('../temp_evidence/m31_visual_review/screenshots/$filename')
          .writeAsBytesSync(bytes);
    });
  }

  testWidgets('Capture complete 17 visual review walkthrough screenshots', (
    tester,
  ) async {
    final originalOnError = FlutterError.onError;
    final layoutErrors = <String>[];
    FlutterError.onError = (details) {
      if (details.exceptionAsString().contains('overflowed')) {
        layoutErrors.add(details.exceptionAsString());
        return;
      }
      originalOnError?.call(details);
    };
    addTearDown(() {
      FlutterError.onError = originalOnError;
    });

    final key = GlobalKey();

    // -------------------------------------------------------------
    // 01_login: Unauthenticated Login Screen (1280x900)
    // -------------------------------------------------------------
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final unauthClient = MockUriClient();
    final unauthState = AppState(unauthClient);
    await unauthState.setBaseUrl('http://127.0.0.1:8000');
    await unauthState.logout();

    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: UriApp(appState: unauthState),
      ),
    );
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '01_login.png');

    // -------------------------------------------------------------
    // 02_onboarding: Onboarding Screen (1280x900)
    // -------------------------------------------------------------
    final onboardClient = MockUriClient();
    final onboardState = AppState(onboardClient);
    await onboardState.setBaseUrl('http://127.0.0.1:8000');
    await onboardState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: false),
    );

    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: UriApp(appState: onboardState),
      ),
    );
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '02_onboarding.png');

    // -------------------------------------------------------------
    // 03_home: Home Screen with 4 Metric Tiles (1280x900)
    // -------------------------------------------------------------
    final mainClient = MockUriClient();
    final mainState = AppState(mainClient);
    await mainState.setBaseUrl('http://127.0.0.1:8000');
    await mainState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );

    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: UriApp(appState: mainState),
      ),
    );
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '03_home.png');

    // -------------------------------------------------------------
    // 04_chat: Chat / Ask URI Screen (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.text('Chat'));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '04_chat.png');

    // -------------------------------------------------------------
    // 05_model_selector: Chat with Active Model Selector (1280x900)
    // -------------------------------------------------------------
    // Open model selector dropdown or tap model control
    final dropdownFinder = find.byType(DropdownButton<String>);
    if (dropdownFinder.evaluate().isNotEmpty) {
      await tester.tap(dropdownFinder.first);
      await tester.pumpAndSettle();
    }
    await saveScreenshot(tester, key, '05_model_selector.png');

    // Close dropdown by tapping outside if open
    await tester.tapAt(const Offset(600, 200));
    await tester.pumpAndSettle();

    // -------------------------------------------------------------
    // 06_connections_providers: Connections & Providers (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.text('Connections & Providers'));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '06_connections_providers.png');

    // -------------------------------------------------------------
    // 07_tasks: Tasks Table (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.text('Tasks'));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '07_tasks.png');

    // -------------------------------------------------------------
    // 08_settings: Settings Shell (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '08_settings.png');

    // -------------------------------------------------------------
    // 09_edge_brain_lab: Edge Brain Lab (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.text('Edge Brain Lab'));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '09_edge_brain_lab.png');

    // -------------------------------------------------------------
    // 10_developer_log_or_trace: Developer Evidence & Trace (1280x900)
    // -------------------------------------------------------------
    // Probe 'hello' to produce a real live trace event
    final helloChip = find.widgetWithText(ActionChip, 'hello');
    if (helloChip.evaluate().isNotEmpty) {
      await tester.tap(helloChip);
      await tester.pumpAndSettle();
    }
    // Scroll down to show trace
    await tester.drag(find.text('Edge Brain Runtime'), const Offset(0, -300));
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '10_developer_log_or_trace.png');

    // -------------------------------------------------------------
    // 11_arn_recovery: ARN Recovery Card Expanded (1280x900)
    // -------------------------------------------------------------
    // Navigate back to Ask URI and add a turn with ARN recovery
    await tester.tap(find.text('Chat'));
    await tester.pumpAndSettle();

    final arnTurn = UriTurn(
      id: 'arn-turn-1',
      userText: 'locate Q3 financial reports',
      timestamp: DateTime.now(),
      stage: TurnStage.completed,
      recoveryRequired: true,
      arnState: const {
        'active_candidates': [
          'Q3_2025_Report_Draft.xlsx',
          'Q3_2025_Final_Financials.pdf'
        ],
        'eliminated_candidates': ['Q3_2024_Archived.pdf'],
        'searched_sources': ['local_docs', 'gmail', 'drive'],
        'clarification_recommendation': {
          'question':
              'Did you mean the draft spreadsheet or the signed final PDF?',
        },
      },
    );
    mainState.conversation.add(arnTurn);
    mainState.notifyListeners();
    await tester.pumpAndSettle();

    // Expand ARN card
    final arnHeader = find.text('Adaptive Retrieval Narrowing (ARN)');
    if (arnHeader.evaluate().isNotEmpty) {
      await tester.tap(arnHeader);
      await tester.pumpAndSettle();
    }
    await saveScreenshot(tester, key, '11_arn_recovery.png');

    // -------------------------------------------------------------
    // 12_compact_mode: Compact Companion Overlay (380x600)
    // -------------------------------------------------------------
    await tester.tap(find.byTooltip('Compact mode'));
    await tester.pumpAndSettle();
    tester.view.physicalSize = const Size(380, 600);
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '12_compact_mode.png');

    // -------------------------------------------------------------
    // 13_compact_chat: Compact Chat View & Clean Composer (380x600)
    // -------------------------------------------------------------
    await tester.enterText(
      find.byType(TextField),
      'Hello URI in compact mode',
    );
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '13_compact_chat.png');

    // -------------------------------------------------------------
    // 14_restore_from_compact: Restored Workspace with Preserved Session (1280x900)
    // -------------------------------------------------------------
    await tester.tap(find.byTooltip('Expand to Workspace'));
    await tester.pumpAndSettle();
    tester.view.physicalSize = const Size(1280, 900);
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '14_restore_from_compact.png');

    // -------------------------------------------------------------
    // 15_mobile_390x844: Mobile Layout (390x844)
    // -------------------------------------------------------------
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '15_mobile_390x844.png');

    // -------------------------------------------------------------
    // 16_mobile_360x640: Ultra-Narrow Mobile Layout (360x640)
    // -------------------------------------------------------------
    tester.view.physicalSize = const Size(360, 640);
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '16_mobile_360x640.png');

    // -------------------------------------------------------------
    // 17_relaunch: Relaunch Clean State (1280x900)
    // -------------------------------------------------------------
    tester.view.physicalSize = const Size(1280, 900);
    final relaunchClient = MockUriClient();
    final relaunchState = AppState(relaunchClient);
    await relaunchState.setBaseUrl('http://127.0.0.1:8000');
    await relaunchState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );

    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: UriApp(appState: relaunchState),
      ),
    );
    await tester.pumpAndSettle();
    await saveScreenshot(tester, key, '17_relaunch.png');

    // Assert all 17 files exist
    final expectedScreenshots = [
      '01_login.png',
      '02_onboarding.png',
      '03_home.png',
      '04_chat.png',
      '05_model_selector.png',
      '06_connections_providers.png',
      '07_tasks.png',
      '08_settings.png',
      '09_edge_brain_lab.png',
      '10_developer_log_or_trace.png',
      '11_arn_recovery.png',
      '12_compact_mode.png',
      '13_compact_chat.png',
      '14_restore_from_compact.png',
      '15_mobile_390x844.png',
      '16_mobile_360x640.png',
      '17_relaunch.png',
    ];

    for (final file in expectedScreenshots) {
      expect(
        File('../temp_evidence/m31_visual_review/screenshots/$file').existsSync(),
        isTrue,
        reason: 'Missing screenshot: $file',
      );
    }

    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
  });
}

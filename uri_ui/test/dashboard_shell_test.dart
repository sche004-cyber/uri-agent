import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/models/system_performance.dart';
import 'package:uri_ui/screens/ask/ask_uri_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/widgets/dashboard/reference_dashboard.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<void> pumpDashboard(WidgetTester tester, {Size size = const Size(1440, 920)}) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final state = AppState(MockUriClient());
    await state.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: state));
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'desktop Home is the approved dashboard shell with one command dock',
    (tester) async {
      await pumpDashboard(tester);

      expect(find.text('INTELLIGENCE FOR A BETTER TOMORROW'), findsOneWidget);
      expect(find.text('CPU'), findsOneWidget);
      expect(find.text('GPU'), findsOneWidget);
      expect(find.text('System Health'), findsOneWidget);
      expect(find.text('Sandbox & permissions'), findsOneWidget);
      expect(find.text('Active Connections'), findsOneWidget);
      expect(find.byType(UriCommandDock), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
    },
  );

  testWidgets(
    'dashboard tabs retain connector state instead of inventing inbox data',
    (tester) async {
      await pumpDashboard(tester);

      await tester.tap(find.byKey(const ValueKey('dashboard-tab-connections')));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Live connector state only. URI does not invent inbox or Drive item counts.',
        ),
        findsOneWidget,
      );
      expect(find.text('Gmail'), findsOneWidget);
      expect(find.text('Google Drive'), findsOneWidget);
    },
  );
  for (final size in [const Size(1024, 682), const Size(800, 700), const Size(390, 844)]) {
    testWidgets('dashboard fits $size without overflow', (tester) async {
      await pumpDashboard(tester, size: size);

      expect(find.byType(UriCommandDock), findsOneWidget);
    });
  }

  testWidgets('dashboard cards keep identical geometry in every presentation state',
      (tester) async {
    Future<Map<String, Rect>> pumpCards(DashboardCardState presentation) async {
      final state = AppState(MockUriClient());
      if (presentation == DashboardCardState.live) {
        state.systemPerformance = const SystemPerformanceSnapshot(
          cpuPercent: 31, logicalCores: 8, physicalCores: 4,
          memoryUsedPercent: 48, memoryTotalBytes: 16 * 1073741824,
          memoryAvailableBytes: 8 * 1073741824, diskUsedPercent: 50,
          diskFreeBytes: 100 * 1073741824, diskTotalBytes: 200 * 1073741824,
          swapAvailable: true, swapUsedPercent: 12,
        );
      }
      await tester.pumpWidget(
        MaterialApp(
          home: SizedBox(
            width: 900,
            height: 500,
            child: SingleChildScrollView(
              child: Column(
                children: [
                  ReferenceDashboard(
                    state: state,
                    presentationStateOverride: presentation,
                    onGoTo: (_, {settingsCategory}) {},
                  ),
                  SizedBox(
                    width: 205,
                    height: 700,
                    child: ReferenceRail(
                      state: state,
                      presentationStateOverride: presentation,
                      onGoTo: (_, {settingsCategory}) {},
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      const ids = [
        'dashboard-metric-CPU', 'dashboard-metric-GPU',
        'dashboard-metric-RAM', 'dashboard-metric-Disk',
        'dashboard-metric-System Health', 'dashboard-panel-Activity',
        'dashboard-panel-Model Usage', 'dashboard-panel-Storage',
        'dashboard-panel-Active Connections', 'dashboard-rail-Current Model',
        'dashboard-rail-Sandbox & permissions', 'dashboard-rail-Tools & Skills',
      ];
      return {for (final id in ids) id: tester.getRect(find.byKey(ValueKey(id)))};
    }

    final loading = await pumpCards(DashboardCardState.loading);
    final unavailable = await pumpCards(DashboardCardState.unavailable);
    // The live override intentionally exercises card geometry independent of
    // data arrival; data-specific rendering is covered by existing shell tests.
    final live = await pumpCards(DashboardCardState.live);
    expect(unavailable, loading);
    expect(live, loading);
  });

}

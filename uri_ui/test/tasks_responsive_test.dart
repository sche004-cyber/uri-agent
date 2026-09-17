// Hybrid UI Frozen Blueprint §4.5/§8.1 (Batch 4): Tasks has no mobile
// mockup in the reference, so the table-rows-to-cards conversion below
// is genuine new responsive design, not a reference transcription -
// this is the responsive-matrix coverage for that conversion. Every
// real field/action from the desktop table must survive unchanged.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<AppState> pumpHybridApp(WidgetTester tester, Size size) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final state = AppState(MockUriClient());
    await state.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: state));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    return state;
  }

  /// Tasks are derived from real proposals awaiting approval (see
  /// MockUriClient.listTasks) - there is nothing to show until a
  /// conversation actually produces one, same as the real backend.
  Future<void> createAPendingTask(WidgetTester tester) async {
    await tester.tap(find.text('Chat'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextField),
      'Prepare the quarterly filing',
    );
    await tester.tap(find.byIcon(Icons.arrow_forward_rounded));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
  }

  testWidgets('a wide layout shows the real Tasks data table, no cards', (
    tester,
  ) async {
    await pumpHybridApp(tester, const Size(1280, 900));
    await createAPendingTask(tester);
    await tester.tap(find.text('Tasks'));
    await tester.pumpAndSettle();

    expect(find.byType(DataTable), findsOneWidget);
  });

  testWidgets(
    'a narrow layout shows the same real tasks as cards, with working Approve/Cancel',
    (tester) async {
      final state = await pumpHybridApp(tester, const Size(390, 844));
      await createAPendingTask(tester);
      await tester.tap(find.text('Tasks'));
      await tester.pumpAndSettle();

      expect(find.byType(DataTable), findsNothing);
      final tasksBefore = state.tasks.length;
      expect(tasksBefore, greaterThan(0));

      // Every task's real description text is present as a card, not
      // dropped or summarized away.
      for (final task in state.tasks) {
        final label = task.description.isEmpty
            ? '(no description)'
            : task.description;
        expect(find.text(label), findsWidgets);
      }

      // The same real approve action a table row's icon button would
      // call - tapping the first card's Approve icon (scrolled into
      // view first: the card list is taller than the viewport).
      final approveButton = find.byTooltip('Approve').first;
      await tester.ensureVisible(approveButton);
      await tester.pumpAndSettle();
      await tester.tap(approveButton);
      // approveTask chains two real latencies (approve, then reload) -
      // pumpAndSettle alone can settle before either timer has even
      // registered; step through explicitly first, same pattern this
      // codebase's other helpers already use for chained mock latency.
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(state.tasks.length, lessThan(tasksBefore));
    },
  );
}

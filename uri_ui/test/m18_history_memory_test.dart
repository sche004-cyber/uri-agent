// M18 UI coverage: a URI-proposed (pending_confirmation) memory shows
// Confirm/Reject controls and confirming it flips its consent; past
// conversations list and resume load their turns into the conversation.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/memory_entry.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

/// A mock that starts with one URI-proposed (pending) memory and one
/// past conversation, so the M18 controls have something to act on.
class _M18Client extends MockUriClient {
  final List<MemoryEntry> _seededMemory = [
    const MemoryEntry(
      memoryId: 'mem-pending',
      category: 'preference',
      consent: 'pending_confirmation',
      content: 'prefers Times New Roman',
      confidence: null,
      notes: null,
      status: 'PROVISIONAL',
      createdAt: '',
      updatedAt: '',
    ),
  ];
  bool confirmed = false;

  @override
  Future<List<MemoryEntry>> listMemory() async => List.of(_seededMemory);

  @override
  Future<MemoryEntry?> confirmMemory(String memoryId, {String? content}) async {
    confirmed = true;
    return MemoryEntry(
      memoryId: memoryId,
      category: 'preference',
      consent: 'user_confirmed',
      content: content ?? 'prefers Times New Roman',
      confidence: null,
      notes: null,
      status: 'CONFIRMED',
      createdAt: '',
      updatedAt: '',
    );
  }

  @override
  Future<List<ConversationSummary>> listHistory() async => const [
        ConversationSummary(
          sessionId: 'past-1',
          turnCount: 2,
          preview: 'draft a note about the seminar',
        ),
      ];

  @override
  Future<List<UriTurn>> getHistory(String sessionId) async => [
        UriTurn(
          id: 'h1',
          userText: 'draft a note about the seminar',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          result: const ActionResult(summary: 'Here is the note.'),
        ),
      ];
}

Future<AppState> _pump(WidgetTester tester, _M18Client client) async {
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final appState = AppState(client: client);
  await appState.updatePreferences(
    const UserPreferences.initial().copyWith(completedOnboarding: true),
  );
  await tester.pumpWidget(UriApp(appState: appState));
  await tester.pumpAndSettle();
  return appState;
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('a URI-proposed memory shows Confirm/Reject and confirming works', (tester) async {
    final client = _M18Client();
    await _pump(tester, client);

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'Memory'));
    await tester.pumpAndSettle();

    expect(find.text('URI suggests remembering'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Confirm'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Reject'), findsOneWidget);

    await tester.tap(find.widgetWithText(ElevatedButton, 'Confirm'));
    await tester.pumpAndSettle();
    expect(client.confirmed, isTrue);
  });

  testWidgets('History lists past conversations and resume loads their turns', (tester) async {
    final client = _M18Client();
    final appState = await _pump(tester, client);

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, 'History'));
    await tester.pumpAndSettle();

    expect(find.text('draft a note about the seminar'), findsWidgets);
    expect(find.widgetWithText(TextButton, 'Resume'), findsOneWidget);

    await tester.tap(find.widgetWithText(TextButton, 'Resume'));
    await tester.pumpAndSettle();

    // The past turn was loaded into the live conversation, and the
    // client was repointed at that session.
    expect(appState.conversation.length, 1);
    expect(appState.conversation.first.userText, 'draft a note about the seminar');
    expect(client.sessionId, 'past-1');

    // Resuming navigates to Home, whose initState fires several mock
    // loads (each with a simulated latency Timer). Drain them so no
    // Timer outlives the disposed widget tree.
    await tester.pumpAndSettle(const Duration(seconds: 2));
  });
}

// Chat UX fix: a submitted message must render immediately and stay
// visible for the whole request lifecycle, with a persistent
// processing state directly beneath it (reusing TurnStage.understanding
// - an existing, previously-unused stage - rather than any new/fake
// progress step), until the same turn is updated in place with the
// real outcome. Also proves a successful conversational reply never
// renders the red failure icon, a genuine failure/capability gap still
// does, and the approval flow composes correctly with the new pending
// state.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/widgets/turn_card.dart';

/// A [MockUriClient] whose [ask] only resolves once [complete] is
/// called - lets a test observe the pending state deterministically
/// instead of racing a fixed latency timer.
class _ControllableUriClient extends MockUriClient {
  var _completer = Completer<UriTurn>();

  @override
  Future<UriTurn> ask(String text, {String? turnId}) {
    _completer = Completer<UriTurn>();
    return _completer.future;
  }

  void complete(UriTurn turn) => _completer.complete(turn);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('AppState.ask() lifecycle', () {
    late _ControllableUriClient client;
    late AppState state;

    setUp(() {
      client = _ControllableUriClient();
      state = AppState(client);
    });

    test(
      'the user\'s message is added immediately, before the request resolves',
      () async {
        final future = state.ask('hello URI');

        expect(state.conversation, hasLength(1));
        expect(state.conversation.single.userText, 'hello URI');
        expect(state.isSendingAsk, isTrue);

        client.complete(
          UriTurn(
            id: state.conversation.single.id,
            userText: 'hello URI',
            timestamp: DateTime.now(),
            stage: TurnStage.completed,
            result: const ActionResult(summary: 'Hello!'),
          ),
        );
        await future;
      },
    );

    test('the pending turn uses TurnStage.understanding (existing, no new stage invented)', () async {
      final future = state.ask('hello URI');

      expect(state.conversation.single.stage, TurnStage.understanding);

      client.complete(
        UriTurn(
          id: state.conversation.single.id,
          userText: 'hello URI',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          result: const ActionResult(summary: 'Hello!'),
        ),
      );
      await future;
    });

    test('a successful resolution updates the same turn in place, not a second entry', () async {
      final future = state.ask('hello URI');
      final pendingId = state.conversation.single.id;

      client.complete(
        UriTurn(
          id: pendingId,
          userText: 'hello URI',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          result: const ActionResult(summary: 'Hello! How can I help?'),
        ),
      );
      await future;

      expect(state.conversation, hasLength(1));
      expect(state.conversation.single.id, pendingId);
      expect(state.conversation.single.stage, TurnStage.completed);
      expect(state.conversation.single.userText, 'hello URI');
      expect(state.isSendingAsk, isFalse);
    });

    test(
      'a failure resolution updates the same turn in place with failed stage',
      () async {
        final future = state.ask('optimize my pc');
        final pendingId = state.conversation.single.id;

        client.complete(
          UriTurn(
            id: pendingId,
            userText: 'optimize my pc',
            timestamp: DateTime.now(),
            stage: TurnStage.failed,
            failureReason: 'URI does not have an implemented capability for this kind of task yet.',
          ),
        );
        await future;

        expect(state.conversation, hasLength(1));
        expect(state.conversation.single.stage, TurnStage.failed);
        expect(state.conversation.single.userText, 'optimize my pc');
        expect(
          state.conversation.single.failureReason,
          'URI does not have an implemented capability for this kind of task yet.',
        );
      },
    );

    test('an awaiting-approval resolution (a different, backend-issued id) still replaces the pending turn, never duplicates it', () async {
      final future = state.ask('draft an office note');
      final pendingId = state.conversation.single.id;

      client.complete(
        UriTurn(
          // A real backend action_id - deliberately NOT pendingId, the
          // exact shape HttpUriClient._turnFromResponse produces for
          // an awaiting-approval outcome.
          id: 'backend-action-id-123',
          userText: 'draft an office note',
          timestamp: DateTime.now(),
          stage: TurnStage.awaitingApproval,
          proposedAction: const ProposedAction(
            title: 'Draft institutional note',
            description: 'Needs your approval.',
            targetService: 'Institutional Drafting',
            impact: ActionImpact.notable,
          ),
        ),
      );
      await future;

      expect(state.conversation, hasLength(1));
      expect(state.conversation.single.id, 'backend-action-id-123');
      expect(state.conversation.single.id, isNot(pendingId));
      expect(state.conversation.single.stage, TurnStage.awaitingApproval);
    });
  });

  group('TurnCard rendering', () {
    Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

    testWidgets('a pending turn shows the processing state and no error icon', (
      tester,
    ) async {
      final turn = UriTurn(
        id: 't1',
        userText: 'hello URI',
        timestamp: DateTime.now(),
        stage: TurnStage.understanding,
      );

      await tester.pumpWidget(
        wrap(
          TurnCard(
            turn: turn,
            onApprove: () {},
            onCancel: () {},
            onConnectService: (_) {},
            onOpenAttachment: (_) {},
          ),
        ),
      );

      expect(find.text('hello URI'), findsOneWidget);
      expect(find.text('URI is working on this…'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byIcon(Icons.error_outline_rounded), findsNothing);
    });

    testWidgets(
      'a successful conversational reply never renders the failure icon',
      (tester) async {
        final turn = UriTurn(
          id: 't1',
          userText: 'hello URI',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          result: const ActionResult(
            summary:
                "Hello — I'm URI. Right now I can help with drafting institutional "
                'notes and orders, looking up student records, and reading '
                'spreadsheets. Let me know what you\'d like help with.',
          ),
        );

        await tester.pumpWidget(
          wrap(
            TurnCard(
              turn: turn,
              onApprove: () {},
              onCancel: () {},
              onConnectService: (_) {},
              onOpenAttachment: (_) {},
            ),
          ),
        );

        expect(find.byIcon(Icons.error_outline_rounded), findsNothing);
        expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
        expect(find.text('Failed'), findsNothing);
      },
    );

    testWidgets(
      'a genuine capability-gap failure still renders failure styling',
      (tester) async {
        final turn = UriTurn(
          id: 't1',
          userText: 'optimize my pc',
          timestamp: DateTime.now(),
          stage: TurnStage.failed,
          failureReason: 'URI does not have an implemented capability for this kind of task yet.',
        );

        await tester.pumpWidget(
          wrap(
            TurnCard(
              turn: turn,
              onApprove: () {},
              onCancel: () {},
              onConnectService: (_) {},
              onOpenAttachment: (_) {},
            ),
          ),
        );

        expect(find.byIcon(Icons.error_outline_rounded), findsOneWidget);
        expect(find.text('Failed'), findsOneWidget);
        expect(
          find.text(
            'URI does not have an implemented capability for this kind of task yet.',
          ),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'the processing state does not overflow a narrow Android phone width',
      (tester) async {
        // A common small-phone logical width (e.g. a compact Android
        // device) - the Row inside _ProcessingBlock must wrap its text
        // in Expanded rather than assuming desktop-width headroom.
        tester.view.physicalSize = const Size(360, 800);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        final turn = UriTurn(
          id: 't1',
          userText: 'hello URI, can you help me understand what you can actually do today',
          timestamp: DateTime.now(),
          stage: TurnStage.understanding,
        );

        await tester.pumpWidget(
          wrap(
            TurnCard(
              turn: turn,
              onApprove: () {},
              onCancel: () {},
              onConnectService: (_) {},
              onOpenAttachment: (_) {},
            ),
          ),
        );

        expect(tester.takeException(), isNull);
        expect(find.text('URI is working on this…'), findsOneWidget);
      },
    );
  });

  group('End-to-end through AskUriScreen (MockUriClient)', () {
    Future<AppState> pumpAskUriScreen(WidgetTester tester) async {
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

      // Not find.text('Ask URI') - Home's own submit button is also
      // labelled exactly "Ask URI" and would ambiguously match too.
      // The sidebar nav icon is unique to navigation.
      await tester.tap(find.byIcon(Icons.auto_awesome_outlined));
      await tester.pumpAndSettle();

      return appState;
    }

    testWidgets(
      'the message stays visible through pending, then settles to a real result',
      (tester) async {
        await pumpAskUriScreen(tester);

        await tester.enterText(
          find.byType(TextField),
          'What is on my calendar today',
        );
        await tester.tap(find.byIcon(Icons.arrow_upward_rounded));

        // One frame: the request is in flight (MockUriClient's fixed
        // latency has not elapsed yet) - the message and a processing
        // state must already be visible.
        await tester.pump();

        expect(find.text('What is on my calendar today'), findsOneWidget);
        expect(find.text('URI is working on this…'), findsOneWidget);

        // Flush the mock's latency.
        await tester.pump(const Duration(milliseconds: 500));

        // Still the same message, now with a real result and no
        // processing state left behind.
        expect(find.text('What is on my calendar today'), findsOneWidget);
        expect(find.text('URI is working on this…'), findsNothing);
        expect(find.text('Result'), findsOneWidget);
      },
    );

    testWidgets(
      'the message stays visible and the approval flow is unchanged',
      (tester) async {
        await pumpAskUriScreen(tester);

        await tester.enterText(
          find.byType(TextField),
          'Please draft a note about the insurance policy renewal',
        );
        await tester.tap(find.byIcon(Icons.arrow_upward_rounded));
        await tester.pump();

        expect(find.text('URI is working on this…'), findsOneWidget);

        await tester.pump(const Duration(milliseconds: 500));

        expect(
          find.text('Please draft a note about the insurance policy renewal'),
          findsOneWidget,
        );
        expect(find.text('Proposed action'), findsOneWidget);
        expect(find.text('Approve'), findsOneWidget);
        expect(find.text('Cancel'), findsOneWidget);

        await tester.tap(find.text('Approve'));
        await tester.pumpAndSettle();

        expect(
          find.text('Please draft a note about the insurance policy renewal'),
          findsOneWidget,
        );
        expect(find.text('Result'), findsOneWidget);
      },
    );
  });
}

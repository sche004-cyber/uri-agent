// Hybrid UI Frozen Blueprint §4.4/§5 (R2, proved again for Batch 4;
// re-proved again for the Live UX Repair's full-bleed Compact; corrected
// again below for the small-companion-window fix):
// Compact is a pure presentation-mode switch over the same AppState -
// never a new session, never a duplicate request, and the draft/
// transcript/attachments/model-override/in-flight-request state must
// survive every Compact <-> Workspace transition intact.
//
// Compact-window correction: the Live UX Repair (see
// docs/plans/UI_HYBRID_LIVE_UX_REPAIR_REPORT.md) made Compact fill the
// entire window as the active UI (Offstage, not IgnorePointer, keeps the
// Workspace shell mounted underneath) rather than floating a small
// fixed-size card over a dimmed Workspace - a deliberate, disclosed
// deviation from §4.4's original "420x580 floating window" text, made on
// the User's direct live-testing instruction. A later direct instruction
// reversed this again: Compact must be a genuinely small, fixed-size
// companion window. The Offstage/full-fill widget structure below is
// UNCHANGED and still correct - what changed is that `app.dart`'s
// [UriHome] now resizes the real OS window itself down to a small fixed
// size the moment Compact engages (see
// lib/services/platform_window_controller.dart), so "fills the window"
// now means filling a genuinely small window. `flutter test` has no
// native window_manager implementation, so the sizing/overlap/overflow/
// long-model-name tests below simulate the shrink by resizing
// `tester.view.physicalSize` after Compact engages, exactly mirroring
// the app's real order of operations (toggle first, native resize
// second) without needing a real platform channel.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/platform_window_controller.dart'
    show compactWindowSize;

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<AppState> pumpHybridApp(
    WidgetTester tester, {
    MockUriClient? client,
    Size size = const Size(1280, 900),
    CompactWindowModeFn? onCompactModeChanged,
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final state = AppState(client ?? MockUriClient());
    await state.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(
      UriApp(appState: state, onCompactModeChanged: onCompactModeChanged),
    );
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    return state;
  }

  /// Enters Compact at a normal (wide) window size - the toggle only
  /// renders in the wide desktop topbar - then simulates the real OS
  /// window shrinking to [size] as Compact's side effect.
  Future<void> enterCompactAtSize(WidgetTester tester, Size size) async {
    await tester.tap(find.byTooltip('Compact mode'));
    await tester.pumpAndSettle();
    tester.view.physicalSize = size;
    await tester.pumpAndSettle();
  }

  testWidgets(
    'Compact toggle fills the window as the active UI over an inert (offstage) Workspace shell, wide layout only',
    (tester) async {
      await pumpHybridApp(tester);

      expect(find.byTooltip('Expand to Workspace'), findsNothing);

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();

      // The overlay's own header is present.
      expect(find.byTooltip('Expand to Workspace'), findsOneWidget);
      // The Workspace shell stays mounted underneath (never rebuilt from
      // scratch) - its sidebar label is still in the tree, just offstage
      // (find.text skips offstage elements by default, so this needs
      // skipOffstage: false to actually prove it, rather than proving
      // nothing the way a plain find.text('Home') now would).
      expect(
        find.text('Home', skipOffstage: false),
        findsWidgets,
      );

      // The background shell is inert while Compact has focus: tapping
      // where "Tasks" renders must not navigate (Offstage, not merely
      // IgnorePointer, so skipOffstage: false is needed just to locate
      // it - Offstage already makes it untappable on its own).
      await tester.tap(
        find.text('Tasks', skipOffstage: false),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();
      expect(find.byTooltip('Expand to Workspace'), findsOneWidget);

      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pumpAndSettle();
      expect(find.byTooltip('Expand to Workspace'), findsNothing);
    },
  );

  testWidgets(
    'Compact is a Workspace-only presentation - no toggle on a narrow layout',
    (tester) async {
      await pumpHybridApp(tester, size: const Size(390, 844));
      expect(find.byTooltip('Compact mode'), findsNothing);
    },
  );

  testWidgets(
    'a draft typed in Compact survives Expand back to the Workspace composer',
    (tester) async {
      final state = await pumpHybridApp(tester);

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();

      const draftText = 'Draft written from the Compact window';
      await tester.enterText(find.byType(TextField), draftText);
      await tester.pump();
      expect(state.composerDraft, draftText);

      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.controller!.text, draftText);
      expect(state.composerDraft, draftText);
    },
  );

  testWidgets(
    'the same session/transcript renders in Compact - no new session, no duplicated turn',
    (tester) async {
      final state = await pumpHybridApp(tester);

      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      const prompt = 'Summarize the quarterly compliance report';
      await tester.enterText(find.byType(TextField), prompt);
      await tester.tap(find.byIcon(Icons.arrow_forward_rounded));
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      final sessionId = state.client.sessionId;
      final turnCountBeforeCompact = state.conversation.length;
      expect(turnCountBeforeCompact, greaterThan(0));

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();

      // Same transcript, not a fresh/empty one.
      expect(find.text(prompt), findsWidgets);
      expect(state.client.sessionId, sessionId);
      expect(state.conversation.length, turnCountBeforeCompact);

      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pumpAndSettle();

      expect(state.client.sessionId, sessionId);
      expect(state.conversation.length, turnCountBeforeCompact);
    },
  );

  testWidgets(
    'toggling Compact while a request is in flight never duplicates the turn once it resolves',
    (tester) async {
      final state = await pumpHybridApp(tester);

      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      const prompt = 'Draft a note for the operations team';
      await tester.enterText(find.byType(TextField), prompt);
      await tester.tap(find.byIcon(Icons.arrow_forward_rounded));
      // One frame only - the mock's simulated latency has not resolved
      // yet, so the request is still in flight.
      await tester.pump();
      expect(state.isSendingAsk, isTrue);

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pump();

      // Now let the in-flight request resolve.
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(state.isSendingAsk, isFalse);
      final userTurns = state.conversation
          .where((turn) => turn.userText == prompt)
          .length;
      expect(userTurns, 1, reason: 'switching modes mid-request must not resend/duplicate the turn');
    },
  );

  test(
    'the companion window target is within the required 420-480 x 600-720 range',
    () {
      expect(compactWindowSize.width, inInclusiveRange(420, 480));
      expect(compactWindowSize.height, inInclusiveRange(600, 720));
    },
  );

  testWidgets(
    'entering and expanding Compact calls the native-window hook exactly once each way',
    (tester) async {
      final calls = <bool>[];
      await pumpHybridApp(
        tester,
        onCompactModeChanged: (isCompact) async {
          calls.add(isCompact);
        },
      );

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();
      expect(calls, [true]);

      // Unrelated state changes (a keystroke) must not re-trigger it.
      await tester.enterText(find.byType(TextField), 'hi');
      await tester.pump();
      expect(calls, [true]);

      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pumpAndSettle();
      expect(calls, [true, false]);
    },
  );

  for (final size in [const Size(420, 600), const Size(440, 680), const Size(480, 720)]) {
    testWidgets(
      'no overflow/overlap at the companion window bound ${size.width.toInt()}x${size.height.toInt()}, with a long draft and a long model name',
      (tester) async {
        final state = await pumpHybridApp(tester);
        await tester.tap(find.text('Chat'));
        await tester.pumpAndSettle();

        state.setConversationModelOverride({
          'provider_id': 'ollama',
          'model': 'a-very-long-locally-installed-model-name-7b-instruct-q4',
        });
        await tester.enterText(
          find.byType(TextField),
          'Line one of a long draft\nLine two\nLine three\nLine four\nLine five near the compact composer max lines cap',
        );
        await tester.pump();

        await enterCompactAtSize(tester, size);

        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'a long model name in the Compact composer ellipsizes instead of overlapping neighboring controls',
    (tester) async {
      final state = await pumpHybridApp(tester);
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      const longModel =
          'a-very-long-locally-installed-model-name-7b-instruct-q4';
      state.setConversationModelOverride({
        'provider_id': 'ollama',
        'model': longModel,
      });
      await tester.pump();

      await enterCompactAtSize(tester, const Size(440, 680));

      final label = tester.widget<Text>(find.text(longModel));
      expect(label.overflow, TextOverflow.ellipsis);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'the conversation scrolls inside the Compact window instead of overflowing it',
    (tester) async {
      final state = await pumpHybridApp(tester);
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      for (var i = 0; i < 20; i++) {
        await tester.enterText(
          find.byType(TextField),
          'Message number $i asking URI something long enough to take real vertical space in the transcript.',
        );
        await tester.tap(find.byIcon(Icons.arrow_forward_rounded));
        await tester.pump(const Duration(seconds: 1));
        await tester.pumpAndSettle();
      }
      expect(state.conversation.length, greaterThan(10));

      await enterCompactAtSize(tester, compactWindowSize);
      expect(tester.takeException(), isNull);

      // The transcript auto-scrolls to the latest turn (maxScrollExtent)
      // after every update, so scrolling further requires dragging back
      // *up* from the bottom, not down.
      final scrollable = find.byType(Scrollable).first;
      final before = tester.state<ScrollableState>(scrollable).position.pixels;
      expect(before, greaterThan(0), reason: 'transcript should already be scrolled past the top');
      await tester.drag(scrollable, const Offset(0, 400));
      await tester.pumpAndSettle();
      final after = tester.state<ScrollableState>(scrollable).position.pixels;
      expect(
        after,
        isNot(equals(before)),
        reason: 'the transcript must be scrollable inside the small Compact window',
      );
    },
  );

  testWidgets(
    'the selected conversation model survives Compact <-> Workspace, same as the draft/session',
    (tester) async {
      final state = await pumpHybridApp(tester);
      await tester.tap(find.text('Chat'));
      await tester.pumpAndSettle();

      state.setConversationModelOverride({
        'provider_id': 'ollama',
        'model': 'llama-3.1-8b',
      });
      await tester.pump();

      await tester.tap(find.byTooltip('Compact mode'));
      await tester.pumpAndSettle();
      expect(state.conversationModelOverride, {
        'provider_id': 'ollama',
        'model': 'llama-3.1-8b',
      });

      await tester.tap(find.byTooltip('Expand to Workspace'));
      await tester.pumpAndSettle();
      expect(state.conversationModelOverride, {
        'provider_id': 'ollama',
        'model': 'llama-3.1-8b',
      });
    },
  );
}

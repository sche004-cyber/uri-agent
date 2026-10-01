// Focused widget test for the Issue-3 TurnCard fix: a failed turn
// with no understanding text (the exact shape produced when the
// model backend itself is unreachable - see
// http_uri_client_test.dart's "network error" case) must still show
// *something* explaining what went wrong, not just a bare red
// "Failed" pill.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uri_ui/models/attachment.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/widgets/turn_card.dart';

void main() {
  Widget wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

  testWidgets(
    'a failed turn with no understanding text still shows the failure reason',
    (tester) async {
      final turn = UriTurn(
        id: 't1',
        userText: 'draft a note',
        timestamp: DateTime.now(),
        stage: TurnStage.failed,
        // Deliberately null - reproduces the exact scenario that
        // previously rendered nothing at all (e.g. the semantic
        // interpreter itself never returned, so no narrative and no
        // "Understood as: ..." text was ever built).
        understanding: null,
        failureReason: 'Could not reach Ollama. Is it running?',
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

      expect(
        find.text('Could not reach Ollama. Is it running?'),
        findsOneWidget,
      );
      expect(find.text('Failed'), findsOneWidget);
    },
  );

  testWidgets(
    'a failed turn with both understanding and failureReason shows both',
    (tester) async {
      final turn = UriTurn(
        id: 't1',
        userText: 'draft a note',
        timestamp: DateTime.now(),
        stage: TurnStage.failed,
        understanding: 'I looked into this but ran into a problem.',
        failureReason: 'No drafted output was available for review.',
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

      expect(
        find.text('I looked into this but ran into a problem.'),
        findsOneWidget,
      );
      expect(
        find.text('No drafted output was available for review.'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'a non-failed turn never shows failure styling even if failureReason were set',
    (tester) async {
      final turn = UriTurn(
        id: 't1',
        userText: 'draft a note',
        timestamp: DateTime.now(),
        stage: TurnStage.completed,
        result: const ActionResult(summary: 'Done.'),
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
    },
  );

  testWidgets(
    'a result with a generated file shows a tappable chip that opens it',
    (tester) async {
      var openedFileId = '';
      final turn = UriTurn(
        id: 't1',
        userText: 'write a project proposal',
        timestamp: DateTime.now(),
        stage: TurnStage.completed,
        result: const ActionResult(
          summary: 'Here is the proposal.',
          generatedFile: Attachment(
            fileId: 'file-123',
            filename: 'proposal.docx',
            mediaType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            sizeBytes: 20480,
          ),
        ),
      );

      await tester.pumpWidget(
        wrap(
          TurnCard(
            turn: turn,
            onApprove: () {},
            onCancel: () {},
            onConnectService: (_) {},
            onOpenAttachment: (attachment) => openedFileId = attachment.fileId,
          ),
        ),
      );

      expect(find.textContaining('proposal.docx'), findsOneWidget);

      await tester.tap(find.byType(ActionChip));
      await tester.pump();

      expect(openedFileId, 'file-123');
    },
  );

  testWidgets(
    'a turn with recoveryRequired and arnState renders ARN recovery card',
    (tester) async {
      final turn = UriTurn(
        id: 't-arn',
        userText: 'find the contract for Acme',
        timestamp: DateTime.now(),
        stage: TurnStage.completed,
        recoveryRequired: true,
        arnState: const {
          'active_candidates': ['Acme-2024.pdf', 'Acme-2025.pdf'],
          'eliminated_candidates': ['Acme-Archive.docx'],
          'searched_sources': ['local_docs', 'gmail'],
          'clarification_recommendation': {
            'question': 'Which year contract are you looking for?',
          },
        },
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

      expect(
        find.text('Adaptive Retrieval Narrowing (ARN)'),
        findsOneWidget,
      );
      expect(
        find.text('2 active · 1 eliminated'),
        findsOneWidget,
      );

      // Tap to expand
      await tester.tap(find.text('Adaptive Retrieval Narrowing (ARN)'));
      await tester.pump();

      expect(
        find.text('Sources Searched: local_docs, gmail'),
        findsOneWidget,
      );
      expect(
        find.text('Suggested Clarification: Which year contract are you looking for?'),
        findsOneWidget,
      );
    },
  );

  for (final (width, name) in [
    (360.0, '360px mobile width'),
    (390.0, '390px mobile width'),
    (1024.0, 'normal desktop width'),
  ]) {
    testWidgets(
      'ARN recovery card renders cleanly without overflow at $name',
      (tester) async {
        tester.view.physicalSize = Size(width, 700);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final turn = UriTurn(
          id: 't-arn-resp-$width',
          userText: 'find the contract for Acme',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          recoveryRequired: true,
          arnState: const {
            'active_candidates': ['Acme-2024.pdf', 'Acme-2025.pdf'],
            'eliminated_candidates': ['Acme-Archive.docx'],
            'searched_sources': ['local_docs', 'gmail'],
            'clarification_recommendation': {
              'question': 'Which year contract are you looking for?',
            },
          },
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
        expect(find.text('Adaptive Retrieval Narrowing (ARN)'), findsOneWidget);
        expect(find.text('2 active · 1 eliminated'), findsOneWidget);

        // Tap to expand and verify no overflow when expanded
        await tester.tap(find.text('Adaptive Retrieval Narrowing (ARN)'));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.text('Sources Searched: local_docs, gmail'), findsOneWidget);
      },
    );

    testWidgets(
      'ARN recovery card with long candidate content renders cleanly without overflow at $name',
      (tester) async {
        tester.view.physicalSize = Size(width, 700);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        // Generate long candidate lists to test realistic long counters
        final activeCandidates = List.generate(42, (i) => 'Acme-Contract-Spec-Revision-202$i-Final-V$i.pdf');
        final eliminatedCandidates = List.generate(35, (i) => 'Acme-Legacy-Archive-Draft-$i.docx');

        final turn = UriTurn(
          id: 't-arn-long-$width',
          userText: 'find every contract matching Acme across all repositories',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          recoveryRequired: true,
          arnState: {
            'active_candidates': activeCandidates,
            'eliminated_candidates': eliminatedCandidates,
            'searched_sources': ['local_docs', 'gmail', 'gdrive', 'slack', 'notion_archive'],
            'clarification_recommendation': {
              'question': 'Are you seeking current active agreements or historical legacy revisions?',
            },
          },
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
        expect(find.text('Adaptive Retrieval Narrowing (ARN)'), findsOneWidget);
        expect(find.text('42 active · 35 eliminated'), findsOneWidget);

        // Tap to expand and verify no overflow
        await tester.tap(find.text('Adaptive Retrieval Narrowing (ARN)'));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.textContaining('local_docs, gmail'), findsOneWidget);
      },
    );

    testWidgets(
      'TurnCard displays end-to-end total duration alongside model duration',
      (tester) async {
        final turn = UriTurn(
          id: 't-latency',
          userText: 'hello',
          timestamp: DateTime.now(),
          stage: TurnStage.completed,
          understanding: 'Greeting',
          durationSeconds: 1.2,
          totalDurationSeconds: 1.5,
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

        expect(find.textContaining('1.5s total (1.2s model)'), findsOneWidget);
      },
    );
  }
}


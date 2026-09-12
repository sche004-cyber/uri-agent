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
}

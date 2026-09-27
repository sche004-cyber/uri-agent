// M33.3-R S12: fixture-backed clarification card. Fixtures are exported from
// real frozen S1 contracts by scripts/m33_3_r_s12_export_fixtures.py and carry
// the exact payload each action must emit.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uri_ui/models/clarification.dart';
import 'package:uri_ui/widgets/clarification_card.dart';

void main() {
  final doc = jsonDecode(
    File('test/fixtures/m33_3_s12_clarification_cards.json').readAsStringSync(),
  ) as Map<String, dynamic>;
  final cards = (doc['cards'] as List).cast<Map<String, dynamic>>();

  Widget wrap(Widget child) =>
      MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));

  Future<List<Map<String, dynamic>>> pump(
    WidgetTester tester,
    Map<String, dynamic> card,
  ) async {
    final emitted = <Map<String, dynamic>>[];
    await tester.pumpWidget(wrap(ClarificationCard(
      request: ClarificationRequest.fromJson(card),
      onRespond: (p) => emitted.add(p.toJson()),
    )));
    return emitted;
  }

  test('fixture is fixture-only and every card parses', () {
    expect(doc['fixture_only'], isTrue);
    for (final card in cards) {
      ClarificationRequest.fromJson(card);
    }
  });

  for (final card in cards) {
    final caseId = card['case_id'];
    final expected = (card['expected_payloads'] as Map).cast<String, dynamic>();

    testWidgets('$caseId: shows exactly the grounded options, no padding', (tester) async {
      await pump(tester, card);
      expect(find.text(card['question'] as String), findsOneWidget);
      final options = (card['options'] as List).cast<Map<String, dynamic>>();
      final filters = (card['attribute_filters'] as List).cast<Map<String, dynamic>>();
      expect(find.byWidgetPredicate((w) =>
          w.key is ValueKey<String> &&
          (w.key as ValueKey<String>).value.startsWith('clarification-option-')),
          findsNWidgets(options.length));
      expect(find.byWidgetPredicate((w) =>
          w.key is ValueKey<String> &&
          (w.key as ValueKey<String>).value.startsWith('clarification-filter-')),
          findsNWidgets(filters.length));
      expect(options.length, lessThanOrEqualTo(5));
      if (card['kind'] == 'FREE_INPUT_ONLY') {
        expect(find.byKey(const Key('clarification-free-input')), findsOneWidget);
      } else {
        expect(find.text(card['escape_label'] as String), findsOneWidget);
      }
    });

    for (final entry in expected.entries) {
      testWidgets('$caseId: ${entry.key} emits the grounded payload, not the label',
          (tester) async {
        final emitted = await pump(tester, card);
        final key = entry.key.startsWith('a')
            ? Key('clarification-filter-${entry.key}')
            : Key('clarification-option-${entry.key}');
        await tester.tap(find.byKey(key));
        await tester.pump();
        expect(emitted, [entry.value]);
        final labels = [
          ...(card['options'] as List).map((o) => o['label']),
          ...(card['attribute_filters'] as List).map((f) => f['label']),
        ];
        expect(labels.contains(emitted.single['candidate_id']), isFalse);
        // One answer per round: the card locks.
        expect(find.byKey(const Key('clarification-answered')), findsOneWidget);
        expect(find.byKey(key), findsNothing);
      });
    }

    testWidgets('$caseId: free input is authoritative and emitted verbatim', (tester) async {
      final emitted = await pump(tester, card);
      if (card['kind'] != 'FREE_INPUT_ONLY') {
        expect(find.byKey(const Key('clarification-free-input')), findsNothing);
        await tester.tap(find.byKey(const Key('clarification-escape')));
        await tester.pump();
      }
      await tester.tap(find.byKey(const Key('clarification-free-input-submit')));
      await tester.pump();
      expect(emitted, isEmpty); // empty text is not an answer
      await tester.enterText(find.byKey(const Key('clarification-free-input')), '  the March one  ');
      await tester.tap(find.byKey(const Key('clarification-free-input-submit')));
      await tester.pump();
      final payload = Map<String, dynamic>.from(card['expected_free_input_payload'] as Map)
        ..['text'] = 'the March one';
      expect(emitted, [payload]);
      expect(find.text('Using: the March one'), findsOneWidget);
    });
  }

  test('malformed or padded cards fail closed', () {
    final base = Map<String, dynamic>.from(cards.first);
    Map<String, dynamic> withOptions(List<Map<String, dynamic>> options) =>
        Map<String, dynamic>.from(base)..['options'] = options;
    final six = List.generate(6, (i) =>
        {'option_key': 's${i + 1}', 'candidate_id': 'c$i', 'label': 'L$i', 'rank': i + 1});
    expect(() => ClarificationRequest.fromJson(withOptions(six)), throwsFormatException);
    expect(() => ClarificationRequest.fromJson(withOptions([
          {'option_key': 's1', 'candidate_id': '', 'label': 'x', 'rank': 1}
        ])), throwsFormatException);
    expect(() => ClarificationRequest.fromJson(withOptions([
          {'option_key': 'a1', 'candidate_id': 'c', 'label': 'x', 'rank': 1}
        ])), throwsFormatException);
    expect(() => ClarificationRequest.fromJson(Map<String, dynamic>.from(base)..['kind'] = 'FREE_INPUT_ONLY'),
        throwsFormatException);
  });
}

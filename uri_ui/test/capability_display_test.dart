import 'package:flutter_test/flutter_test.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/utils/capability_display.dart';

void main() {
  group('humanizeIdentifier', () {
    test('converts snake_case to Title Case with spaces', () {
      expect(
        humanizeIdentifier('draft_institutional_note'),
        'Draft Institutional Note',
      );
    });

    test('handles a single-word identifier', () {
      expect(humanizeIdentifier('optimize'), 'Optimize');
    });

    test('handles an empty string without crashing', () {
      expect(humanizeIdentifier(''), '');
    });

    test('collapses accidental double underscores', () {
      expect(humanizeIdentifier('draft__note'), 'Draft Note');
    });
  });

  group('impactFromRisk', () {
    test(
      'never returns routine - approval-gated proposals never look routine',
      () {
        for (final risk in [
          'controlled',
          'low',
          'variable',
          'high',
          'unknown',
          null,
          'garbage',
        ]) {
          expect(impactFromRisk(risk), isNot(ActionImpact.routine));
        }
      },
    );

    test('controlled and low map to notable', () {
      expect(impactFromRisk('controlled'), ActionImpact.notable);
      expect(impactFromRisk('low'), ActionImpact.notable);
    });

    test('variable maps to notable', () {
      expect(impactFromRisk('variable'), ActionImpact.notable);
    });

    test('high maps to sensitive', () {
      expect(impactFromRisk('high'), ActionImpact.sensitive);
    });

    test('unknown or missing risk defaults to sensitive, not routine', () {
      expect(impactFromRisk('unknown'), ActionImpact.sensitive);
      expect(impactFromRisk(null), ActionImpact.sensitive);
    });
  });
}

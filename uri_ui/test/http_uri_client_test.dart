// Directly unit-tests HttpUriClient's real request/response mapping
// logic against a fake http.Client (package:http/testing.dart) - no
// real network, no real backend. This is deliberately new: every
// other existing widget test in this suite builds AppState against
// MockUriClient, so HttpUriClient's own mapping logic (in particular
// _turnFromResponse's awaiting_approval branch and _decide's summary
// extraction) was never exercised by anything automated - exactly how
// the raw-JSON-dump and raw-snake_case-title bugs (Issues 3/4) shipped
// unnoticed. This file closes that gap.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:uri_ui/models/uri_turn.dart';
import 'package:uri_ui/services/http_uri_client.dart';

http.Response _json(Map<String, dynamic> body, {int statusCode = 200}) {
  return http.Response(jsonEncode(body), statusCode);
}

void main() {
  group('ask()', () {
    test('a successful direct execution with narrative uses the narrative as the result summary', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'status': 'success',
            'session_id': 's1',
            'semantic_analysis': {'goal': 'draft a note'},
            'execution': {'status': 'success', 'tool': 'draft_institutional_note'},
            'response': {'status': 'success', 'note_sheet': 'RAW DOCUMENT TEXT'},
            'narrative': "I've drafted the note for your review.",
          });
        }),
      );

      final turn = await client.ask('draft a note');

      expect(turn.stage, TurnStage.completed);
      expect(turn.result!.summary, "I've drafted the note for your review.");
      // The raw tool output must never leak into the summary text.
      expect(turn.result!.summary, isNot(contains('RAW DOCUMENT TEXT')));
    });

    test('a successful execution with no narrative and no message never dumps raw JSON', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'status': 'success',
            'session_id': 's1',
            'semantic_analysis': {'goal': 'draft a note'},
            'execution': {'status': 'success', 'tool': 'draft_institutional_note'},
            'response': {'status': 'success', 'note_sheet': 'RAW DOCUMENT TEXT'},
            'narrative': null,
          });
        }),
      );

      final turn = await client.ask('draft a note');

      expect(turn.stage, TurnStage.completed);
      expect(turn.result!.summary, isNot(contains('{')));
      expect(turn.result!.summary, isNot(contains('RAW DOCUMENT TEXT')));
    });

    test(
      'M15 correction: a successful execution with no narrative but a real, '
      'readable tool result relays that result rather than a content-free '
      'confirmation',
      () async {
        const realNoteSheet =
            'NOTING\n\nSubject: New library hours\n\n'
            'The matter is submitted for kind consideration.';

        final client = HttpUriClient(
          httpClient: MockClient((request) async {
            return _json({
              'status': 'success',
              'session_id': 's1',
              'semantic_analysis': {'goal': 'draft a note'},
              'execution': {'status': 'success', 'tool': 'draft_institutional_note'},
              'response': {'status': 'success', 'note_sheet': realNoteSheet},
              'narrative': null,
            });
          }),
        );

        final turn = await client.ask('draft a note');

        expect(turn.stage, TurnStage.completed);
        // The real, already-produced result must reach the user - a
        // transient drafting failure must never silently discard it.
        expect(turn.result!.summary, realNoteSheet);
      },
    );

    test('awaiting_approval uses a humanized title and the registry description', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'status': 'success',
            'session_id': 's1',
            'semantic_analysis': {'goal': 'draft a note'},
            'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
            'response': {
              'status': 'awaiting_approval',
              'action_id': '11111111-1111-1111-1111-111111111111',
              'tool_name': 'draft_institutional_note',
              'risk': 'controlled',
              'description': 'Draft a concise administrative office noting.',
              'message': 'This action requires your explicit approval before URI can proceed.',
            },
            'narrative': null,
          });
        }),
      );

      final turn = await client.ask('draft a note');

      expect(turn.stage, TurnStage.awaitingApproval);
      expect(turn.id, '11111111-1111-1111-1111-111111111111');
      expect(turn.proposedAction!.title, 'Draft Institutional Note');
      expect(turn.proposedAction!.description, 'Draft a concise administrative office noting.');
      // "controlled" risk must never render as routine for a gated proposal.
      expect(turn.proposedAction!.impact, isNot(ActionImpact.routine));
    });

    test('awaiting_approval without a registry description falls back to the generic message', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'status': 'success',
            'session_id': 's1',
            'semantic_analysis': {},
            'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
            'response': {
              'status': 'awaiting_approval',
              'action_id': 'a1',
              'tool_name': 'draft_institutional_note',
              'risk': 'controlled',
              'description': null,
              'message': 'This action requires your explicit approval before URI can proceed.',
            },
          });
        }),
      );

      final turn = await client.ask('draft a note');

      expect(
        turn.proposedAction!.description,
        'This action requires your explicit approval before URI can proceed.',
      );
    });

    test('a failed outcome sets failureReason from execution.error', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'status': 'success',
            'session_id': 's1',
            'semantic_analysis': {},
            'execution': {'status': 'failed', 'error': 'No drafted output was available for review.'},
            'response': {'message': 'URI could not complete the planned workflow.'},
          });
        }),
      );

      final turn = await client.ask('do something ambiguous');

      expect(turn.stage, TurnStage.failed);
      expect(turn.failureReason, 'No drafted output was available for review.');
    });

    test('a request-level failure (status != success) sets failureReason', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({'status': 'failed', 'error': 'simulated backend error'});
        }),
      );

      final turn = await client.ask('anything');

      expect(turn.stage, TurnStage.failed);
      expect(turn.failureReason, 'simulated backend error');
    });

    test('a network error sets a clear failureReason rather than throwing', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          throw Exception('connection refused');
        }),
      );

      final turn = await client.ask('anything');

      expect(turn.stage, TurnStage.failed);
      expect(turn.failureReason, contains('Could not reach the URI backend'));
    });
  });

  group('approve()/cancel() via _decide', () {
    test('approve prefers the narrative over raw tool JSON', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          if (request.url.path == '/ask') {
            return _json({
              'status': 'success',
              'session_id': 's1',
              'semantic_analysis': {},
              'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
              'response': {
                'status': 'awaiting_approval',
                'action_id': 'action-1',
                'tool_name': 'draft_institutional_note',
                'risk': 'controlled',
                'message': 'needs approval',
              },
            });
          }
          return _json({
            'status': 'success',
            'data': {'status': 'success', 'note_sheet': 'RAW DOCUMENT TEXT'},
            'narrative': "I've completed the note as requested.",
          });
        }),
      );

      await client.ask('draft a note');
      final approved = await client.approve('action-1');

      expect(approved.stage, TurnStage.completed);
      expect(approved.result!.summary, "I've completed the note as requested.");
      expect(approved.result!.summary, isNot(contains('RAW DOCUMENT TEXT')));
    });

    test('approve without a narrative never dumps raw JSON', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          if (request.url.path == '/ask') {
            return _json({
              'status': 'success',
              'session_id': 's1',
              'semantic_analysis': {},
              'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
              'response': {
                'status': 'awaiting_approval',
                'action_id': 'action-1',
                'tool_name': 'draft_institutional_note',
                'risk': 'controlled',
                'message': 'needs approval',
              },
            });
          }
          return _json({
            'status': 'success',
            'data': {'status': 'success', 'note_sheet': 'RAW DOCUMENT TEXT'},
            'narrative': null,
          });
        }),
      );

      await client.ask('draft a note');
      final approved = await client.approve('action-1');

      expect(approved.result!.summary, isNot(contains('{')));
      expect(approved.result!.summary, isNot(contains('RAW DOCUMENT TEXT')));
    });

    test(
      'M15 correction: approve without a narrative but a real, readable '
      'tool result relays that result rather than a content-free '
      'confirmation',
      () async {
        const noteSheet =
            'NOTING\n\nSubject: New library hours\n\n'
            'The matter is submitted for kind consideration.';
        final client = HttpUriClient(
          httpClient: MockClient((request) async {
            if (request.url.path == '/ask') {
              return _json({
                'status': 'success',
                'session_id': 's1',
                'semantic_analysis': {},
                'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
                'response': {
                  'status': 'awaiting_approval',
                  'action_id': 'action-1',
                  'tool_name': 'draft_institutional_note',
                  'risk': 'controlled',
                  'message': 'needs approval',
                },
              });
            }
            return _json({
              'status': 'success',
              'data': {'status': 'success', 'note_sheet': noteSheet},
              'narrative': null,
            });
          }),
        );

        await client.ask('draft a note');
        final approved = await client.approve('action-1');

        expect(approved.result!.summary, contains('New library hours'));
      },
    );

    test('cancel reports no action was taken', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          if (request.url.path == '/ask') {
            return _json({
              'status': 'success',
              'session_id': 's1',
              'semantic_analysis': {},
              'execution': {'status': 'awaiting_approval', 'tool': 'draft_institutional_note'},
              'response': {
                'status': 'awaiting_approval',
                'action_id': 'action-1',
                'tool_name': 'draft_institutional_note',
                'risk': 'controlled',
                'message': 'needs approval',
              },
            });
          }
          return _json({'status': 'cancelled', 'action_id': 'action-1', 'narrative': null});
        }),
      );

      await client.ask('draft a note');
      final cancelled = await client.cancel('action-1');

      expect(cancelled.stage, TurnStage.cancelled);
      expect(cancelled.result!.summary, 'No action was taken.');
    });

    test('an error response sets failureReason, not a crash', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({'status': 'error', 'message': 'Action not-found is not pending.'});
        }),
      );

      final result = await client.approve('not-found');

      expect(result.stage, TurnStage.failed);
      expect(result.failureReason, 'Action not-found is not pending.');
    });
  });

  group('listTasks()', () {
    test('maps backend tasks into TaskItem objects', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          return _json({
            'tasks': [
              {
                'action_id': 'a1',
                'capability_id': 'pc_system_optimization',
                'description': "Optimize this device's performance.",
                'risk': 'high',
                'session_id': 's1',
                'created_at': '2026-01-01T00:00:00+00:00',
              },
            ],
          });
        }),
      );

      final tasks = await client.listTasks();

      expect(tasks, hasLength(1));
      expect(tasks.first.capabilityId, 'pc_system_optimization');
      expect(tasks.first.risk, 'high');
    });

    test('a network error returns an empty list rather than throwing', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          throw Exception('connection refused');
        }),
      );

      final tasks = await client.listTasks();

      expect(tasks, isEmpty);
    });
  });
}

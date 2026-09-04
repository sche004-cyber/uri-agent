import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/uri_turn.dart';
import 'mock_uri_client.dart';
import 'uri_client.dart';

/// Real HTTP implementation of [UriClient].
///
/// [ask] is the only method backed by a real network call — it POSTs to
/// the FastAPI boundary in `uri_core/app/server.py`, which calls
/// `UriOrchestrator.process_user_input()` unmodified and returns its
/// result as JSON.
///
/// UriOrchestrator does not expose anything for connections, activity
/// history, the home summary, or a separate approve/cancel step (its
/// deterministic paths execute immediately once a capability or
/// workflow is selected — there is no server-side "awaiting approval"
/// gate to call back into). Until that backend surface exists, those
/// methods delegate to [MockUriClient] so the rest of the UI keeps
/// working. This is intentionally visible here rather than hidden:
/// see the class doc on [UriClient] for the boundary this respects.
class HttpUriClient implements UriClient {
  HttpUriClient({
    this.baseUrl = 'http://localhost:8000',
    String? sessionId,
    http.Client? httpClient,
    UriClient? fallback,
  }) : _sessionId = sessionId ?? _generateSessionId(),
       _http = httpClient ?? http.Client(),
       _fallback = fallback ?? MockUriClient();

  final String baseUrl;
  final String _sessionId;
  final http.Client _http;
  final UriClient _fallback;

  static String _generateSessionId() =>
      'flutter-${DateTime.now().microsecondsSinceEpoch}';

  @override
  Future<UriTurn> ask(String text) async {
    final id = 'turn-${DateTime.now().microsecondsSinceEpoch}';
    final timestamp = DateTime.now();

    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl/ask'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({'session_id': _sessionId, 'text': text}),
          )
          .timeout(const Duration(seconds: 30));
    } catch (error) {
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        failureReason: 'Could not reach the URI backend: $error',
      );
    }

    if (response.statusCode != 200) {
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        failureReason: 'URI backend returned HTTP ${response.statusCode}.',
      );
    }

    final Map<String, dynamic> body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (error) {
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        failureReason: 'URI backend returned a response that could not be parsed.',
      );
    }

    return _turnFromResponse(id: id, text: text, timestamp: timestamp, body: body);
  }

  UriTurn _turnFromResponse({
    required String id,
    required String text,
    required DateTime timestamp,
    required Map<String, dynamic> body,
  }) {
    if (body['status'] != 'success') {
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        failureReason: body['error'] as String? ?? 'URI could not process this request.',
      );
    }

    final semantic = body['semantic_analysis'] as Map<String, dynamic>?;
    final execution = body['execution'] as Map<String, dynamic>?;
    final responseData = body['response'];

    final understanding = semantic != null && semantic['goal'] != null
        ? 'Understood as: ${semantic['goal']}'
        : 'URI processed this request.';

    if (execution != null && execution['status'] == 'failed') {
      final reason = execution['error'] ?? execution['reason'];
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        understanding: understanding,
        failureReason: reason?.toString() ?? 'Execution failed.',
      );
    }

    final String summary;
    if (responseData is Map && responseData['message'] != null) {
      summary = responseData['message'].toString();
    } else if (responseData != null) {
      summary = jsonEncode(responseData);
    } else {
      summary = 'URI finished processing this request.';
    }

    return UriTurn(
      id: id,
      userText: text,
      timestamp: timestamp,
      stage: TurnStage.completed,
      understanding: understanding,
      result: ActionResult(
        summary: summary,
        detail: execution != null ? 'Tool: ${execution['tool'] ?? execution['status']}' : null,
      ),
    );
  }

  // ---------------------------------------------------------------
  // No real backend surface exists for these yet — see class doc.
  // ---------------------------------------------------------------

  @override
  Future<UriTurn> approve(String turnId) => _fallback.approve(turnId);

  @override
  Future<UriTurn> cancel(String turnId) => _fallback.cancel(turnId);

  @override
  Future<List<ServiceConnection>> listConnections() => _fallback.listConnections();

  @override
  Future<ServiceConnection> authorizeConnection(String connectionId) =>
      _fallback.authorizeConnection(connectionId);

  @override
  Future<ServiceConnection> disconnectConnection(String connectionId) =>
      _fallback.disconnectConnection(connectionId);

  @override
  Future<List<ActivityEvent>> listActivity() => _fallback.listActivity();

  @override
  Future<HomeSummary> loadHomeSummary() => _fallback.loadHomeSummary();
}

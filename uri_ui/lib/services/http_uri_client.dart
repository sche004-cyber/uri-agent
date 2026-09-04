import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/uri_turn.dart';
import '../utils/capability_display.dart';
import 'mock_uri_client.dart';
import 'uri_client.dart';

/// Real HTTP implementation of [UriClient].
///
/// [ask], [approve], [cancel], and [listTasks] are all backed by real
/// network calls to the FastAPI boundary in `uri_core/app/server.py`
/// (POST /ask, POST /approve, POST /cancel, GET /tasks) — the backend
/// now has a real deterministic approval gate (see approval_gate.py)
/// and a real cross-session pending-actions store to read from, so
/// these no longer need [MockUriClient] as a stand-in.
///
/// [listConnections]/[authorizeConnection]/[disconnectConnection],
/// [listActivity], and [loadHomeSummary] still delegate to
/// [MockUriClient] — no backend surface exists yet for OAuth-style
/// connection management or a general activity feed, and building one
/// is explicitly out of scope for this UI-prototype-discovery phase
/// (see uri_core/app/server.py's GET /tasks docstring and this
/// milestone's own scope notes). This is intentionally visible here
/// rather than hidden: see the class doc on [UriClient] for the
/// boundary this respects.
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

  /// Every turn this client has produced, keyed by [UriTurn.id] —
  /// needed because POST /approve and POST /cancel return only the
  /// raw execution/decision result (see server.py), not a full turn
  /// shape. approve()/cancel() look the original turn up here and
  /// return an updated copy, the same pattern [MockUriClient] already
  /// uses internally.
  final Map<String, UriTurn> _turns = <String, UriTurn>{};

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

    final turn = _turnFromResponse(id: id, text: text, timestamp: timestamp, body: body);
    _turns[turn.id] = turn;
    return turn;
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
    // Milestone 8A: an additive, shadow-rolled-out field — present
    // only when the backend's drafting+validation both succeeded.
    // Preferred over the deterministic template text below when
    // available, since it's the more natural phrasing; the template
    // text remains the fallback exactly as it always has been.
    final narrative = body['narrative'] as String?;

    final understanding =
        narrative ??
        (semantic != null && semantic['goal'] != null
            ? 'Understood as: ${semantic['goal']}'
            : 'URI processed this request.');

    if (execution != null && execution['status'] == 'awaiting_approval') {
      final actionId = responseData is Map ? responseData['action_id'] as String? : null;
      final toolName = responseData is Map ? responseData['tool_name'] as String? : null;
      final riskValue = responseData is Map ? responseData['risk'] as String? : null;
      final message = responseData is Map ? responseData['message'] as String? : null;
      // The registry's own human-readable description (Issue 4) -
      // preferred over the generic approval-needed message, which
      // stays the fallback when the registry has none.
      final registryDescription =
          responseData is Map ? responseData['description'] as String? : null;
      final humanTitle = toolName != null ? humanizeIdentifier(toolName) : 'Proposed action';

      return UriTurn(
        // Use the backend's real action_id as the turn id when present
        // - approve()/cancel() then need no separate id-mapping table,
        // they just call POST /approve|/cancel with this same id.
        id: actionId ?? id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.awaitingApproval,
        understanding: understanding,
        proposedAction: ProposedAction(
          title: humanTitle,
          description: (registryDescription != null && registryDescription.isNotEmpty)
              ? registryDescription
              : (message ?? 'This action needs your approval before URI can proceed.'),
          targetService: humanTitle,
          impact: impactFromRisk(riskValue),
        ),
      );
    }

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

    if (execution != null && execution['status'] == 'error') {
      final message = responseData is Map ? responseData['message'] : null;
      return UriTurn(
        id: id,
        userText: text,
        timestamp: timestamp,
        stage: TurnStage.failed,
        understanding: understanding,
        failureReason: message?.toString() ?? 'URI could not complete this action.',
      );
    }

    final String summary;
    if (narrative != null) {
      summary = narrative;
    } else if (responseData is Map && responseData['message'] != null) {
      summary = responseData['message'].toString();
    } else {
      // Deliberately never dumps raw JSON (e.g. a drafting tool's
      // {status, note_sheet} shape has no "message" key) - a generic,
      // honest confirmation is always better than an unreadable
      // escaped-JSON string (Issue 3).
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

  Future<UriTurn> _decide({required String actionId, required bool approved}) async {
    final existing = _turns[actionId];

    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl/${approved ? 'approve' : 'cancel'}'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({'action_id': actionId, 'session_id': _sessionId}),
          )
          .timeout(const Duration(seconds: 30));
    } catch (error) {
      final failed = (existing ?? _placeholderTurn(actionId)).copyWith(
        stage: TurnStage.failed,
        failureReason: 'Could not reach the URI backend: $error',
      );
      _turns[actionId] = failed;
      return failed;
    }

    Map<String, dynamic>? body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      body = null;
    }

    if (response.statusCode != 200 || body == null || body['status'] == 'error') {
      final reason = body?['message'] as String? ?? 'URI backend returned HTTP ${response.statusCode}.';
      final failed = (existing ?? _placeholderTurn(actionId)).copyWith(
        stage: TurnStage.failed,
        failureReason: reason,
      );
      _turns[actionId] = failed;
      return failed;
    }

    if (!approved) {
      final cancelled = (existing ?? _placeholderTurn(actionId)).copyWith(
        stage: TurnStage.cancelled,
        result: const ActionResult(
          summary: 'No action was taken.',
          detail: 'You cancelled this before URI carried it out.',
        ),
      );
      _turns[actionId] = cancelled;
      return cancelled;
    }

    // body here is UriOrchestrator.decide_action()'s result: the raw
    // dispatch_result ApprovalGate.decide() returned once approved
    // (e.g. {"status": "success", "data": {...}}), plus an additive
    // "narrative" field (Milestone 8A) explaining that same outcome
    // in URI's voice when drafting+validation both succeeded.
    final narrative = body['narrative'] as String?;
    final data = body['data'];
    final String summary;
    if (narrative != null) {
      summary = narrative;
    } else if (data is Map && data['message'] != null) {
      summary = data['message'].toString();
    } else {
      // Deliberately never dumps raw JSON - see the identical fix in
      // _turnFromResponse (Issue 3).
      summary = 'URI completed this action.';
    }

    final completed = (existing ?? _placeholderTurn(actionId)).copyWith(
      stage: TurnStage.completed,
      result: ActionResult(summary: summary),
    );
    _turns[actionId] = completed;
    return completed;
  }

  /// Used only when approve()/cancel() is called for an id this client
  /// never produced via ask() (e.g. a Tasks-screen item from another
  /// session) — still a real, valid [UriTurn], just without the
  /// original conversational context this client never saw.
  UriTurn _placeholderTurn(String actionId) => UriTurn(
    id: actionId,
    userText: '',
    timestamp: DateTime.now(),
    stage: TurnStage.awaitingApproval,
  );

  @override
  Future<UriTurn> approve(String turnId) => _decide(actionId: turnId, approved: true);

  @override
  Future<UriTurn> cancel(String turnId) => _decide(actionId: turnId, approved: false);

  @override
  Future<List<TaskItem>> listTasks() async {
    http.Response response;
    try {
      response = await _http.get(Uri.parse('$baseUrl/tasks')).timeout(const Duration(seconds: 30));
    } catch (_) {
      return const [];
    }

    if (response.statusCode != 200) return const [];

    final Map<String, dynamic> body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return const [];
    }

    final rawTasks = body['tasks'];
    if (rawTasks is! List) return const [];

    return rawTasks
        .whereType<Map<String, dynamic>>()
        .map(
          (raw) => TaskItem(
            id: raw['action_id'] as String,
            capabilityId: raw['capability_id'] as String? ?? 'unknown',
            description: raw['description'] as String? ?? '',
            risk: raw['risk'] as String? ?? 'unknown',
            sessionId: raw['session_id'] as String? ?? '',
            createdAt: DateTime.tryParse(raw['created_at'] as String? ?? '') ?? DateTime.now(),
          ),
        )
        .toList();
  }

  // ---------------------------------------------------------------
  // No real backend surface exists for these yet — see class doc.
  // ---------------------------------------------------------------

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

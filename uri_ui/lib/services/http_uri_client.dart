import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/uri_turn.dart';
import '../utils/capability_display.dart';
import 'mock_uri_client.dart';
import 'uri_client.dart';

/// M15 correction: a generic, tool-agnostic fallback for when neither
/// a Brain-drafted narrative nor a "message" field is available on a
/// tool's own result map - picks the longest plain-string value
/// present, if any is long enough to plausibly be real content (a
/// drafted document, a generated report, ...) rather than a short
/// status/id token, so a real result is never silently replaced with
/// a content-free confirmation just because the tool happened to use
/// a different key name than "message" (e.g. a drafting tool's
/// {status, note_sheet} shape). Never dumps the whole map as JSON -
/// only ever returns a single string the tool itself already
/// produced. Returns null when nothing suitable exists, leaving the
/// caller's own last-resort fallback text in place.
String? _bestTextualField(Map<dynamic, dynamic> data) {
  const minimumContentLength = 20;
  String? best;

  for (final value in data.values) {
    if (value is String && value.length >= minimumContentLength) {
      if (best == null || value.length > best.length) {
        best = value;
      }
    }
  }

  return best;
}

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
    String? deviceId,
    String? sessionId,
    http.Client? httpClient,
    UriClient? fallback,
  }) : _deviceId = deviceId,
       _sessionId = sessionId ?? _generateSessionId(),
       _http = httpClient ?? http.Client(),
       _fallback = fallback ?? MockUriClient();

  /// Prototype 2 (multi-client + runtime awareness): mutable, not
  /// final — [setBaseUrl] lets a caller (see Settings) repoint this
  /// client at a different backend address (e.g. localhost during
  /// desktop development vs a PC's LAN IP from a phone) without
  /// rebuilding the client or losing [_token]/[_deviceId].
  @override
  String baseUrl;

  /// This install's own client device_id (see device_identity.dart) -
  /// sent only at login/signup time, bound server-side to that login's
  /// token (see auth_session.py). Never sent on any other request, and
  /// never treated as a credential.
  final String? _deviceId;

  final String _sessionId;
  final http.Client _http;
  final UriClient _fallback;

  /// Prototype 1 (multi-user identity): set only by a successful
  /// [login]/[signup], sent as `Authorization: Bearer <token>` on every
  /// request that follows. Null means "not logged in" - those requests
  /// still reach the backend exactly as before login existed (see
  /// server.py's _resolve_authenticated_user_id), so this client keeps
  /// working unauthenticated until a caller explicitly logs in.
  String? _token;
  String? _username;

  /// Every turn this client has produced, keyed by [UriTurn.id] —
  /// needed because POST /approve and POST /cancel return only the
  /// raw execution/decision result (see server.py), not a full turn
  /// shape. approve()/cancel() look the original turn up here and
  /// return an updated copy, the same pattern [MockUriClient] already
  /// uses internally.
  final Map<String, UriTurn> _turns = <String, UriTurn>{};

  static String _generateSessionId() =>
      'flutter-${DateTime.now().microsecondsSinceEpoch}';

  Map<String, String> get _jsonHeaders {
    final token = _token;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  @override
  bool get isAuthenticated => _token != null;

  @override
  String? get currentUsername => _username;

  @override
  void setBaseUrl(String baseUrl) => this.baseUrl = baseUrl;

  @override
  Future<ConnectionCheckResult> checkConnection({String? addressOverride}) async {
    final target = addressOverride ?? baseUrl;

    final Uri uri;
    try {
      uri = Uri.parse('$target/health');
    } catch (error) {
      return ConnectionCheckResult.unreachable('Invalid server address: $error');
    }

    try {
      final response = await _http.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) return const ConnectionCheckResult.reachable();
      return ConnectionCheckResult.unreachable('URI backend returned HTTP ${response.statusCode}.');
    } catch (error) {
      // Never swallowed to a bare false — a cleartext-traffic block, a
      // wrong/unreachable host, a timeout, and a refused connection all
      // produce different messages here, so a real failure is
      // diagnosable instead of collapsing into one generic result.
      return ConnectionCheckResult.unreachable(error.toString());
    }
  }

  Future<AuthOutcome> _authenticate({
    required String path,
    required String username,
    required String password,
  }) async {
    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl$path'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'username': username,
              'password': password,
              if (_deviceId != null) 'device_id': _deviceId,
            }),
          )
          .timeout(const Duration(seconds: 15));
    } catch (error) {
      return AuthOutcome.failure('Could not reach the URI backend: $error');
    }

    Map<String, dynamic>? body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      body = null;
    }

    if (response.statusCode != 200 || body == null || body['token'] == null) {
      final detail = body?['detail']?.toString();
      return AuthOutcome.failure(
        detail ?? 'The URI backend rejected this request (HTTP ${response.statusCode}).',
      );
    }

    _token = body['token'] as String;
    _username = body['username'] as String? ?? username;
    return const AuthOutcome.success();
  }

  @override
  Future<AuthOutcome> signup(String username, String password) =>
      _authenticate(path: '/auth/signup', username: username, password: password);

  @override
  Future<AuthOutcome> login(String username, String password) =>
      _authenticate(path: '/auth/login', username: username, password: password);

  @override
  Future<void> logout() async {
    final token = _token;
    _token = null;
    _username = null;
    if (token == null) return;

    try {
      await _http
          .post(
            Uri.parse('$baseUrl/auth/logout'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(const Duration(seconds: 15));
    } catch (_) {
      // Local state is already cleared above; a failed revoke call on
      // the way out must never block the user from appearing logged
      // out in this client.
    }
  }

  @override
  Future<UriTurn> ask(String text, {String? turnId}) async {
    final id = turnId ?? 'turn-${DateTime.now().microsecondsSinceEpoch}';
    final timestamp = DateTime.now();

    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl/ask'),
            headers: _jsonHeaders,
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
    } else if (responseData is Map &&
        _bestTextualField(responseData) != null) {
      // M15 correction: the Brain's narrative wasn't available this
      // time (e.g. a transient drafting failure), but the tool itself
      // already produced real, readable content under some other key
      // (e.g. a drafting tool's {status, note_sheet} shape) - show
      // that rather than a content-free confirmation that silently
      // discards a real result. This is exactly the tool's own real
      // output, never anything this client invents.
      summary = _bestTextualField(responseData)!;
    } else {
      // Deliberately never dumps the raw map as JSON - a generic,
      // honest confirmation is always better than an unreadable
      // escaped-JSON string (Issue 3). Only reached when there is
      // truly no readable content anywhere in the result.
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
        // Only ever shown when a real tool was actually involved (e.g.
        // a registered capability's dispatch) - a conversational,
        // no-capability-required reply's execution has no "tool" key
        // at all, and must not show a meaningless "Tool: success"/
        // "Tool: null" line under a plain greeting.
        detail: execution != null && execution['tool'] != null
            ? 'Tool: ${execution['tool']}'
            : null,
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
            headers: _jsonHeaders,
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
    } else if (data is Map && _bestTextualField(data) != null) {
      // M15 correction: see the identical fix in _turnFromResponse -
      // relay the tool's own real, readable content rather than
      // discarding it just because it isn't under "message".
      summary = _bestTextualField(data)!;
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
      response = await _http
          .get(Uri.parse('$baseUrl/tasks'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
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

  /// Real authorization state from the backend's GET /connections
  /// (see uri_core/core/connection_status.py). Previously this
  /// delegated to [_fallback], whose seeded mock data always claimed
  /// Gmail was "Connected" whether or not any credential existed —
  /// a badge the backend could not back with anything real.
  ///
  /// An unreachable backend or unreadable body degrades to an empty
  /// list (the Connections screen then simply shows nothing) rather
  /// than falling back to mock data, because a fabricated
  /// "Connected" is worse than showing no state at all.
  @override
  Future<List<ServiceConnection>> listConnections() async {
    http.Response response;
    try {
      response = await _http
          .get(Uri.parse('$baseUrl/connections'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
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

    final raw = body['connections'];
    if (raw is! List) return const [];

    return raw
        .whereType<Map<String, dynamic>>()
        .map(
          (item) => ServiceConnection(
            id: item['id'] as String? ?? 'unknown',
            name: item['name'] as String? ?? 'Unknown service',
            description: item['description'] as String? ?? '',
            status: _connectionStatusFrom(item['status'] as String?),
            detail: item['detail'] as String?,
          ),
        )
        .toList();
  }

  /// Unknown/absent values map to [ConnectionStatus.notConnected] —
  /// never to connected — so an unrecognized backend value can never
  /// be displayed as an authorization URI does not actually have.
  static ConnectionStatus _connectionStatusFrom(String? raw) {
    switch (raw) {
      case 'connected':
        return ConnectionStatus.connected;
      case 'needs_authorization':
        return ConnectionStatus.needsAuthorization;
      default:
        return ConnectionStatus.notConnected;
    }
  }

  /// Google OAuth consent runs a local browser flow on the URI server
  /// host, so it cannot be completed from a phone client. Rather than
  /// fabricate a "Connected" result the way the mock did, this
  /// re-reads the real state — so the button reflects whatever
  /// actually changed on the host, and nothing if nothing did.
  @override
  Future<ServiceConnection> authorizeConnection(String connectionId) async {
    final current = await listConnections();
    return current.firstWhere(
      (c) => c.id == connectionId,
      orElse: () => ServiceConnection(
        id: connectionId,
        name: connectionId,
        description: '',
        status: ConnectionStatus.notConnected,
        detail: 'Sign-in must be completed on the URI server host.',
      ),
    );
  }

  // ---------------------------------------------------------------
  // No real backend surface exists for these yet — see class doc.
  // ---------------------------------------------------------------

  @override
  Future<ServiceConnection> disconnectConnection(String connectionId) =>
      _fallback.disconnectConnection(connectionId);

  @override
  Future<List<ActivityEvent>> listActivity() => _fallback.listActivity();

  @override
  Future<HomeSummary> loadHomeSummary() => _fallback.loadHomeSummary();
}

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/memory_entry.dart';
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
/// As of M16 this client delegates to [MockUriClient] for NOTHING.
/// Every method is backed by a real backend call: connections by
/// GET/DELETE /connections, activity by GET /activity (the runtime's
/// own AuditTrail), and the home summary composed from real /tasks and
/// /connections data. Where the backend cannot evidence something, the
/// method returns an honest empty/unchanged result rather than mock
/// data — the UI must never present fabricated state as real.
class HttpUriClient implements UriClient {
  HttpUriClient({
    this.baseUrl = 'http://localhost:8000',
    String? deviceId,
    String? sessionId,
    http.Client? httpClient,
  }) : _deviceId = deviceId,
       _sessionId = sessionId ?? _generateSessionId(),
       _http = httpClient ?? http.Client();

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

  // M18: mutable so the client can be repointed at a past conversation
  // to resume it (see setSessionId / AppState.resumeSession). A fresh
  // login/session still starts from a generated id.
  String _sessionId;
  final http.Client _http;

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
      response = await _askOnce(text);
    } on http.ClientException {
      // A pooled keep-alive connection that went idle (e.g. over a
      // Tailscale relay) dies with exactly this exception on its next
      // reuse, before the request ever reaches the server - confirmed
      // by the backend's access log never showing the attempt at all.
      // A single retry opens a fresh connection; since the prior
      // attempt provably never reached the server, this cannot result
      // in the same ask being processed twice.
      try {
        response = await _askOnce(text);
      } catch (error) {
        return UriTurn(
          id: id,
          userText: text,
          timestamp: timestamp,
          stage: TurnStage.failed,
          failureReason: 'Could not reach the URI backend: $error',
        );
      }
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

  Future<http.Response> _askOnce(String text) {
    return _http
        .post(
          Uri.parse('$baseUrl/ask'),
          headers: _jsonHeaders,
          body: jsonEncode({'session_id': _sessionId, 'text': text}),
        )
        // The backend runs a multi-step reasoning chain against a
        // local LLM for every /ask (semantic analysis, planning,
        // drafting are each a separate model call) - confirmed to take
        // ~20s on its own even for a request that ends up failing, and
        // Ollama reloading the model after ~5 minutes idle (its
        // default keep_alive) adds several seconds more on top of
        // that. 30s was tuned for a network problem (a dead pooled
        // connection - see the retry above), not for how long this
        // endpoint can legitimately take to answer; 120s leaves real
        // headroom for a cold model load plus relay latency without
        // that answer never even having a chance to arrive.
        .timeout(const Duration(seconds: 120));
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
        sources: _sourcesFrom(responseData),
        generatedFile: _generatedFileFrom(responseData),
      ),
    );
  }

  /// M19: the real file a generation capability (generate_document,
  /// draft_institutional_note/order — see server.py's dispatch
  /// response) actually stored, taken verbatim from the tool's own
  /// {"file": {file_id, filename, media_type, size_bytes}} reference —
  /// the exact shape FileStore.StoredFile.to_reference() already
  /// returns for a user's own uploads. Null unless a real file
  /// reference is present; never synthesised.
  static Attachment? _generatedFileFrom(dynamic responseData) {
    if (responseData is! Map) return null;
    final file = responseData['file'];
    if (file is! Map) return null;

    final fileId = file['file_id'];
    final filename = file['filename'];
    if (fileId is! String || fileId.isEmpty) return null;
    if (filename is! String || filename.isEmpty) return null;

    return Attachment(
      fileId: fileId,
      filename: filename,
      mediaType: file['media_type'] as String? ?? 'application/octet-stream',
      sizeBytes: (file['size_bytes'] as num?)?.toInt() ?? 0,
    );
  }

  /// M16: the REAL sources behind a researched answer, taken verbatim
  /// from the tool result the backend already returns (web_search's
  /// {title, url, content} entries). Before this, the URLs were
  /// dropped at the client boundary and the user had no way to verify
  /// a researched claim.
  ///
  /// Never synthesised: only entries that genuinely carry a url are
  /// included, so an answer can never display a citation URI did not
  /// actually retrieve.
  static List<ResultSource> _sourcesFrom(dynamic responseData) {
    if (responseData is! Map) return const [];

    final raw = responseData['results'];
    if (raw is! List) return const [];

    final sources = <ResultSource>[];

    for (final item in raw) {
      if (item is! Map) continue;
      final url = item['url'];
      if (url is! String || url.isEmpty) continue;
      sources.add(
        ResultSource(
          title: (item['title'] as String?)?.trim().isNotEmpty == true
              ? item['title'] as String
              : url,
          url: url,
        ),
      );
    }

    return sources;
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

    return _connectionsFrom(body['connections']);
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
  /// host, so it cannot be completed from a phone client - server.py's
  /// authorize_connection deliberately never launches that flow from
  /// an HTTP call, and returns the real state plus a plain-language
  /// explanation instead. This actually calls that endpoint (a
  /// previous version of this method silently never did, which is why
  /// tapping Connect/Reconnect used to appear to do nothing at all)
  /// and surfaces its "detail" string verbatim, so the caller can show
  /// the user exactly what is required rather than a re-read of
  /// unchanged state with no explanation.
  @override
  Future<ConnectionAuthorizeOutcome> authorizeConnection(String connectionId) async {
    final fallback = ServiceConnection(
      id: connectionId,
      name: connectionId,
      description: '',
      status: ConnectionStatus.notConnected,
      detail: 'Sign-in must be completed on the URI server host.',
    );

    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl/connections/$connectionId/authorize'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 30));
    } catch (error) {
      return ConnectionAuthorizeOutcome(
        connection: fallback,
        explanation: 'Could not reach the URI backend: $error',
      );
    }

    if (response.statusCode != 200) {
      return ConnectionAuthorizeOutcome(
        connection: fallback,
        explanation: 'URI backend returned HTTP ${response.statusCode}.',
      );
    }

    final Map<String, dynamic> body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (error) {
      return ConnectionAuthorizeOutcome(
        connection: fallback,
        explanation: 'URI backend returned a response that could not be parsed.',
      );
    }

    final connections = _connectionsFrom(body['connections']);
    final connection = connections.firstWhere(
      (c) => c.id == connectionId,
      orElse: () => fallback,
    );
    final explanation = body['detail'] as String? ?? connection.detail ?? 'No further detail was provided.';

    return ConnectionAuthorizeOutcome(connection: connection, explanation: explanation);
  }

  /// Shared with [listConnections] - both read the exact same
  /// "connections" list shape, just from different endpoints.
  static List<ServiceConnection> _connectionsFrom(Object? raw) {
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

  /// A REAL disconnect: the backend removes the stored OAuth token, so
  /// the service genuinely requires sign-in again. Previously this
  /// delegated to the mock, which reported "Disconnected" while
  /// nothing had actually changed.
  ///
  /// The returned state is whatever the backend reports afterwards —
  /// never an assumed "now disconnected".
  @override
  Future<ServiceConnection> disconnectConnection(String connectionId) async {
    try {
      await _http
          .delete(
            Uri.parse('$baseUrl/connections/$connectionId'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      // Fall through: re-read real state rather than assume either way.
    }

    final current = await listConnections();
    return current.firstWhere(
      (c) => c.id == connectionId,
      orElse: () => ServiceConnection(
        id: connectionId,
        name: connectionId,
        description: '',
        status: ConnectionStatus.notConnected,
        detail: null,
      ),
    );
  }

  /// Real audit-backed activity from GET /activity (see
  /// audit_trail.py). Previously served fabricated mock events.
  ///
  /// An unreachable backend yields an empty list — an honest "nothing
  /// to show" — never invented history.
  @override
  Future<List<ActivityEvent>> listActivity() async {
    http.Response response;
    try {
      response = await _http
          .get(Uri.parse('$baseUrl/activity'), headers: _jsonHeaders)
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

    final raw = body['activity'];
    if (raw is! List) return const [];

    return raw.whereType<Map<String, dynamic>>().map((item) {
      final eventType = item['event_type'] as String? ?? 'event';
      final capability = item['capability'] as String?;
      final status = item['status'] as String?;
      return ActivityEvent(
        id: item['id'] as String? ?? eventType,
        timestamp:
            DateTime.tryParse(item['timestamp'] as String? ?? '') ??
                DateTime.now(),
        kind: _activityKindFrom(eventType),
        summary: capability == null
            ? _humanizeEventType(eventType)
            : '${_humanizeEventType(eventType)}: $capability',
        detail: status,
      );
    }).toList();
  }

  /// Maps a runtime audit event_type onto the client's display kinds.
  /// An unrecognized type falls back to [ActivityKind.system] rather
  /// than being dropped — the event really happened, so it is shown.
  static ActivityKind _activityKindFrom(String eventType) {
    if (eventType.contains('approval')) return ActivityKind.approval;
    if (eventType.contains('execution')) return ActivityKind.execution;
    if (eventType.contains('cancel')) return ActivityKind.cancellation;
    if (eventType.contains('proposal') || eventType.contains('reasoning')) {
      return ActivityKind.proposal;
    }
    return ActivityKind.system;
  }

  static String _humanizeEventType(String raw) {
    final words = raw.split('_').where((w) => w.isNotEmpty).toList();
    if (words.isEmpty) return raw;
    return words
        .map((w) => w[0].toUpperCase() + w.substring(1))
        .join(' ');
  }

  /// Every fact URI holds about the user, from GET /memory. An
  /// unreachable/failing backend yields an empty list — an honest
  /// "nothing to show", never invented entries.
  @override
  Future<List<MemoryEntry>> listMemory() async {
    http.Response response;
    try {
      response = await _http
          .get(Uri.parse('$baseUrl/memory'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      return const [];
    }

    if (response.statusCode != 200) return const [];

    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['memories'];
      if (raw is! List) return const [];
      return raw.whereType<Map<String, dynamic>>().map(_memoryFrom).toList();
    } catch (_) {
      return const [];
    }
  }

  static MemoryEntry _memoryFrom(Map<String, dynamic> item) {
    return MemoryEntry(
      memoryId: item['memory_id'] as String? ?? '',
      category: item['category'] as String? ?? '',
      consent: item['consent'] as String? ?? '',
      content: item['content'] as String? ?? '',
      confidence: (item['confidence'] as num?)?.toDouble(),
      notes: item['notes'] as String?,
      status: item['status'] as String? ?? '',
      createdAt: item['created_at'] as String? ?? '',
      updatedAt: item['updated_at'] as String? ?? '',
    );
  }

  @override
  Future<MemoryEntry> addMemory({
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    http.Response response;
    try {
      response = await _http
          .post(
            Uri.parse('$baseUrl/memory'),
            headers: _jsonHeaders,
            body: jsonEncode({
              'category': category,
              'content': content,
              if (confidence != null) 'confidence': confidence,
              if (notes != null) 'notes': notes,
            }),
          )
          .timeout(const Duration(seconds: 30));
    } catch (error) {
      throw MemoryWriteException('Could not reach the URI backend: $error');
    }

    if (response.statusCode != 200) {
      String detail = 'URI backend returned HTTP ${response.statusCode}.';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        if (body['detail'] is String) detail = body['detail'] as String;
      } catch (_) {
        // Keep the generic HTTP-status message above.
      }
      throw MemoryWriteException(detail);
    }

    return _memoryFrom(jsonDecode(response.body) as Map<String, dynamic>);
  }

  @override
  Future<bool> deleteMemory(String memoryId) async {
    try {
      final response = await _http
          .delete(Uri.parse('$baseUrl/memory/$memoryId'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return false;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['deleted'] == true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<MemoryEntry> updateMemory({
    required String memoryId,
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    http.Response response;
    try {
      response = await _http
          .put(
            Uri.parse('$baseUrl/memory/$memoryId'),
            headers: _jsonHeaders,
            body: jsonEncode({
              'category': category,
              'content': content,
              if (confidence != null) 'confidence': confidence,
              if (notes != null) 'notes': notes,
            }),
          )
          .timeout(const Duration(seconds: 30));
    } catch (error) {
      throw MemoryWriteException('Could not reach the URI backend: $error');
    }

    if (response.statusCode != 200) {
      String detail = 'URI backend returned HTTP ${response.statusCode}.';
      try {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        if (body['detail'] is String) detail = body['detail'] as String;
      } catch (_) {
        // Keep the generic HTTP-status message above.
      }
      throw MemoryWriteException(detail);
    }

    return _memoryFrom(jsonDecode(response.body) as Map<String, dynamic>);
  }

  @override
  String get sessionId => _sessionId;

  @override
  void setSessionId(String sessionId) {
    _sessionId = sessionId;
  }

  @override
  Future<MemoryEntry?> confirmMemory(String memoryId, {String? content}) async {
    try {
      final response = await _http
          .post(
            Uri.parse('$baseUrl/memory/$memoryId/confirm'),
            headers: _jsonHeaders,
            body: jsonEncode({if (content != null) 'content': content}),
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return null;
      return _memoryFrom(jsonDecode(response.body) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<bool> rejectMemory(String memoryId) async {
    try {
      final response = await _http
          .post(Uri.parse('$baseUrl/memory/$memoryId/reject'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return false;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['rejected'] == true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<ConversationSummary>> listHistory() async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/history'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return const [];
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['sessions'];
      if (raw is! List) return const [];
      return raw.whereType<Map<String, dynamic>>().map((item) {
        return ConversationSummary(
          sessionId: item['session_id'] as String? ?? '',
          turnCount: (item['turn_count'] as num?)?.toInt() ?? 0,
          preview: item['preview'] as String? ?? '',
          lastActivity: item['last_activity'] as String?,
        );
      }).toList();
    } catch (_) {
      return const [];
    }
  }

  @override
  Future<List<UriTurn>> getHistory(String sessionId) async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/history/$sessionId'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return const [];
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['turns'];
      if (raw is! List) return const [];
      return raw.whereType<Map<String, dynamic>>().map((turn) {
        final status = turn['status'] as String?;
        final responseText = turn['response_text'] as String? ?? '';
        // A past turn is rendered read-only: a completed turn shows its
        // recorded response as the result; a failed turn shows it as the
        // failure detail. Never re-runs or re-proposes anything.
        final failed = status != null &&
            status != 'success' &&
            status != 'awaiting_approval';
        return UriTurn(
          id: turn['turn_id'] as String? ??
              'history-${DateTime.now().microsecondsSinceEpoch}',
          userText: turn['user_text'] as String? ?? '',
          timestamp: DateTime.tryParse(turn['timestamp'] as String? ?? '') ??
              DateTime.now(),
          stage: failed ? TurnStage.failed : TurnStage.completed,
          failureReason: failed ? responseText : null,
          result: failed
              ? null
              : ActionResult(summary: responseText.isEmpty ? '—' : responseText),
        );
      }).toList();
    } catch (_) {
      return const [];
    }
  }

  @override
  Future<bool> deleteHistory(String sessionId) async {
    try {
      final response = await _http
          .delete(Uri.parse('$baseUrl/history/$sessionId'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return false;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['deleted'] == true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<AccountInfo?> getAccountInfo() async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/auth/me'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return null;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      if (body['authenticated'] != true) return null;
      final userId = body['user_id'] as String?;
      if (userId == null) return null;
      return AccountInfo(
        userId: userId,
        username: body['username'] as String?,
        role: body['role'] as String?,
        experienceTier: body['experience_tier'] as String?,
        deviceId: body['device_id'] as String?,
        runtimeDeviceId: body['runtime_device_id'] as String?,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  Future<bool> setExperienceTier(String tier) async {
    try {
      final response = await _http
          .post(
            Uri.parse('$baseUrl/auth/experience-tier'),
            headers: _jsonHeaders,
            body: jsonEncode({'experience_tier': tier}),
          )
          .timeout(const Duration(seconds: 30));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<DeviceSession>> listDevices() async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/auth/devices'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return const [];
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['devices'];
      if (raw is! List) return const [];
      return raw.whereType<Map<String, dynamic>>().map((item) {
        return DeviceSession(
          deviceId: item['device_id'] as String? ?? '',
          sessionCount: (item['session_count'] as num?)?.toInt() ?? 0,
          mostRecentExpiresAt: item['most_recent_expires_at'] as String?,
        );
      }).toList();
    } catch (_) {
      return const [];
    }
  }

  @override
  Future<int> revokeDevice(String deviceId) async {
    try {
      final response = await _http
          .delete(
            Uri.parse('$baseUrl/auth/devices/$deviceId'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return 0;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return (body['revoked_sessions'] as num?)?.toInt() ?? 0;
    } catch (_) {
      return 0;
    }
  }

  @override
  Future<ModelStatus?> getModelStatus() async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/capabilities'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return null;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final model = body['model'];
      if (model is! Map<String, dynamic>) return null;
      final providerName = model['provider_name'] as String?;
      final modelName = model['model_name'] as String?;
      if (providerName == null || modelName == null) return null;
      return ModelStatus(
        providerName: providerName,
        modelName: modelName,
        location: model['location'] as String? ?? 'unknown',
        available: model['available'] as bool? ?? false,
        detail: model['detail'] as String?,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  Future<UriIdentity?> getIdentity() async {
    try {
      final response = await _http
          .get(Uri.parse('$baseUrl/identity'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return null;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final userId = body['user_id'] as String?;
      final deviceId = body['device_id'] as String?;
      if (userId == null || deviceId == null) return null;
      return UriIdentity(userId: userId, deviceId: deviceId);
    } catch (_) {
      return null;
    }
  }

  /// M16: URI's real capability catalogue from GET /capabilities.
  /// Relayed verbatim, including the honest gap_reason — the client
  /// never re-decides what URI can do.
  @override
  Future<List<CapabilityInfo>> listCapabilities() async {
    http.Response response;
    try {
      response = await _http
          .get(Uri.parse('$baseUrl/capabilities'), headers: _jsonHeaders)
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      return const [];
    }

    if (response.statusCode != 200) return const [];

    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['capabilities'];
      if (raw is! List) return const [];

      return raw
          .whereType<Map<String, dynamic>>()
          .map(
            (item) => CapabilityInfo(
              id: item['id'] as String? ?? 'unknown',
              description: item['description'] as String? ?? '',
              status: item['status'] as String? ?? 'unknown',
              availability: item['availability'] as String? ?? 'unknown',
              approvalRequirement:
                  item['approval_requirement'] as String? ?? 'none',
              risk: item['risk'] as String? ?? 'unknown',
              limitations: (item['limitations'] as String?)?.trim().isEmpty ==
                      false
                  ? item['limitations'] as String
                  : null,
              gapReason: item['gap_reason'] as String?,
            ),
          )
          .toList();
    } catch (_) {
      return const [];
    }
  }

  /// M16: sends the user's real preferences to the backend profile so
  /// the Brain actually receives them (see personalization_context.py).
  /// Reports whether the backend accepted them; a failure is never
  /// reported as success.
  @override
  Future<bool> syncPreferences({
    required String communicationStyle,
    required String autonomyLevel,
    required List<String> focusAreas,
  }) async {
    try {
      final response = await _http
          .post(
            Uri.parse('$baseUrl/profile'),
            headers: _jsonHeaders,
            body: jsonEncode({
              'communication_style': communicationStyle,
              'autonomy_level': autonomyLevel,
              'focus_areas': focusAreas,
            }),
          )
          .timeout(const Duration(seconds: 30));

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// M16: uploads one file for the CURRENT conversation session, so
  /// the backend scopes it to exactly this chat (see file_store.py's
  /// per-session listing and read_attached_file's session boundary).
  ///
  /// Validation lives on the backend, never here: this relays the
  /// real rejection reason as an [AttachmentException] rather than
  /// pre-judging what is acceptable.
  @override
  Future<Attachment> uploadAttachment({
    required String filename,
    required List<int> bytes,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/files'),
    )
      ..fields['session_id'] = _sessionId
      ..files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );

    if (_token != null) {
      request.headers['Authorization'] = 'Bearer $_token';
    }

    http.Response response;
    try {
      // _http.send (not request.send) so the configured/injected
      // client is used - request.send() would silently create its own.
      final streamed = await _http.send(request).timeout(
            const Duration(seconds: 60),
          );
      response = await http.Response.fromStream(streamed);
    } catch (_) {
      throw const AttachmentException(
        'URI could not be reached, so the file was not attached.',
      );
    }

    if (response.statusCode != 200) {
      throw AttachmentException(_uploadFailureReason(response));
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return _attachmentFrom(body['file'] as Map<String, dynamic>);
  }

  /// The backend's own reason (FastAPI puts it in `detail`), falling
  /// back to a plain message rather than showing raw JSON.
  static String _uploadFailureReason(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] is String) {
        return body['detail'] as String;
      }
    } catch (_) {
      // fall through
    }
    return 'The file could not be attached (HTTP ${response.statusCode}).';
  }

  static Attachment _attachmentFrom(Map<String, dynamic> raw) {
    return Attachment(
      fileId: raw['file_id'] as String? ?? '',
      filename: raw['filename'] as String? ?? 'file',
      mediaType: raw['media_type'] as String? ?? 'application/octet-stream',
      sizeBytes: (raw['size_bytes'] as num?)?.toInt() ?? 0,
    );
  }

  @override
  Future<List<Attachment>> listAttachments() async {
    http.Response response;
    try {
      response = await _http
          .get(
            Uri.parse('$baseUrl/files?session_id=$_sessionId'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 30));
    } catch (_) {
      return const [];
    }

    if (response.statusCode != 200) return const [];

    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final raw = body['files'];
      if (raw is! List) return const [];
      return raw
          .whereType<Map<String, dynamic>>()
          .map(_attachmentFrom)
          .toList();
    } catch (_) {
      return const [];
    }
  }

  @override
  Future<bool> deleteAttachment(String fileId) async {
    try {
      final response = await _http
          .delete(
            Uri.parse('$baseUrl/files/$fileId'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) return false;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['deleted'] == true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<List<int>> downloadAttachmentContent(String fileId) async {
    http.Response response;
    try {
      response = await _http
          .get(
            Uri.parse('$baseUrl/files/$fileId/content'),
            headers: _jsonHeaders,
          )
          .timeout(const Duration(seconds: 60));
    } catch (error) {
      throw AttachmentException('Could not reach the URI backend: $error');
    }

    if (response.statusCode != 200) {
      throw AttachmentException(
        'URI backend returned HTTP ${response.statusCode} for this file.',
      );
    }

    return response.bodyBytes;
  }

  /// Composed entirely from REAL data already fetched from real
  /// endpoints — pending approvals from /tasks, service counts from
  /// /connections — plus the caller-supplied conversation the client
  /// already holds. Previously this returned mock counts.
  ///
  /// No new endpoint is needed: every number here is something the
  /// backend can already evidence.
  @override
  Future<HomeSummary> loadHomeSummary() async {
    final tasks = await listTasks();
    final connections = await listConnections();

    return HomeSummary(
      recentTurns: const [],
      pendingApprovalCount: tasks.length,
      connectedServiceCount: connections
          .where((c) => c.status == ConnectionStatus.connected)
          .length,
      totalServiceCount: connections.length,
    );
  }
}

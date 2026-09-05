import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/uri_turn.dart';
import 'uri_client.dart';

/// In-memory stand-in for URI's runtime.
///
/// This is UI-side mock data only — no network, no OAuth, no Python
/// process involved. It exists so the interface in [UriClient] has a
/// working implementation to build and test the UI against.
///
/// The "understanding" heuristic below reacts to loose signal words
/// (mentions of mail, a document, a meeting, a question) purely so the
/// mock has *some* varied, request-shaped behaviour to demo — it is not
/// a capability catalogue, and nothing here should be read as the set
/// of things URI can do. A real backend would replace this whole file.
class MockUriClient implements UriClient {
  MockUriClient() {
    _seedConnections();
    _seedActivity();
  }

  final Map<String, UriTurn> _turns = <String, UriTurn>{};
  final List<ServiceConnection> _connections = <ServiceConnection>[];
  final List<ActivityEvent> _activity = <ActivityEvent>[];
  int _idCounter = 0;

  String _nextId(String prefix) => '$prefix-${++_idCounter}';

  // ---------------------------------------------------------------
  // Auth — no real backend involved, just enough state for widget
  // tests and the mock-only fallback paths to have something
  // consistent to react to. Never used by HttpUriClient.
  //
  // Starts already "logged in" (as a placeholder user) rather than
  // starting logged out - every existing widget test builds
  // AppState(client: MockUriClient()) and expects to land straight on
  // onboarding/Home with no login screen in the way, since real login
  // is a property of the HTTP backend (see HttpUriClient), not of this
  // offline stand-in. Call logout() explicitly in a test that wants to
  // exercise the logged-out state against MockUriClient.
  // ---------------------------------------------------------------

  String? _username = 'demo-user';

  @override
  bool get isAuthenticated => _username != null;

  @override
  String? get currentUsername => _username;

  @override
  Future<AuthOutcome> signup(String username, String password) async {
    await _latency(const Duration(milliseconds: 120));
    _username = username;
    return const AuthOutcome.success();
  }

  @override
  Future<AuthOutcome> login(String username, String password) async {
    await _latency(const Duration(milliseconds: 120));
    _username = username;
    return const AuthOutcome.success();
  }

  @override
  Future<void> logout() async {
    _username = null;
  }

  // ---------------------------------------------------------------
  // Connection config — no real backend, so these are trivial: this
  // mock is always "reachable" and baseUrl is a fixed placeholder
  // never actually dialed. See HttpUriClient for the real behaviour
  // this stands in for.
  // ---------------------------------------------------------------

  String _baseUrl = 'mock://local';

  @override
  String get baseUrl => _baseUrl;

  @override
  void setBaseUrl(String baseUrl) => _baseUrl = baseUrl;

  @override
  Future<bool> checkConnection() async {
    await _latency(const Duration(milliseconds: 80));
    return true;
  }

  void _seedConnections() {
    _connections.addAll(const [
      ServiceConnection(
        id: 'gmail',
        name: 'Gmail',
        description: 'Read relevant messages and prepare replies for your review.',
        status: ConnectionStatus.connected,
        detail: 'Connected',
      ),
      ServiceConnection(
        id: 'drive',
        name: 'Google Drive',
        description: 'Find and reference documents you already have access to.',
        status: ConnectionStatus.connected,
        detail: 'Connected',
      ),
      ServiceConnection(
        id: 'calendar',
        name: 'Calendar',
        description: 'Check availability and propose scheduling changes.',
        status: ConnectionStatus.needsAuthorization,
        detail: 'Authorization expired — reconnect to use this',
      ),
      ServiceConnection(
        id: 'drafting',
        name: 'Institutional Drafting',
        description: 'Prepare office notes and orders in the institute\'s format.',
        status: ConnectionStatus.connected,
        detail: 'Connected',
      ),
      ServiceConnection(
        id: 'sheets',
        name: 'Google Sheets',
        description: 'Read structured records such as rosters or logs.',
        status: ConnectionStatus.notConnected,
      ),
    ]);
  }

  void _seedActivity() {
    final now = DateTime.now();
    _activity.addAll([
      ActivityEvent(
        id: _nextId('act'),
        timestamp: now.subtract(const Duration(hours: 3)),
        kind: ActivityKind.execution,
        summary: 'Sent a reply to a routine query on your behalf.',
        detail: 'Auto-approved under your routine-action preference.',
      ),
      ActivityEvent(
        id: _nextId('act'),
        timestamp: now.subtract(const Duration(hours: 6)),
        kind: ActivityKind.approval,
        summary: 'You approved a proposed document draft.',
      ),
      ActivityEvent(
        id: _nextId('act'),
        timestamp: now.subtract(const Duration(days: 1)),
        kind: ActivityKind.system,
        summary: 'Google Drive connected.',
      ),
    ]);
  }

  Future<void> _latency([Duration duration = const Duration(milliseconds: 420)]) =>
      Future.delayed(duration);

  ServiceConnection? _findConnection(String id) {
    for (final connection in _connections) {
      if (connection.id == id) return connection;
    }
    return null;
  }

  // ---------------------------------------------------------------
  // Connections
  // ---------------------------------------------------------------

  @override
  Future<List<ServiceConnection>> listConnections() async {
    await _latency();
    return List.unmodifiable(_connections);
  }

  @override
  Future<ServiceConnection> authorizeConnection(String connectionId) async {
    await _latency();
    final index = _connections.indexWhere((c) => c.id == connectionId);
    if (index == -1) {
      throw StateError('Unknown connection: $connectionId');
    }
    final updated = _connections[index].copyWith(
      status: ConnectionStatus.connected,
      detail: 'Connected',
    );
    _connections[index] = updated;
    _activity.insert(
      0,
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: ActivityKind.system,
        summary: '${updated.name} connected.',
      ),
    );
    return updated;
  }

  @override
  Future<ServiceConnection> disconnectConnection(String connectionId) async {
    await _latency();
    final index = _connections.indexWhere((c) => c.id == connectionId);
    if (index == -1) {
      throw StateError('Unknown connection: $connectionId');
    }
    final updated = _connections[index].copyWith(
      status: ConnectionStatus.notConnected,
      detail: null,
    );
    _connections[index] = updated;
    _activity.insert(
      0,
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: ActivityKind.system,
        summary: '${updated.name} disconnected.',
      ),
    );
    return updated;
  }

  // ---------------------------------------------------------------
  // Ask URI
  // ---------------------------------------------------------------

  @override
  Future<UriTurn> ask(String text) async {
    await _latency();
    final id = _nextId('turn');
    final analysis = _analyze(text);

    final TurnStage stage;
    if (analysis.isBlockedByConnection) {
      stage = TurnStage.needsConnection;
    } else if (analysis.proposedAction != null) {
      stage = TurnStage.awaitingApproval;
    } else {
      stage = TurnStage.completed;
    }

    final turn = UriTurn(
      id: id,
      userText: text,
      timestamp: DateTime.now(),
      stage: stage,
      understanding: analysis.understanding,
      proposedAction: analysis.proposedAction,
      result: analysis.directResult,
      requiredConnectionId: analysis.requiredConnectionId,
      requiredConnectionName: analysis.requiredConnectionName,
    );
    _turns[id] = turn;

    final String activitySummary;
    if (analysis.isBlockedByConnection) {
      activitySummary = 'Needs ${analysis.requiredConnectionName} to continue: "${_truncate(text)}"';
    } else if (analysis.proposedAction != null) {
      activitySummary = 'Proposed: ${analysis.proposedAction!.title}';
    } else {
      activitySummary = 'Answered directly: "${_truncate(text)}"';
    }

    _activity.insert(
      0,
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: analysis.isBlockedByConnection ? ActivityKind.system : ActivityKind.proposal,
        summary: activitySummary,
      ),
    );

    return turn;
  }

  @override
  Future<UriTurn> approve(String turnId) async {
    final existing = _turns[turnId];
    if (existing == null) {
      throw StateError('Unknown turn: $turnId');
    }

    _turns[turnId] = existing.copyWith(stage: TurnStage.executing);
    await _latency(const Duration(milliseconds: 650));

    final action = existing.proposedAction!;
    final result = ActionResult(
      summary: 'Completed — ${_lowerFirst(action.title)}.',
      detail: _resultDetailFor(action),
    );

    final completed = existing.copyWith(stage: TurnStage.completed, result: result);
    _turns[turnId] = completed;

    _activity.insertAll(0, [
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: ActivityKind.execution,
        summary: 'Executed: ${action.title}',
        detail: result.summary,
      ),
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: ActivityKind.approval,
        summary: 'You approved: ${action.title}',
      ),
    ]);

    return completed;
  }

  @override
  Future<UriTurn> cancel(String turnId) async {
    await _latency(const Duration(milliseconds: 200));
    final existing = _turns[turnId];
    if (existing == null) {
      throw StateError('Unknown turn: $turnId');
    }
    final cancelled = existing.copyWith(
      stage: TurnStage.cancelled,
      result: const ActionResult(
        summary: 'No action was taken.',
        detail: 'You cancelled this before URI carried it out.',
      ),
    );
    _turns[turnId] = cancelled;

    _activity.insert(
      0,
      ActivityEvent(
        id: _nextId('act'),
        timestamp: DateTime.now(),
        kind: ActivityKind.cancellation,
        summary: 'You cancelled: ${existing.proposedAction?.title ?? existing.userText}',
      ),
    );

    return cancelled;
  }

  // ---------------------------------------------------------------
  // Activity + Home
  // ---------------------------------------------------------------

  @override
  Future<List<ActivityEvent>> listActivity() async {
    await _latency();
    return List.unmodifiable(_activity);
  }

  @override
  Future<HomeSummary> loadHomeSummary() async {
    await _latency();
    final pending = _turns.values
        .where((t) => t.stage == TurnStage.awaitingApproval)
        .length;
    final connected = _connections
        .where((c) => c.status == ConnectionStatus.connected)
        .length;
    final recent = _turns.values.toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

    return HomeSummary(
      recentTurns: recent.take(3).toList(),
      pendingApprovalCount: pending,
      connectedServiceCount: connected,
      totalServiceCount: _connections.length,
    );
  }

  // ---------------------------------------------------------------
  // Tasks
  // ---------------------------------------------------------------

  @override
  Future<List<TaskItem>> listTasks() async {
    await _latency();

    return _turns.values
        .where((turn) => turn.stage == TurnStage.awaitingApproval)
        .map(
          (turn) => TaskItem(
            id: turn.id,
            capabilityId: turn.proposedAction?.targetService ?? 'unknown',
            description: turn.proposedAction?.description ?? '',
            risk: _riskFromImpact(turn.proposedAction?.impact),
            sessionId: 'mock-session',
            createdAt: turn.timestamp,
          ),
        )
        .toList();
  }

  String _riskFromImpact(ActionImpact? impact) {
    switch (impact) {
      case ActionImpact.routine:
        return 'controlled';
      case ActionImpact.notable:
        return 'variable';
      case ActionImpact.sensitive:
        return 'high';
      case null:
        return 'unknown';
    }
  }

  // ---------------------------------------------------------------
  // Heuristic "understanding" — mock only, see class doc.
  // ---------------------------------------------------------------

  _Analysis _analyze(String rawText) {
    final text = rawText.toLowerCase();

    bool has(List<String> words) => words.any(text.contains);

    final isQuestion = has(['what', 'how many', 'when', 'who', 'is there', 'do i', 'can i']) &&
        !has(['draft', 'send', 'schedule', 'submit', 'renew', 'approve', 'prepare']);

    if (isQuestion) {
      return _Analysis(
        understanding:
            'This reads like a direct question rather than a request to take '
            'action, so I looked into it and answered without proposing anything.',
        directResult: ActionResult(
          summary: 'Here is what I found for: "${_truncate(rawText)}".',
          detail:
              'In a connected build this would draw on your real evidence '
              '(mail, documents, records) rather than mock data.',
        ),
      );
    }

    // connectionId == null means the request doesn't hinge on any one
    // specific service, so there is nothing to gate on.
    String? connectionId;
    String targetService;
    String verb;
    ActionImpact impact;

    if (has(['mail', 'email', 'reply', 'inbox'])) {
      connectionId = 'gmail';
      targetService = 'Gmail';
      verb = 'Draft a reply for';
      impact = has(['send']) ? ActionImpact.sensitive : ActionImpact.notable;
    } else if (has(['meeting', 'schedule', 'calendar', 'reschedule', 'book'])) {
      connectionId = 'calendar';
      targetService = 'Calendar';
      verb = 'Propose scheduling for';
      impact = ActionImpact.notable;
    } else if (has(['document', 'note', 'order', 'draft', 'renew', 'submit', 'extend'])) {
      connectionId = 'drafting';
      targetService = 'Institutional Drafting';
      verb = 'Prepare a draft for';
      impact = has(['submit', 'send', 'order']) ? ActionImpact.sensitive : ActionImpact.notable;
    } else if (has(['roster', 'sheet', 'record', 'students', 'list'])) {
      connectionId = 'sheets';
      targetService = 'Google Sheets';
      verb = 'Compile a summary for';
      impact = ActionImpact.routine;
    } else {
      targetService = 'your connected services';
      verb = 'Work on';
      impact = ActionImpact.routine;
    }

    // Respect the current connection state: URI does not pretend it can
    // proceed with a service that isn't authorized.
    if (connectionId != null) {
      final connection = _findConnection(connectionId);
      if (connection != null && connection.status != ConnectionStatus.connected) {
        return _Analysis(
          understanding:
              'This would need ${connection.name}, which ${connection.status == ConnectionStatus.needsAuthorization ? 'needs to be reconnected' : "isn't connected"} '
              'right now — so rather than guessing, I stopped here instead of proposing something I can\'t actually do.',
          requiredConnectionId: connection.id,
          requiredConnectionName: connection.name,
        );
      }
    }

    final excerpt = _truncate(rawText, 64);

    return _Analysis(
      understanding:
          'I understand you want help with: "$excerpt". Before doing '
          'anything in $targetService, here is what I am proposing.',
      proposedAction: ProposedAction(
        title: '$verb: $excerpt',
        description:
            'Based on your request, I would use $targetService to carry '
            'this out, then let you review the result before it is treated '
            'as final.',
        targetService: targetService,
        impact: impact,
      ),
    );
  }

  String _resultDetailFor(ProposedAction action) {
    return 'This is placeholder output — in a connected build, the result '
        'would come back from the real ${action.targetService} action, '
        'reported by the runtime rather than assumed by this screen.';
  }

  String _truncate(String text, [int maxLength = 48]) {
    final trimmed = text.trim();
    if (trimmed.length <= maxLength) return trimmed;
    return '${trimmed.substring(0, maxLength).trimRight()}…';
  }

  String _lowerFirst(String text) {
    if (text.isEmpty) return text;
    return text[0].toLowerCase() + text.substring(1);
  }
}

class _Analysis {
  _Analysis({
    required this.understanding,
    this.proposedAction,
    this.directResult,
    this.requiredConnectionId,
    this.requiredConnectionName,
  });

  final String understanding;
  final ProposedAction? proposedAction;
  final ActionResult? directResult;
  final String? requiredConnectionId;
  final String? requiredConnectionName;

  bool get isBlockedByConnection => requiredConnectionId != null;
}

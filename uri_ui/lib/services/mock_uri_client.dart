import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/memory_entry.dart';
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

  /// M22.9 (§0.3): a fixed, non-secret stand-in token — good enough for
  /// [SessionStore] persistence to exercise the same code path
  /// [HttpUriClient] does, with no real backend involved.
  @override
  String? get authToken => _username == null ? null : 'mock-token-$_username';

  @override
  void restoreSession({required String token, required String username}) {
    _username = username;
  }

  /// Test hook: set to false to make the next [validateSession] call
  /// behave like a backend that has rejected the token (expired/
  /// invalid), which also logs this mock out - matching
  /// [HttpUriClient]'s real behaviour so AppState tests can exercise
  /// both outcomes without a real backend.
  bool nextValidateSessionResult = true;

  @override
  Future<bool> validateSession() async {
    if (_username == null) return false;
    if (!nextValidateSessionResult) {
      _username = null;
      return false;
    }
    return true;
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
  Future<ConnectionCheckResult> checkConnection({String? addressOverride}) async {
    await _latency(const Duration(milliseconds: 80));
    return const ConnectionCheckResult.reachable();
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
  Future<ConnectionAuthorizeOutcome> authorizeConnection(String connectionId) async {
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
    return ConnectionAuthorizeOutcome(connection: updated, explanation: 'Connected.');
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
  Future<UriTurn> ask(String text, {String? turnId}) async {
    await _latency();
    final id = turnId ?? _nextId('turn');
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

  // ---------------------------------------------------------------
  // Memory
  // ---------------------------------------------------------------

  final List<MemoryEntry> _memories = <MemoryEntry>[];

  @override
  Future<List<MemoryEntry>> listMemory() async {
    await _latency();
    return List.unmodifiable(_memories);
  }

  @override
  Future<MemoryEntry> addMemory({
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    await _latency();
    if (content.trim().isEmpty) {
      throw const MemoryWriteException('Content cannot be empty.');
    }
    final now = DateTime.now().toIso8601String();
    final entry = MemoryEntry(
      memoryId: _nextId('mem'),
      category: category,
      consent: 'user_provided',
      content: content,
      confidence: confidence,
      notes: notes,
      status: 'active',
      createdAt: now,
      updatedAt: now,
    );
    _memories.add(entry);
    return entry;
  }

  @override
  Future<bool> deleteMemory(String memoryId) async {
    await _latency();
    final before = _memories.length;
    _memories.removeWhere((m) => m.memoryId == memoryId);
    return _memories.length != before;
  }

  @override
  Future<MemoryEntry> updateMemory({
    required String memoryId,
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    await _latency();
    if (content.trim().isEmpty) {
      throw const MemoryWriteException('Content cannot be empty.');
    }
    final index = _memories.indexWhere((m) => m.memoryId == memoryId);
    if (index == -1) {
      throw const MemoryWriteException('Memory not found.');
    }
    final existing = _memories[index];
    final updated = MemoryEntry(
      memoryId: existing.memoryId,
      category: category,
      consent: existing.consent,
      content: content,
      confidence: confidence,
      notes: notes,
      status: existing.status,
      createdAt: existing.createdAt,
      updatedAt: DateTime.now().toIso8601String(),
    );
    _memories[index] = updated;
    return updated;
  }

  // M18: session id + history + memory-confirmation stand-ins for tests
  // and offline development. HttpUriClient never delegates here.
  String _sessionId = 'mock-session';

  @override
  String get sessionId => _sessionId;

  @override
  void setSessionId(String sessionId) {
    _sessionId = sessionId;
  }

  @override
  Future<MemoryEntry?> confirmMemory(String memoryId, {String? content}) async {
    await _latency();
    final index = _memories.indexWhere((m) => m.memoryId == memoryId);
    if (index == -1) return null;
    final existing = _memories[index];
    final updated = MemoryEntry(
      memoryId: existing.memoryId,
      category: existing.category,
      consent: 'user_confirmed',
      content: content ?? existing.content,
      confidence: existing.confidence,
      notes: existing.notes,
      status: 'CONFIRMED',
      createdAt: existing.createdAt,
      updatedAt: DateTime.now().toIso8601String(),
    );
    _memories[index] = updated;
    return updated;
  }

  @override
  Future<bool> rejectMemory(String memoryId) async {
    await _latency();
    final before = _memories.length;
    _memories.removeWhere((m) => m.memoryId == memoryId);
    return _memories.length != before;
  }

  final Map<String, List<UriTurn>> _history = <String, List<UriTurn>>{};

  @override
  Future<List<ConversationSummary>> listHistory() async {
    await _latency();
    return _history.entries
        .map(
          (entry) => ConversationSummary(
            sessionId: entry.key,
            turnCount: entry.value.length,
            preview: entry.value.isEmpty ? '' : entry.value.first.userText,
            lastActivity: DateTime.now().toIso8601String(),
          ),
        )
        .toList();
  }

  @override
  Future<List<UriTurn>> getHistory(String sessionId) async {
    await _latency();
    return List.unmodifiable(_history[sessionId] ?? const []);
  }

  @override
  Future<bool> deleteHistory(String sessionId) async {
    await _latency();
    return _history.remove(sessionId) != null;
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

  @override
  Future<UriIdentity?> getIdentity() async {
    await _latency();
    return const UriIdentity(userId: 'mock-user', deviceId: 'mock-device');
  }

  // A couple of seeded, realistic-shaped entries (mirroring
  // capability_registry.py's real vocabulary) so widget tests/demo runs
  // against this mock have something to render - real capability data
  // always comes from HttpUriClient's GET /capabilities; this is never
  // read by HttpUriClient.
  @override
  Future<List<CapabilityInfo>> listCapabilities() async {
    await _latency();
    return const [
      CapabilityInfo(
        id: 'draft_institutional_note',
        description: 'Draft a note in NIT Sikkim\'s institutional style.',
        status: 'implemented',
        availability: 'available',
        approvalRequirement: 'required',
        risk: 'low',
      ),
      CapabilityInfo(
        id: 'pc_system_optimization',
        description: 'Optimize this PC\'s performance settings.',
        status: 'not_implemented',
        availability: 'unavailable',
        approvalRequirement: 'required',
        risk: 'high',
        gapReason: 'not_implemented',
      ),
    ];
  }

  // M22.2/M22.3 UI parity stand-ins - a single fixed ADMIN account
  // (first-account-becomes-ADMIN, matching the real backend's own
  // bootstrap rule) with one other device already logged in, so the
  // Devices section and role/tier controls have something real to
  // render offline/in widget tests. HttpUriClient never delegates here.
  String _experienceTier = 'BASIC';
  String _mode = 'office';
  final List<DeviceSession> _devices = <DeviceSession>[
    const DeviceSession(
      deviceId: 'mock-device',
      sessionCount: 1,
      mostRecentExpiresAt: null,
    ),
  ];

  @override
  Future<AccountInfo?> getAccountInfo() async {
    await _latency();
    if (_username == null) return null;
    return AccountInfo(
      userId: 'mock-user',
      username: _username,
      role: 'ADMIN',
      experienceTier: _experienceTier,
      deviceId: 'mock-device',
      runtimeDeviceId: 'mock-runtime-device',
    );
  }

  @override
  Future<bool> setExperienceTier(String tier) async {
    await _latency();
    _experienceTier = tier;
    return true;
  }

  @override
  Future<ModeInfo?> getModeInfo() async =>
      ModeInfo(mode: _mode, validModes: const ['admin', 'diagnostic', 'office']);

  @override
  Future<bool> setMode(String mode) async {
    if (!const {'office', 'diagnostic', 'admin'}.contains(mode)) return false;
    _mode = mode;
    return true;
  }

  @override
  Future<UsageLimitStatus?> getUsageLimitStatus() async =>
      const UsageLimitStatus(warning: false, ceilingReached: false);

  @override
  Future<List<DeviceSession>> listDevices() async {
    await _latency();
    return List.unmodifiable(_devices);
  }

  @override
  Future<int> revokeDevice(String deviceId) async {
    await _latency();
    final index = _devices.indexWhere((d) => d.deviceId == deviceId);
    if (index == -1) return 0;
    final revoked = _devices[index].sessionCount;
    _devices.removeAt(index);
    return revoked;
  }

  @override
  Future<ModelStatus?> getModelStatus() async {
    await _latency();
    return const ModelStatus(
      providerName: 'Ollama',
      modelName: 'qwen3:14b',
      location: 'local',
      available: true,
    );
  }

  @override
  Future<bool> syncPreferences({
    required String communicationStyle,
    required String autonomyLevel,
    required List<String> focusAreas,
  }) async {
    // Deliberately NO _latency() here, unlike every other mock method.
    // AppState.updatePreferences is routinely awaited by tests BEFORE
    // the first pumpWidget (see ask_uri_flow_test's
    // pumpPostOnboardingApp). A simulated delay at that point is a
    // timer that fake-async time never advances - the await then never
    // completes and the test hangs indefinitely, without even its own
    // timeout firing. Returning synchronously keeps the mock faithful
    // (it still reports success/failure the same way) without
    // introducing a timer no one can pump.
    return true;
  }

  // M16: in-memory attachments so the mock (used by widget tests and
  // offline development) exercises the same interface as the real
  // client. This is explicitly test/dev scaffolding — HttpUriClient
  // never delegates here.
  final List<Attachment> _attachments = <Attachment>[];
  final Map<String, List<int>> _attachmentBytes = <String, List<int>>{};

  @override
  Future<Attachment> uploadAttachment({
    required String filename,
    required List<int> bytes,
  }) async {
    await _latency();

    if (bytes.isEmpty) {
      throw const AttachmentException('The file is empty.');
    }

    final attachment = Attachment(
      fileId: _nextId('file'),
      filename: filename,
      mediaType: 'application/octet-stream',
      sizeBytes: bytes.length,
    );
    _attachments.add(attachment);
    _attachmentBytes[attachment.fileId] = bytes;
    return attachment;
  }

  @override
  Future<List<Attachment>> listAttachments() async {
    await _latency();
    return List.unmodifiable(_attachments);
  }

  @override
  Future<bool> deleteAttachment(String fileId) async {
    await _latency();
    final before = _attachments.length;
    _attachments.removeWhere((a) => a.fileId == fileId);
    _attachmentBytes.remove(fileId);
    return _attachments.length != before;
  }

  @override
  Future<List<int>> downloadAttachmentContent(String fileId) async {
    await _latency();
    final bytes = _attachmentBytes[fileId];
    if (bytes == null) {
      throw const AttachmentException('This attachment no longer exists.');
    }
    return bytes;
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

  // ---------------------------------------------------------------
  // M22.4: Admin capability grant management mock
  // ---------------------------------------------------------------

  final Map<String, List<String>> _mockUserGrants = <String, List<String>>{};

  @override
  Future<List<AdminUserEntry>> listAdminUsers() async {
    return const [
      AdminUserEntry(userId: 'mock-user', username: 'demo-user', role: 'ADMIN'),
      AdminUserEntry(userId: 'user-secondary', username: 'student-user', role: 'USER'),
    ];
  }

  @override
  Future<UserGrantsInfo> getUserGrants(String userId) async {
    const allCaps = ['draft_institutional_note', 'pc_system_optimization'];
    final grants = _mockUserGrants[userId] ?? List<String>.from(allCaps);
    return UserGrantsInfo(
      userId: userId,
      grants: grants,
      registryCeiling: allCaps,
    );
  }

  @override
  Future<bool> updateUserGrants(String userId, List<String> grants) async {
    _mockUserGrants[userId] = List<String>.from(grants);
    return true;
  }

  // ---------------------------------------------------------------
  // M22.5: Provider registry and key management mock
  // ---------------------------------------------------------------

  final Map<String, String> _mockProviderKeysLastFour = <String, String>{};
  final Map<String, Map<String, String>> _mockProviderOverrides =
      <String, Map<String, String>>{};

  @override
  Future<List<ProviderEntry>> listProviders() async {
    return [
      ProviderEntry(
        providerId: 'ollama',
        displayName: 'Ollama (Local)',
        adapter: 'ollama',
        baseUrl: _mockProviderOverrides['ollama']?['base_url'] ??
            'http://localhost:11434',
        configured: true,
        lastFour: null,
        available: true,
      ),
      ProviderEntry(
        providerId: 'openai',
        displayName: 'OpenAI',
        adapter: 'openai_compatible',
        baseUrl: _mockProviderOverrides['openai']?['base_url'] ??
            'https://api.openai.com/v1',
        configured: _mockProviderKeysLastFour.containsKey('openai'),
        lastFour: _mockProviderKeysLastFour['openai'],
        available: true,
      ),
      ProviderEntry(
        providerId: 'groq',
        displayName: 'Groq',
        adapter: 'openai_compatible',
        baseUrl: _mockProviderOverrides['groq']?['base_url'] ??
            'https://api.groq.com/openai/v1',
        configured: _mockProviderKeysLastFour.containsKey('groq'),
        lastFour: _mockProviderKeysLastFour['groq'],
        available: true,
      ),
      ProviderEntry(
        providerId: 'anthropic',
        displayName: 'Anthropic',
        adapter: 'openai_compatible',
        baseUrl: _mockProviderOverrides['anthropic']?['base_url'] ??
            'https://api.anthropic.com/v1',
        configured: _mockProviderKeysLastFour.containsKey('anthropic'),
        lastFour: _mockProviderKeysLastFour['anthropic'],
        available: false,
      ),
    ];
  }

  @override
  Future<ProviderKeyResult?> submitProviderKey(
    String providerId,
    String apiKey,
  ) async {
    final lastFour =
        apiKey.length >= 4 ? apiKey.substring(apiKey.length - 4) : '****';
    _mockProviderKeysLastFour[providerId] = lastFour;
    return ProviderKeyResult(
      providerId: providerId,
      configured: true,
      lastFour: lastFour,
    );
  }

  @override
  Future<bool> updateProviderConfig(
    String providerId, {
    String? baseUrl,
    String? model,
  }) async {
    final current =
        _mockProviderOverrides[providerId] ?? <String, String>{};
    if (baseUrl != null) current['base_url'] = baseUrl;
    if (model != null) current['model'] = model;
    _mockProviderOverrides[providerId] = current;
    return true;
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

String _lowerFirst(String text) {
  if (text.isEmpty) return text;
  return text[0].toLowerCase() + text.substring(1);
}

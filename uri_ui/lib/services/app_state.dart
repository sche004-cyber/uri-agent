import 'package:flutter/foundation.dart';

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/user_preferences.dart';
import '../models/uri_turn.dart';
import 'preferences_store.dart';
import 'server_address_store.dart';
import 'uri_client.dart' show AuthOutcome, HomeSummary, UriClient;

/// Prototype 2 (multi-client + runtime awareness): the result of the
/// last [AppState.checkConnection] call. Deliberately a separate type
/// from models/connection.dart's ConnectionStatus (OAuth-style external
/// service connections, e.g. Gmail) - this is about reaching the URI
/// backend itself, an unrelated concern.
enum BackendConnectionStatus { unknown, reachable, unreachable }

/// App-wide, UI-only state. Holds nothing that belongs to the runtime
/// (no facts, no evidence, no authorization decisions) — only what the
/// interface needs to render, and what the user has told this client
/// about their preferences (persisted locally on-device via
/// [PreferencesStore] — not a backend, nothing sensitive).
class AppState extends ChangeNotifier {
  AppState({
    required UriClient client,
    PreferencesStore? preferencesStore,
    ServerAddressStore? serverAddressStore,
    UserPreferences? initialPreferences,
  }) : _client = client,
       _preferencesStore = preferencesStore ?? PreferencesStore(),
       _serverAddressStore = serverAddressStore ?? ServerAddressStore(),
       preferences = initialPreferences ?? const UserPreferences.initial();

  final UriClient _client;
  final PreferencesStore _preferencesStore;
  final ServerAddressStore _serverAddressStore;

  UserPreferences preferences;

  final List<UriTurn> conversation = <UriTurn>[];
  List<ServiceConnection> connections = <ServiceConnection>[];
  List<ActivityEvent> activity = <ActivityEvent>[];
  List<TaskItem> tasks = <TaskItem>[];
  HomeSummary? homeSummary;

  bool isLoadingHome = false;
  bool isSendingAsk = false;
  bool isLoadingTasks = false;

  // ---------------------------------------------------------------
  // Prototype 1 — multi-user identity + login foundation.
  // ---------------------------------------------------------------

  bool get isAuthenticated => _client.isAuthenticated;
  String? get currentUsername => _client.currentUsername;

  Future<AuthOutcome> login(String username, String password) async {
    final outcome = await _client.login(username, password);
    notifyListeners();
    return outcome;
  }

  Future<AuthOutcome> signup(String username, String password) async {
    final outcome = await _client.signup(username, password);
    notifyListeners();
    return outcome;
  }

  /// Logs out and clears every piece of state this client fetched
  /// under the previous login - a returning/different user must never
  /// still see the prior user's conversation, tasks, or home summary
  /// left over in this in-memory UI state.
  Future<void> logout() async {
    await _client.logout();
    conversation.clear();
    tasks.clear();
    homeSummary = null;
    hasLoadedActivity = false;
    notifyListeners();
  }

  // ---------------------------------------------------------------
  // Prototype 2 — multi-client + runtime awareness.
  // ---------------------------------------------------------------

  String get baseUrl => _client.baseUrl;

  BackendConnectionStatus connectionStatus = BackendConnectionStatus.unknown;

  /// A short diagnostic reason for the last unreachable result (the
  /// underlying exception message or HTTP status - see
  /// ConnectionCheckResult.detail) - null on success, or when nothing
  /// has been tested yet. Purely informational, shown alongside
  /// [connectionStatus] rather than replacing it, so the badge itself
  /// stays exactly as simple as before.
  String? lastConnectionErrorDetail;

  /// Bootstrap fix: true once a backend address has actually been
  /// configured on this device - either recovered from a prior launch
  /// (see [loadPersistedServerAddress]) or explicitly applied via
  /// [setBaseUrl] this session. Before that, the compiled-in default
  /// (`http://localhost:8000`, meaningless on a phone) is all any
  /// client has, and login/signup can never succeed against it - see
  /// screens/bootstrap/bootstrap_screen.dart, which main.dart shows
  /// instead of the login screen until this becomes true. Login itself
  /// is completely unaffected: this only ever gates which screen is
  /// shown, never any backend call's authorization.
  bool hasConfiguredServerAddress = false;

  /// Loads any previously persisted backend address for this device,
  /// applying it to [_client] before first use. Call once, alongside
  /// [loadPersistedPreferences], before the first frame - a phone that
  /// was already pointed at its PC must not silently fall back to
  /// localhost on relaunch.
  Future<void> loadPersistedServerAddress() async {
    final saved = await _serverAddressStore.load();
    if (saved != null && saved.isNotEmpty) {
      _client.setBaseUrl(saved);
      hasConfiguredServerAddress = true;
      notifyListeners();
    }
  }

  /// Repoints this client at a different backend address and persists
  /// it on-device for next launch. Does not itself verify reachability
  /// - call [checkConnection] afterwards for that, exactly as a human
  /// tester would after changing this in Settings.
  Future<void> setBaseUrl(String url) async {
    _client.setBaseUrl(url);
    connectionStatus = BackendConnectionStatus.unknown;
    hasConfiguredServerAddress = true;
    notifyListeners();
    await _serverAddressStore.save(url);
  }

  /// Explicit "Test connection" action - never called automatically/on
  /// a timer, so reconnect/disconnect behaviour stays predictable and
  /// visible rather than silently polling in the background.
  ///
  /// [addressOverride], when given, is tested exactly as typed instead
  /// of [baseUrl] - this is what lets Settings test whatever address is
  /// currently in the text field even before [setBaseUrl]/Save has
  /// been pressed. This never applies or persists that address itself;
  /// call [setBaseUrl] separately for that, exactly as before.
  Future<bool> checkConnection({String? addressOverride}) async {
    final result = await _client.checkConnection(addressOverride: addressOverride);
    connectionStatus = result.reachable
        ? BackendConnectionStatus.reachable
        : BackendConnectionStatus.unreachable;
    lastConnectionErrorDetail = result.detail;
    notifyListeners();
    return result.reachable;
  }

  /// Loads any previously persisted preferences from this device,
  /// replacing whatever [preferences] was constructed with. Call once,
  /// before the first frame that depends on onboarding status.
  Future<void> loadPersistedPreferences() async {
    preferences = await _preferencesStore.load();
    notifyListeners();
  }

  /// Applies and persists a preferences update — used both by onboarding
  /// completion and by later edits from Settings.
  Future<void> updatePreferences(UserPreferences updated) async {
    preferences = updated;
    notifyListeners();
    await _preferencesStore.save(updated);
  }

  Future<void> loadHome() async {
    isLoadingHome = true;
    notifyListeners();
    homeSummary = await _client.loadHomeSummary();
    isLoadingHome = false;
    notifyListeners();
  }

  bool hasLoadedActivity = false;

  Future<void> loadConnections() async {
    connections = await _client.listConnections();
    notifyListeners();
  }

  Future<void> loadActivity() async {
    activity = await _client.listActivity();
    hasLoadedActivity = true;
    notifyListeners();
  }

  Future<void> authorizeConnection(String id) async {
    final updated = await _client.authorizeConnection(id);
    _replaceConnection(updated);
    notifyListeners();
  }

  Future<void> disconnectConnection(String id) async {
    final updated = await _client.disconnectConnection(id);
    _replaceConnection(updated);
    notifyListeners();
  }

  void _replaceConnection(ServiceConnection updated) {
    final index = connections.indexWhere((c) => c.id == updated.id);
    if (index == -1) {
      connections = [...connections, updated];
    } else {
      connections = [...connections]..[index] = updated;
    }
  }

  /// Fix (chat UX): the user's message and a persistent URI
  /// processing state must both appear the instant this is called,
  /// not only once the request resolves - a placeholder turn (stage
  /// [TurnStage.understanding], an existing, previously-unused stage
  /// whose own doc comment already means exactly "URI is processing,
  /// nothing decided yet") is added to [conversation] synchronously,
  /// before the network call is even made. Once [_client.ask] resolves
  /// (success, capability gap, or failure), that same turn is updated
  /// in place - see [_replacePendingTurn] - never appended as a second,
  /// separate entry.
  Future<UriTurn> ask(String text) async {
    final pendingId = _generateTurnId();

    conversation.add(
      UriTurn(
        id: pendingId,
        userText: text,
        timestamp: DateTime.now(),
        stage: TurnStage.understanding,
      ),
    );
    isSendingAsk = true;
    notifyListeners();

    final turn = await _client.ask(text, turnId: pendingId);
    _replacePendingTurn(pendingId, turn);
    isSendingAsk = false;
    notifyListeners();
    return turn;
  }

  static String _generateTurnId() =>
      'turn-${DateTime.now().microsecondsSinceEpoch}';

  /// Finds the pending placeholder by [pendingId] - never by
  /// [updated]'s own id, which can legitimately differ from it: an
  /// awaiting-approval turn's id becomes the backend's real action_id
  /// (see HttpUriClient._turnFromResponse), not the client-generated
  /// placeholder id. Keying off [pendingId] is what keeps this a
  /// single, updated-in-place card in both cases rather than leaving a
  /// stuck "Understanding" placeholder behind a second, duplicate
  /// entry.
  void _replacePendingTurn(String pendingId, UriTurn updated) {
    final index = conversation.indexWhere((t) => t.id == pendingId);
    if (index == -1) {
      conversation.add(updated);
    } else {
      conversation[index] = updated;
    }
    notifyListeners();
  }

  Future<void> approve(String turnId) async {
    _updateTurn(turnId, (t) => t.copyWith(stage: TurnStage.executing));
    final updated = await _client.approve(turnId);
    _replaceTurn(updated);
  }

  Future<void> cancel(String turnId) async {
    final updated = await _client.cancel(turnId);
    _replaceTurn(updated);
  }

  void _updateTurn(String turnId, UriTurn Function(UriTurn) transform) {
    final index = conversation.indexWhere((t) => t.id == turnId);
    if (index == -1) return;
    conversation[index] = transform(conversation[index]);
    notifyListeners();
  }

  void _replaceTurn(UriTurn updated) {
    final index = conversation.indexWhere((t) => t.id == updated.id);
    if (index == -1) {
      conversation.add(updated);
    } else {
      conversation[index] = updated;
    }
    notifyListeners();
  }

  Future<void> loadTasks() async {
    isLoadingTasks = true;
    notifyListeners();
    tasks = await _client.listTasks();
    isLoadingTasks = false;
    notifyListeners();
  }

  /// Approves a task by id (see [TaskItem.id]) — a separate flow from
  /// [approve] (which operates on the current Ask URI conversation)
  /// since a task may belong to a different session this client never
  /// held a [UriTurn] for. Reloads [tasks] from the backend afterwards
  /// so the list reflects reality rather than being guessed at
  /// client-side.
  Future<void> approveTask(String actionId) async {
    await _client.approve(actionId);
    await loadTasks();
  }

  Future<void> cancelTask(String actionId) async {
    await _client.cancel(actionId);
    await loadTasks();
  }
}

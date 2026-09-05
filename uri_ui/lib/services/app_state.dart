import 'package:flutter/foundation.dart';

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/user_preferences.dart';
import '../models/uri_turn.dart';
import 'preferences_store.dart';
import 'uri_client.dart' show AuthOutcome, HomeSummary, UriClient;

/// App-wide, UI-only state. Holds nothing that belongs to the runtime
/// (no facts, no evidence, no authorization decisions) — only what the
/// interface needs to render, and what the user has told this client
/// about their preferences (persisted locally on-device via
/// [PreferencesStore] — not a backend, nothing sensitive).
class AppState extends ChangeNotifier {
  AppState({
    required UriClient client,
    PreferencesStore? preferencesStore,
    UserPreferences? initialPreferences,
  }) : _client = client,
       _preferencesStore = preferencesStore ?? PreferencesStore(),
       preferences = initialPreferences ?? const UserPreferences.initial();

  final UriClient _client;
  final PreferencesStore _preferencesStore;

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

  Future<UriTurn> ask(String text) async {
    isSendingAsk = true;
    notifyListeners();
    final turn = await _client.ask(text);
    conversation.add(turn);
    isSendingAsk = false;
    notifyListeners();
    return turn;
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

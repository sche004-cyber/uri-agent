import 'package:flutter/material.dart' show ThemeMode;
import 'package:flutter/foundation.dart';

import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/memory_entry.dart';
import '../models/task_item.dart';
import '../models/user_preferences.dart';
import '../models/uri_turn.dart';
import 'preferences_store.dart';
import 'server_address_store.dart';
import 'theme_store.dart';
import 'uri_client.dart'
    show
        AccountInfo,
        AdminUserEntry,
        Attachment,
        AttachmentException,
        AuthOutcome,
        CapabilityInfo,
        ConversationSummary,
        DeviceSession,
        HomeSummary,
        MemoryWriteException,
        ModelStatus,
        ProviderEntry,
        ProviderKeyResult,
        UriClient,
        UriIdentity,
        UserGrantsInfo;

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
    ThemeStore? themeStore,
    UserPreferences? initialPreferences,
  }) : _client = client,
       _preferencesStore = preferencesStore ?? PreferencesStore(),
       _serverAddressStore = serverAddressStore ?? ServerAddressStore(),
       _themeStore = themeStore ?? ThemeStore(),
       preferences = initialPreferences ?? const UserPreferences.initial();

  final UriClient _client;
  final PreferencesStore _preferencesStore;
  final ServerAddressStore _serverAddressStore;
  final ThemeStore _themeStore;

  UserPreferences preferences;

  /// Settings → Appearance. Defaults to following the OS until the
  /// user picks otherwise; persisted on-device only (see [ThemeStore])
  /// — never sent to the backend, which has no concept of how any
  /// client renders itself.
  ThemeMode themeMode = ThemeMode.system;

  Future<void> loadPersistedThemeMode() async {
    themeMode = await _themeStore.load();
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    if (themeMode == mode) return;
    themeMode = mode;
    notifyListeners();
    await _themeStore.save(mode);
  }

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
    // M16: attachments are conversation state too - a different user
    // must never see the previous user's attached filenames.
    attachments = <Attachment>[];
    attachmentError = null;
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
  ///
  /// M16: also pushes them to the backend profile, which is what
  /// personalization_context feeds the Brain each turn. Before this,
  /// preferences lived only on-device and the Brain never saw them.
  /// The device-local save still happens first and independently: it
  /// is what survives a restart, and it must not depend on the backend
  /// being reachable.
  Future<void> updatePreferences(UserPreferences updated) async {
    preferences = updated;
    notifyListeners();
    await _preferencesStore.save(updated);

    await _client.syncPreferences(
      communicationStyle: updated.communicationStyle.name,
      autonomyLevel: updated.autonomyLevel.name,
      focusAreas: updated.focusAreas,
    );
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

  /// Returns the backend's own explanation of what happened/what's
  /// needed, so the caller can show it to the user — tapping
  /// Connect/Reconnect must never be a silent no-op (see
  /// UriClient.authorizeConnection).
  Future<String> authorizeConnection(String id) async {
    final outcome = await _client.authorizeConnection(id);
    _replaceConnection(outcome.connection);
    notifyListeners();
    return outcome.explanation;
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

    // Attachments stick to the turn they were sent with - like a chat
    // bubble's own attachment, not a standing part of the composer -
    // so the snapshot is taken and the composer cleared right here,
    // the moment the message is sent, not once the response arrives.
    // The backend is untouched: it still keeps the file scoped to this
    // session (see FileStore) so URI can reference it in a later turn
    // even though its chip no longer shows as staged in the composer.
    final sentAttachments = List<Attachment>.unmodifiable(attachments);
    attachments = <Attachment>[];

    conversation.add(
      UriTurn(
        id: pendingId,
        userText: text,
        timestamp: DateTime.now(),
        stage: TurnStage.understanding,
        attachments: sentAttachments,
      ),
    );
    isSendingAsk = true;
    notifyListeners();

    final response = await _client.ask(text, turnId: pendingId);
    final turn = response.copyWith(attachments: sentAttachments);
    _replacePendingTurn(pendingId, turn);
    isSendingAsk = false;
    notifyListeners();
    return turn;
  }

  // ---------------------------------------------------------------
  // Memory (Settings → Memory) — every fact URI holds about the user.
  // ---------------------------------------------------------------

  List<MemoryEntry> memories = <MemoryEntry>[];
  bool hasLoadedMemory = false;
  bool isSavingMemory = false;
  String? memoryError;

  Future<void> loadMemory() async {
    memories = await _client.listMemory();
    hasLoadedMemory = true;
    notifyListeners();
  }

  Future<void> addMemory({
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    isSavingMemory = true;
    memoryError = null;
    notifyListeners();
    try {
      final entry = await _client.addMemory(
        category: category,
        content: content,
        confidence: confidence,
        notes: notes,
      );
      memories = [...memories, entry];
    } on MemoryWriteException catch (error) {
      memoryError = error.message;
    } catch (_) {
      memoryError = 'This memory could not be saved.';
    } finally {
      isSavingMemory = false;
      notifyListeners();
    }
  }

  /// Whole-entry edit of an existing memory (distinct from [addMemory],
  /// which creates a new one). Same error-handling shape as
  /// [addMemory]: a rejected edit surfaces the backend's real reason via
  /// [memoryError] rather than throwing into the caller.
  Future<void> updateMemory({
    required String memoryId,
    required String category,
    required String content,
    double? confidence,
    String? notes,
  }) async {
    isSavingMemory = true;
    memoryError = null;
    notifyListeners();
    try {
      final updated = await _client.updateMemory(
        memoryId: memoryId,
        category: category,
        content: content,
        confidence: confidence,
        notes: notes,
      );
      final index = memories.indexWhere((m) => m.memoryId == memoryId);
      if (index != -1) {
        memories = [...memories]..[index] = updated;
      } else {
        memories = [...memories, updated];
      }
    } on MemoryWriteException catch (error) {
      memoryError = error.message;
    } catch (_) {
      memoryError = 'This memory could not be updated.';
    } finally {
      isSavingMemory = false;
      notifyListeners();
    }
  }

  Future<void> deleteMemory(String memoryId) async {
    final removed = await _client.deleteMemory(memoryId);
    if (removed) {
      memories = memories.where((m) => m.memoryId != memoryId).toList(growable: false);
      notifyListeners();
    }
  }

  void clearMemoryError() {
    if (memoryError == null) return;
    memoryError = null;
    notifyListeners();
  }

  // ---------------------------------------------------------------
  // Identity (Settings → Profile / Diagnostics / About).
  // ---------------------------------------------------------------

  UriIdentity? identity;
  bool hasLoadedIdentity = false;

  Future<void> loadIdentity() async {
    identity = await _client.getIdentity();
    hasLoadedIdentity = true;
    notifyListeners();
  }

  // ---------------------------------------------------------------
  // M22.2/M22.3: role, experience tier, and device/session
  // management (Settings → Profile). role is a privilege the backend
  // alone decides (USER|ADMIN) - this client only ever displays it,
  // never uses it to gate anything itself beyond deciding whether an
  // ADMIN-only action's control is even offered (the backend's own
  // authorization check is what actually protects the action; see
  // connections_screen.dart). experience_tier remains a zero-authority
  // display preference, exactly as the backend treats it - nothing in
  // this class ever branches on it for anything other than which
  // Preferences UI to show.
  // ---------------------------------------------------------------

  AccountInfo? accountInfo;
  bool hasLoadedAccountInfo = false;

  Future<void> loadAccountInfo() async {
    accountInfo = await _client.getAccountInfo();
    hasLoadedAccountInfo = true;
    notifyListeners();
  }

  /// True only once the backend has actually said so (see
  /// [AccountInfo.isAdmin]) - false (never assumed true) before
  /// [loadAccountInfo] resolves, so an ADMIN-only control never
  /// flashes visible-then-hidden, only hidden-then-visible.
  bool get isAdmin => accountInfo?.isAdmin ?? false;

  /// Direct client reference for admin screens.
  UriClient get client => _client;

  Future<List<AdminUserEntry>> listAdminUsers() => _client.listAdminUsers();

  Future<UserGrantsInfo> getUserGrants(String userId) =>
      _client.getUserGrants(userId);

  Future<bool> updateUserGrants(String userId, List<String> grants) =>
      _client.updateUserGrants(userId, grants);

  // ---------------------------------------------------------------
  // M22.5: Provider registry and key management
  // ---------------------------------------------------------------

  Future<List<ProviderEntry>> listProviders() => _client.listProviders();

  Future<ProviderKeyResult?> submitProviderKey(
    String providerId,
    String apiKey,
  ) =>
      _client.submitProviderKey(providerId, apiKey);

  Future<bool> updateProviderConfig(
    String providerId, {
    String? baseUrl,
    String? model,
  }) =>
      _client.updateProviderConfig(providerId, baseUrl: baseUrl, model: model);


  Future<bool> setExperienceTier(String tier) async {
    final accepted = await _client.setExperienceTier(tier);
    if (accepted) {
      await loadAccountInfo();
    }
    return accepted;
  }

  List<DeviceSession> devices = <DeviceSession>[];
  bool hasLoadedDevices = false;

  Future<void> loadDevices() async {
    devices = await _client.listDevices();
    hasLoadedDevices = true;
    notifyListeners();
  }

  /// Logs out every session on one of the CALLER's OWN devices (see
  /// UriClient.revokeDevice) - reloads the device list afterwards so it
  /// reflects reality rather than being guessed at client-side.
  Future<int> revokeDevice(String deviceId) async {
    final revoked = await _client.revokeDevice(deviceId);
    await loadDevices();
    return revoked;
  }

  // ---------------------------------------------------------------
  // Model/provider self-knowledge (Settings → Capabilities).
  // ---------------------------------------------------------------

  ModelStatus? modelStatus;
  bool hasLoadedModelStatus = false;

  Future<void> loadModelStatus() async {
    modelStatus = await _client.getModelStatus();
    hasLoadedModelStatus = true;
    notifyListeners();
  }

  // ---------------------------------------------------------------
  // M18: conversation history (list / resume / delete) and
  // Brain-proposed memory confirmation.
  // ---------------------------------------------------------------

  List<ConversationSummary> history = <ConversationSummary>[];
  bool hasLoadedHistory = false;

  Future<void> loadHistory() async {
    history = await _client.listHistory();
    hasLoadedHistory = true;
    notifyListeners();
  }

  /// Loads a past conversation's turns into the live conversation view
  /// and repoints the client at that session, so the next message the
  /// user sends continues it rather than starting a new one. Read-only
  /// reconstruction: nothing is re-run or re-proposed.
  Future<void> resumeSession(String sessionId) async {
    final turns = await _client.getHistory(sessionId);
    _client.setSessionId(sessionId);
    conversation
      ..clear()
      ..addAll(turns);
    notifyListeners();
  }

  Future<void> deleteHistory(String sessionId) async {
    final deleted = await _client.deleteHistory(sessionId);
    if (deleted) {
      history = history.where((h) => h.sessionId != sessionId).toList(growable: false);
      notifyListeners();
    }
  }

  /// M18: accept a URI-proposed (pending_confirmation) memory, optionally
  /// correcting its content. Refreshes the memory list on success.
  Future<void> confirmMemory(String memoryId, {String? content}) async {
    final confirmed = await _client.confirmMemory(memoryId, content: content);
    if (confirmed != null) {
      final index = memories.indexWhere((m) => m.memoryId == memoryId);
      if (index != -1) {
        memories = [...memories]..[index] = confirmed;
        notifyListeners();
      } else {
        await loadMemory();
      }
    }
  }

  Future<void> rejectMemory(String memoryId) async {
    final rejected = await _client.rejectMemory(memoryId);
    if (rejected) {
      memories = memories.where((m) => m.memoryId != memoryId).toList(growable: false);
      notifyListeners();
    }
  }

  // ---------------------------------------------------------------
  // M16: file attachments.
  //
  // Attachments belong to the conversation, not to a single message:
  // the backend scopes them by session_id and the Brain is shown that
  // they exist (see query_context's "attachments"), deciding for
  // itself whether to read one. [attachmentError] holds the backend's
  // real rejection reason so the UI can show why, never a silent
  // failure.
  // ---------------------------------------------------------------

  // M16: URI's real capability catalogue, loaded from the backend.
  // hasLoadedCapabilities distinguishes "not asked yet" from "asked
  // and got nothing" - the UI must not show an honest-looking empty
  // list before it has actually checked.
  List<CapabilityInfo> capabilities = <CapabilityInfo>[];
  bool hasLoadedCapabilities = false;

  Future<void> loadCapabilities() async {
    capabilities = await _client.listCapabilities();
    hasLoadedCapabilities = true;
    notifyListeners();
  }

  List<Attachment> attachments = <Attachment>[];
  bool isUploadingAttachment = false;
  String? attachmentError;

  Future<void> attachFile({
    required String filename,
    required List<int> bytes,
  }) async {
    isUploadingAttachment = true;
    attachmentError = null;
    notifyListeners();

    try {
      final attachment = await _client.uploadAttachment(
        filename: filename,
        bytes: bytes,
      );
      attachments = [...attachments, attachment];
    } on AttachmentException catch (error) {
      attachmentError = error.message;
    } catch (_) {
      attachmentError = 'The file could not be attached.';
    } finally {
      isUploadingAttachment = false;
      notifyListeners();
    }
  }

  Future<void> removeAttachment(String fileId) async {
    final removed = await _client.deleteAttachment(fileId);
    if (removed) {
      attachments = attachments
          .where((a) => a.fileId != fileId)
          .toList(growable: false);
      notifyListeners();
    }
  }

  /// Raw bytes of a file the user (or a past turn) attached, so the
  /// chat screen can let them open it back up and verify it's really
  /// what they think it is — a plain passthrough; the caller decides
  /// what "open" means on this platform.
  Future<List<int>> downloadAttachment(String fileId) =>
      _client.downloadAttachmentContent(fileId);

  void clearAttachmentError() {
    if (attachmentError == null) return;
    attachmentError = null;
    notifyListeners();
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

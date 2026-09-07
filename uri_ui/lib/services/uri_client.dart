import '../models/activity_event.dart';
import '../models/attachment.dart';
import '../models/connection.dart';
import '../models/memory_entry.dart';
import '../models/task_item.dart';
import '../models/uri_turn.dart';

export '../models/attachment.dart' show Attachment;

/// The boundary between this Flutter client and URI's runtime.
///
/// IMPORTANT — architecture boundary:
/// The URI Python runtime (uri_core/) does not currently expose an HTTP
/// or RPC API. Its only existing entry point
/// (`UriOrchestrator.process_user_input`) is called in-process by a
/// separate PyQt desktop prototype. This interface exists so the UI can
/// be built and reviewed now, against a shape modelled on that same
/// runtime contract (intent -> proposal -> approval -> execution
/// result), without inventing or wiring a real network API.
///
/// [MockUriClient] is the only implementation today. A future
/// `HttpUriClient` (or similar) can implement this same interface once
/// a real API exists, without any screen needing to change.
///
/// This interface deliberately does NOT expose reasoning, planning,
/// authorization, persistence, or execution mechanics — only the
/// request/response shapes a client is entitled to see. All of that
/// stays owned by the Python runtime.
abstract class UriClient {
  /// True once this client holds a token from a successful login/signup
  /// (see [login]/[signup]) that hasn't been [logout]-ed. Client
  /// identity (which device/install this is) stays entirely separate
  /// from this — see [HttpUriClient], which never mixes the two.
  bool get isAuthenticated;

  /// The username of the currently logged-in user, or null when
  /// [isAuthenticated] is false.
  String? get currentUsername;

  /// Creates a new account for [username]/[password] and logs in as it
  /// immediately on success — a fresh, isolated user_id is created
  /// server-side (see uri_core/core/user_accounts.py); this is
  /// prototype-only local authentication, not OAuth/Gmail/GitHub.
  Future<AuthOutcome> signup(String username, String password);

  /// Logs in as an existing account. Only ever proves which user_id
  /// this client should now act as — it grants no capability beyond
  /// selecting that user's own isolated URI state.
  Future<AuthOutcome> login(String username, String password);

  /// Ends the current login. After this, [isAuthenticated] is false
  /// and every subsequent call behaves as an unauthenticated client
  /// until [login]/[signup] succeeds again.
  Future<void> logout();

  /// Prototype 2 (multi-client + runtime awareness): the backend
  /// address this client is currently configured to talk to. Never
  /// "localhost" by assumption on every device — a phone reaching a
  /// PC's backend over the LAN must be pointed at that PC's own
  /// address (see [setBaseUrl]).
  String get baseUrl;

  /// Reconfigures which backend this client talks to. Takes effect
  /// immediately for every subsequent call - already-in-flight
  /// requests are unaffected. Does not itself log out or clear any
  /// held token; a token issued by one backend is meaningless to a
  /// different one, so a caller should usually [logout] first when
  /// deliberately switching backends.
  void setBaseUrl(String baseUrl);

  /// A cheap, side-effect-free reachability check - backs a "Test
  /// connection" action so reconnect/disconnect has clear, explicit
  /// feedback rather than only surfacing as a failed [ask]/[approve]/
  /// [cancel] later. Never throws; any network failure, timeout, or
  /// non-2xx response is reported through [ConnectionCheckResult],
  /// never as an uncaught exception.
  ///
  /// [addressOverride], when non-null, is tested as-is instead of
  /// [baseUrl] - this is what lets a "Test connection" action check
  /// whatever address is currently typed into a form field even before
  /// [setBaseUrl] has been called with it (see Settings). This check
  /// itself never calls [setBaseUrl] and never persists anything -
  /// applying/saving an address stays entirely [setBaseUrl]'s job.
  Future<ConnectionCheckResult> checkConnection({String? addressOverride});

  /// Ask URI to understand and, if appropriate, propose an action for
  /// [text]. Never executes anything by itself.
  ///
  /// [turnId], when given, becomes the returned [UriTurn.id] instead of
  /// a freshly generated one - this is what lets a caller (see
  /// AppState.ask) add an immediately-visible pending turn to the
  /// conversation before this call resolves, then update that exact
  /// same turn in place once it does, rather than the pending turn and
  /// the final result ever being two separate list entries.
  Future<UriTurn> ask(String text, {String? turnId});

  /// Approve a previously proposed action, moving it through execution.
  /// Returns the final turn once execution completes.
  Future<UriTurn> approve(String turnId);

  /// Cancel a previously proposed action. Nothing is executed.
  Future<UriTurn> cancel(String turnId);

  /// Current connection state for known external services.
  Future<List<ServiceConnection>> listConnections();

  /// Starts (or reports on) authorization for a service. This never
  /// fakes success: for a Google service, the backend cannot complete
  /// OAuth consent from an HTTP call (see server.py's
  /// authorize_connection) - what actually comes back is the real,
  /// current state plus an honest, actionable explanation of what is
  /// needed, which the caller shows verbatim rather than silently
  /// discarding.
  Future<ConnectionAuthorizeOutcome> authorizeConnection(String connectionId);

  /// Disconnect a currently-connected service.
  Future<ServiceConnection> disconnectConnection(String connectionId);

  /// Structured activity/audit history, most recent first.
  Future<List<ActivityEvent>> listActivity();

  /// Every fact URI currently holds about the user (see GET /memory).
  Future<List<MemoryEntry>> listMemory();

  /// The user explicitly telling URI to remember something. Throws
  /// [AttachmentException]-style validation errors as
  /// [MemoryWriteException] with the backend's real reason.
  Future<MemoryEntry> addMemory({
    required String category,
    required String content,
    double? confidence,
    String? notes,
  });

  /// Real, complete removal. Returns whether anything was deleted.
  Future<bool> deleteMemory(String memoryId);

  /// This install's durable identity (see GET /identity): the
  /// logged-in user's own portable user_id, and this device's
  /// local-only device_id. Neither is a credential. Null on any
  /// failure — Settings/About show it as unavailable rather than a
  /// stale or fabricated value.
  Future<UriIdentity?> getIdentity();

  /// A short summary of recent + pending work for the Home screen.
  Future<HomeSummary> loadHomeSummary();

  /// Every proposed action still awaiting a decision, across all
  /// sessions — not only the current Ask URI conversation. Approve or
  /// cancel a task the same way as any awaiting-approval turn: call
  /// [approve]/[cancel] with [TaskItem.id].
  Future<List<TaskItem>> listTasks();

  /// M16: URI's real capability catalogue (GET /capabilities) — what
  /// it can do, what it cannot, and honestly why not (gap_reason
  /// distinguishes "no implementation exists" from "exists but this
  /// runtime cannot use it right now").
  ///
  /// Returns an empty list when the backend is unreachable — the UI
  /// then shows nothing rather than claiming capabilities it cannot
  /// verify.
  Future<List<CapabilityInfo>> listCapabilities();

  /// M16: pushes the user's behaviour-changing preferences to the
  /// backend profile (POST /profile), which is what
  /// personalization_context feeds to the Brain on every turn.
  ///
  /// Before M16 these lived only in device-local storage, so the Brain
  /// never actually saw the communication style or autonomy level the
  /// user chose during onboarding. Returns whether the backend
  /// accepted them - never assumed.
  Future<bool> syncPreferences({
    required String communicationStyle,
    required String autonomyLevel,
    required List<String> focusAreas,
  });

  /// M16: attach a file to the current conversation. The backend
  /// validates type/size and stores it (see file_store.py); URI only
  /// ever reads it if the Brain decides to, via the registered
  /// read_attached_file capability.
  ///
  /// Throws [AttachmentException] with the backend's real reason when
  /// the file is rejected, so the user is told why rather than seeing
  /// a silent failure.
  Future<Attachment> uploadAttachment({
    required String filename,
    required List<int> bytes,
  });

  /// Files currently attached to this conversation.
  Future<List<Attachment>> listAttachments();

  /// Remove an attachment. Returns whether anything was actually
  /// removed.
  Future<bool> deleteAttachment(String fileId);

  /// The raw bytes of a previously attached file, so the user can open
  /// it back up from the chat screen to verify what URI actually has —
  /// the same file the Brain may separately choose to read via
  /// read_attached_file, never a re-interpretation of it.
  Future<List<int>> downloadAttachmentContent(String fileId);
}

/// M16: one capability from URI's real registry, with the honest
/// availability fields the backend already maintains (see
/// capability_registry.py). [gapReason] is null when the capability is
/// genuinely usable right now.
class CapabilityInfo {
  const CapabilityInfo({
    required this.id,
    required this.description,
    required this.status,
    required this.availability,
    required this.approvalRequirement,
    required this.risk,
    this.limitations,
    this.gapReason,
  });

  final String id;
  final String description;
  final String status;
  final String availability;
  final String approvalRequirement;
  final String risk;
  final String? limitations;
  final String? gapReason;

  /// True only for a capability the backend says is usable right now.
  bool get isUsable => status == 'implemented' && gapReason == null;

  /// Whether an implementation exists at all — distinct from whether
  /// it can run right now. Nothing the user says or approves makes a
  /// non-existent capability work, and the UI must not imply otherwise.
  bool get isImplemented => status == 'implemented';
}

/// This install's durable identity, from GET /identity — see
/// UriClient.getIdentity.
class UriIdentity {
  const UriIdentity({required this.userId, required this.deviceId});

  final String userId;
  final String deviceId;
}

/// Raised when the backend refuses a memory write (see POST /memory's
/// validation — server.py's MemoryValidationError).
class MemoryWriteException implements Exception {
  const MemoryWriteException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Raised when the backend refuses an upload. [message] is the real,
/// user-facing reason (unsupported type, too large, empty).
class AttachmentException implements Exception {
  const AttachmentException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Result of a [UriClient.login]/[UriClient.signup] attempt.
/// Result of a [UriClient.authorizeConnection] call: the connection's
/// real current state plus the backend's own plain-language
/// explanation of what is (or was) needed — shown verbatim by the
/// caller so tapping "Connect" always produces honest, visible
/// feedback instead of a silent no-op.
class ConnectionAuthorizeOutcome {
  const ConnectionAuthorizeOutcome({
    required this.connection,
    required this.explanation,
  });

  final ServiceConnection connection;
  final String explanation;
}

class AuthOutcome {
  const AuthOutcome.success() : success = true, message = null;
  const AuthOutcome.failure(this.message) : success = false;

  final bool success;
  final String? message;
}

/// Result of a [UriClient.checkConnection] attempt. [detail] carries a
/// short, human-readable diagnostic (the underlying exception's
/// message, or an HTTP status) rather than swallowing every failure
/// into a bare bool - null on success, or when a failure genuinely has
/// nothing more specific to say.
class ConnectionCheckResult {
  const ConnectionCheckResult.reachable() : reachable = true, detail = null;
  const ConnectionCheckResult.unreachable([this.detail]) : reachable = false;

  final bool reachable;
  final String? detail;
}

/// Aggregate data the Home screen needs in one call.
class HomeSummary {
  const HomeSummary({
    required this.recentTurns,
    required this.pendingApprovalCount,
    required this.connectedServiceCount,
    required this.totalServiceCount,
  });

  final List<UriTurn> recentTurns;
  final int pendingApprovalCount;
  final int connectedServiceCount;
  final int totalServiceCount;
}

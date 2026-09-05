import '../models/activity_event.dart';
import '../models/connection.dart';
import '../models/task_item.dart';
import '../models/uri_turn.dart';

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

  /// Request (mock) authorization for a service that needs it.
  Future<ServiceConnection> authorizeConnection(String connectionId);

  /// Disconnect a currently-connected service.
  Future<ServiceConnection> disconnectConnection(String connectionId);

  /// Structured activity/audit history, most recent first.
  Future<List<ActivityEvent>> listActivity();

  /// A short summary of recent + pending work for the Home screen.
  Future<HomeSummary> loadHomeSummary();

  /// Every proposed action still awaiting a decision, across all
  /// sessions — not only the current Ask URI conversation. Approve or
  /// cancel a task the same way as any awaiting-approval turn: call
  /// [approve]/[cancel] with [TaskItem.id].
  Future<List<TaskItem>> listTasks();
}

/// Result of a [UriClient.login]/[UriClient.signup] attempt.
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

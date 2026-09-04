import '../models/activity_event.dart';
import '../models/connection.dart';
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
  /// Ask URI to understand and, if appropriate, propose an action for
  /// [text]. Never executes anything by itself.
  Future<UriTurn> ask(String text);

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

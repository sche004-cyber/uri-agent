/// One proposed action still awaiting a user decision, from any
/// session — the backend for a cross-session "what needs my
/// attention" view. Deliberately a separate, smaller shape than
/// [ProposedAction]/[UriTurn]: a task has no conversational turn
/// (userText, understanding) behind it, only what the runtime's
/// capability registry already knows about the capability it
/// belongs to.
class TaskItem {
  const TaskItem({
    required this.id,
    required this.capabilityId,
    required this.description,
    required this.risk,
    required this.sessionId,
    required this.createdAt,
  });

  /// Matches the backend's action_id exactly — also usable directly
  /// as a [UriClient.approve]/[UriClient.cancel] argument, the same
  /// way an awaiting-approval [UriTurn.id] is (see HttpUriClient).
  final String id;

  final String capabilityId;
  final String description;

  /// One of the capability registry's risk values (e.g. "controlled",
  /// "low", "variable", "high", "unknown") — not a Flutter enum, since
  /// it's read straight from GET /tasks. See tasks_screen.dart for how
  /// this maps onto the existing [ActionImpact]-based status pill for
  /// a visually consistent look with Ask URI's proposal cards.
  final String risk;

  final String sessionId;
  final DateTime createdAt;
}

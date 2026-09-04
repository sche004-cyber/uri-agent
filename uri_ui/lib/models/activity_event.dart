/// A structured, audit-style record of something URI's runtime did or
/// decided — the same kind of entry the Python runtime's AuditTrail
/// produces. This view intentionally shows structured outcomes
/// (what was proposed, what was approved, what executed) rather than
/// raw model reasoning or chain-of-thought, matching the runtime's own
/// "no raw prompts/responses in audit records" rule.
enum ActivityKind { proposal, approval, execution, cancellation, system }

class ActivityEvent {
  const ActivityEvent({
    required this.id,
    required this.timestamp,
    required this.kind,
    required this.summary,
    this.detail,
  });

  final String id;
  final DateTime timestamp;
  final ActivityKind kind;
  final String summary;
  final String? detail;
}

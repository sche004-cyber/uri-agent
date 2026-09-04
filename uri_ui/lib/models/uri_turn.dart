/// Lifecycle stage of a single Ask-URI turn.
///
/// This intentionally mirrors the shape of URI's real runtime contract
/// (see URI_MODEL_RUNTIME_CONTRACT.md): a model may only ever *propose*
/// an action; the runtime decides whether it is authorized and reports
/// execution separately. The UI never collapses "URI understood the
/// request" and "URI did the thing" into a single state.
enum TurnStage {
  understanding,
  proposalReady,
  awaitingApproval,
  executing,
  completed,
  cancelled,
  failed,

  /// URI understood the request but the service it would need isn't
  /// authorized yet. Distinct from [failed]: nothing went wrong, URI is
  /// just being honest that it can't proceed rather than pretending it
  /// can. See UriTurn.requiredConnectionName / requiredConnectionId.
  needsConnection,
}

/// A risk/impact hint for a proposed action, used only to drive how much
/// visual weight the approval control gets. This is a UI-side display
/// concern, not an authorization decision — the runtime remains the sole
/// authority on whether an action is actually permitted.
enum ActionImpact { routine, notable, sensitive }

/// A concrete, runtime-registered action URI is proposing to take.
///
/// Deliberately does not claim a fixed catalogue name like "Insurance
/// Renewal" — [title] and [description] are generated per-request, the
/// way a real proposal from the model/runtime contract would be.
class ProposedAction {
  const ProposedAction({
    required this.title,
    required this.description,
    required this.targetService,
    required this.impact,
  });

  final String title;
  final String description;
  final String targetService;
  final ActionImpact impact;
}

/// The outcome of an executed (approved) action, as reported back by the
/// runtime — never fabricated or assumed by the UI.
class ActionResult {
  const ActionResult({required this.summary, this.detail});

  final String summary;
  final String? detail;
}

/// One exchange in the Ask URI conversation: the user's request plus
/// URI's evolving response as it moves through understanding, proposal,
/// approval, and execution.
class UriTurn {
  UriTurn({
    required this.id,
    required this.userText,
    required this.timestamp,
    required this.stage,
    this.understanding,
    this.proposedAction,
    this.result,
    this.failureReason,
    this.requiredConnectionId,
    this.requiredConnectionName,
  });

  final String id;
  final String userText;
  final DateTime timestamp;
  TurnStage stage;
  String? understanding;
  ProposedAction? proposedAction;
  ActionResult? result;
  String? failureReason;

  /// Set only when [stage] is [TurnStage.needsConnection] — which
  /// connection (by id, for the "connect" action, and by display name,
  /// for the message) URI would need before it could actually propose
  /// anything for this request.
  String? requiredConnectionId;
  String? requiredConnectionName;

  UriTurn copyWith({
    TurnStage? stage,
    String? understanding,
    ProposedAction? proposedAction,
    ActionResult? result,
    String? failureReason,
    String? requiredConnectionId,
    String? requiredConnectionName,
  }) {
    return UriTurn(
      id: id,
      userText: userText,
      timestamp: timestamp,
      stage: stage ?? this.stage,
      understanding: understanding ?? this.understanding,
      proposedAction: proposedAction ?? this.proposedAction,
      result: result ?? this.result,
      failureReason: failureReason ?? this.failureReason,
      requiredConnectionId: requiredConnectionId ?? this.requiredConnectionId,
      requiredConnectionName: requiredConnectionName ?? this.requiredConnectionName,
    );
  }
}

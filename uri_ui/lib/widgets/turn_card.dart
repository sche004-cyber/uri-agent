import 'package:flutter/material.dart';

import '../models/uri_turn.dart';
import '../theme/uri_theme.dart';
import 'status_pill.dart';

/// Renders one Ask-URI turn end to end, keeping three stages visually
/// distinct at all times rather than collapsing them into one blob:
///   1. Understanding / proposal — what URI read from the request and,
///      if applicable, what it wants to do.
///   2. Approval — the explicit human decision point.
///   3. Execution / result — reported outcome, only ever shown once the
///      runtime has actually confirmed it (never assumed by the card).
class TurnCard extends StatelessWidget {
  const TurnCard({
    super.key,
    required this.turn,
    required this.onApprove,
    required this.onCancel,
    required this.onConnectService,
  });

  final UriTurn turn;
  final VoidCallback onApprove;
  final VoidCallback onCancel;

  /// Invoked with the blocked connection's id when the user taps
  /// "Connect [service]" from a [TurnStage.needsConnection] turn.
  final ValueChanged<String> onConnectService;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ---- the request itself ----
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    turn.userText,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                const SizedBox(width: UriSpace.sm),
                StatusPill.forStage(turn.stage),
              ],
            ),

            if (turn.understanding != null) ...[
              const SizedBox(height: UriSpace.sm),
              Text(turn.understanding!, style: theme.textTheme.bodyMedium),
            ],

            // ---- failed: the technical detail, always shown ----
            //
            // Previously never rendered anywhere - a failed turn with
            // no understanding text (e.g. the model backend itself
            // was unreachable, so no narrative was ever attempted)
            // showed only the red "Failed" pill above and nothing
            // else. failureReason is shown regardless of whether
            // understanding is also present, since it's the specific
            // technical detail rather than a restatement of it.
            if (turn.stage == TurnStage.failed && turn.failureReason != null) ...[
              const SizedBox(height: UriSpace.sm),
              _FailureBlock(reason: turn.failureReason!),
            ],

            // ---- blocked: needs a connection first ----
            if (turn.stage == TurnStage.needsConnection) ...[
              const SizedBox(height: UriSpace.md),
              _ConnectionRequiredBlock(turn: turn, onConnectService: onConnectService),
            ],

            // ---- stage 1: proposal ----
            if (turn.proposedAction != null) ...[
              const SizedBox(height: UriSpace.md),
              _ProposalBlock(
                turn: turn,
                onApprove: onApprove,
                onCancel: onCancel,
              ),
            ],

            // ---- stage 3: result ----
            if (turn.result != null) ...[
              const SizedBox(height: UriSpace.md),
              _ResultBlock(turn: turn),
            ],
          ],
        ),
      ),
    );
  }
}

class _FailureBlock extends StatelessWidget {
  const _FailureBlock({required this.reason});

  final String reason;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.dangerSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: UriColors.danger.withValues(alpha: 0.22)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline_rounded, size: 16, color: UriColors.danger),
          const SizedBox(width: UriSpace.xs),
          Expanded(
            child: Text(
              reason,
              style: theme.textTheme.bodyMedium?.copyWith(color: UriColors.danger),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConnectionRequiredBlock extends StatelessWidget {
  const _ConnectionRequiredBlock({required this.turn, required this.onConnectService});

  final UriTurn turn;
  final ValueChanged<String> onConnectService;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final serviceName = turn.requiredConnectionName ?? 'that service';
    final connectionId = turn.requiredConnectionId;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.warningSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: UriColors.warning.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.link_off_rounded, size: 16, color: UriColors.warning),
              const SizedBox(width: UriSpace.xs),
              Text(
                'Connection needed',
                style: theme.textTheme.labelLarge?.copyWith(color: UriColors.warning),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.sm),
          Text(
            'URI would need access to $serviceName to do this — nothing has been proposed or attempted.',
            style: theme.textTheme.bodyMedium,
          ),
          if (connectionId != null) ...[
            const SizedBox(height: UriSpace.md),
            OutlinedButton.icon(
              onPressed: () => onConnectService(connectionId),
              icon: const Icon(Icons.hub_outlined, size: 16),
              label: Text('Connect $serviceName'),
            ),
          ],
        ],
      ),
    );
  }
}

class _ProposalBlock extends StatelessWidget {
  const _ProposalBlock({required this.turn, required this.onApprove, required this.onCancel});

  final UriTurn turn;
  final VoidCallback onApprove;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final action = turn.proposedAction!;
    final isDecided = turn.stage != TurnStage.awaitingApproval && turn.stage != TurnStage.proposalReady;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.accentSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: UriColors.accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.bolt_rounded, size: 16, color: UriColors.accentInk),
              const SizedBox(width: UriSpace.xs),
              Text(
                'Proposed action',
                style: theme.textTheme.labelLarge?.copyWith(color: UriColors.accentInk),
              ),
              const Spacer(),
              StatusPill.forImpact(action.impact),
            ],
          ),
          const SizedBox(height: UriSpace.sm),
          Text(action.title, style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(action.description, style: theme.textTheme.bodyMedium),
          const SizedBox(height: UriSpace.xs),
          Text(
            'Uses: ${action.targetService}',
            style: theme.textTheme.labelSmall,
          ),
          if (!isDecided) ...[
            const SizedBox(height: UriSpace.md),
            Row(
              children: [
                ElevatedButton(onPressed: onApprove, child: const Text('Approve')),
                const SizedBox(width: UriSpace.sm),
                OutlinedButton(onPressed: onCancel, child: const Text('Cancel')),
              ],
            ),
          ] else if (turn.stage == TurnStage.executing) ...[
            const SizedBox(height: UriSpace.md),
            const Row(
              children: [
                SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: UriColors.accentInk),
                ),
                SizedBox(width: UriSpace.sm),
                Text('Executing…', style: TextStyle(color: UriColors.accentInk, fontWeight: FontWeight.w600)),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _ResultBlock extends StatelessWidget {
  const _ResultBlock({required this.turn});

  final UriTurn turn;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final result = turn.result!;
    final isCancelled = turn.stage == TurnStage.cancelled;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: isCancelled ? UriColors.surfaceSunken : UriColors.successSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isCancelled ? Icons.block_rounded : Icons.check_circle_rounded,
                size: 16,
                color: isCancelled ? UriColors.inkFaint : UriColors.success,
              ),
              const SizedBox(width: UriSpace.xs),
              Text(
                isCancelled ? 'Cancelled' : 'Result',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: isCancelled ? UriColors.inkFaint : UriColors.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Text(result.summary, style: theme.textTheme.bodyLarge?.copyWith(color: UriColors.ink)),
          if (result.detail != null) ...[
            const SizedBox(height: 4),
            Text(result.detail!, style: theme.textTheme.bodyMedium),
          ],
        ],
      ),
    );
  }
}

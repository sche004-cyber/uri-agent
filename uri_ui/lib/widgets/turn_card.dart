import 'package:flutter/material.dart';

import '../models/attachment.dart';
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
    required this.onOpenAttachment,
  });

  final UriTurn turn;
  final VoidCallback onApprove;
  final VoidCallback onCancel;

  /// Invoked with the blocked connection's id when the user taps
  /// "Connect [service]" from a [TurnStage.needsConnection] turn.
  final ValueChanged<String> onConnectService;

  /// Invoked when the user taps one of [turn.attachments] to open and
  /// verify it — the same file URI has, not a re-upload or re-pick.
  final ValueChanged<Attachment> onOpenAttachment;

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
                StatusPill.forStage(context, turn.stage),
              ],
            ),

            // ---- attachments this turn was sent with ----
            //
            // Fixed to this turn (see UriTurn.attachments), never the
            // whole conversation's staged list, so re-opening old
            // history always shows the right file next to the right
            // message - like a WhatsApp chat bubble's own attachment.
            if (turn.attachments.isNotEmpty) ...[
              const SizedBox(height: UriSpace.sm),
              _TurnAttachments(
                attachments: turn.attachments,
                onOpen: onOpenAttachment,
              ),
            ],

            if (turn.understanding != null) ...[
              const SizedBox(height: UriSpace.sm),
              Text(turn.understanding!, style: theme.textTheme.bodyMedium),
            ],

            // ---- chat UX fix: persistent processing state ----
            //
            // TurnStage.understanding is set the instant a request is
            // submitted (see AppState.ask) and nothing else on the turn
            // is populated yet - proposedAction/result/failureReason
            // are all still null. Without this block the card would
            // show only the user's message and a bare status pill,
            // which is easy to miss as "URI is working on this" rather
            // than a stalled/empty card. Not a new stage or a fake
            // progress step - existing TurnStage.understanding
            // semantics, rendered.
            if (turn.stage == TurnStage.understanding) ...[
              const SizedBox(height: UriSpace.md),
              const _ProcessingBlock(),
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

/// A persistent, visible "URI is working on this" state shown from the
/// instant a request is submitted until it resolves - see TurnCard's
/// TurnStage.understanding branch. Reuses the exact spinner+label
/// pattern _ProposalBlock's "Executing…" row already established,
/// rather than inventing a new visual language for "processing."
class _ProcessingBlock extends StatelessWidget {
  const _ProcessingBlock();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          SizedBox(
            height: 16,
            width: 16,
            child: CircularProgressIndicator(strokeWidth: 2, color: colors.inkFaint),
          ),
          const SizedBox(width: UriSpace.sm),
          Expanded(
            child: Text(
              'URI is working on this…',
              style: theme.textTheme.bodyMedium?.copyWith(color: colors.inkFaint),
            ),
          ),
        ],
      ),
    );
  }
}

/// The files this specific turn was sent with, each tappable to open
/// and verify — see [TurnCard.onOpenAttachment].
class _TurnAttachments extends StatelessWidget {
  const _TurnAttachments({required this.attachments, required this.onOpen});

  final List<Attachment> attachments;
  final ValueChanged<Attachment> onOpen;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: UriSpace.sm,
      runSpacing: UriSpace.sm,
      children: [
        for (final attachment in attachments)
          ActionChip(
            avatar: const Icon(Icons.description_outlined, size: 18),
            label: Text(
              '${attachment.filename} · ${_formatSize(attachment.sizeBytes)}',
            ),
            onPressed: () => onOpen(attachment),
          ),
      ],
    );
  }

  static String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).round()} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

class _FailureBlock extends StatelessWidget {
  const _FailureBlock({required this.reason});

  final String reason;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.dangerSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.danger.withValues(alpha: 0.22)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline_rounded, size: 16, color: colors.danger),
          const SizedBox(width: UriSpace.xs),
          Expanded(
            child: Text(
              reason,
              style: theme.textTheme.bodyMedium?.copyWith(color: colors.danger),
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
    final colors = UriColors.of(context);
    final serviceName = turn.requiredConnectionName ?? 'that service';
    final connectionId = turn.requiredConnectionId;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.warningSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.warning.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.link_off_rounded, size: 16, color: colors.warning),
              const SizedBox(width: UriSpace.xs),
              Text(
                'Connection needed',
                style: theme.textTheme.labelLarge?.copyWith(color: colors.warning),
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
    final colors = UriColors.of(context);
    final action = turn.proposedAction!;
    final isDecided = turn.stage != TurnStage.awaitingApproval && turn.stage != TurnStage.proposalReady;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.accentSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.bolt_rounded, size: 16, color: colors.accentInk),
              const SizedBox(width: UriSpace.xs),
              Text(
                'Proposed action',
                style: theme.textTheme.labelLarge?.copyWith(color: colors.accentInk),
              ),
              const Spacer(),
              StatusPill.forImpact(context, action.impact),
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
            Row(
              children: [
                SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: colors.accentInk),
                ),
                const SizedBox(width: UriSpace.sm),
                Text('Executing…', style: TextStyle(color: colors.accentInk, fontWeight: FontWeight.w600)),
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
    final colors = UriColors.of(context);
    final result = turn.result!;
    final isCancelled = turn.stage == TurnStage.cancelled;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: isCancelled ? colors.surfaceSunken : colors.successSoft,
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
                color: isCancelled ? colors.inkFaint : colors.success,
              ),
              const SizedBox(width: UriSpace.xs),
              Text(
                isCancelled ? 'Cancelled' : 'Result',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: isCancelled ? colors.inkFaint : colors.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Text(result.summary, style: theme.textTheme.bodyLarge?.copyWith(color: colors.ink)),
          if (result.detail != null) ...[
            const SizedBox(height: 4),
            Text(result.detail!, style: theme.textTheme.bodyMedium),
          ],
          // M16: real, retrievable sources behind a researched answer.
          // Only rendered when the capability actually returned some -
          // never a placeholder or an invented citation.
          if (result.sources.isNotEmpty) ...[
            const SizedBox(height: UriSpace.sm),
            Text(
              'Sources',
              style: theme.textTheme.labelLarge?.copyWith(
                color: colors.inkFaint,
              ),
            ),
            const SizedBox(height: 4),
            for (final source in result.sources)
              Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Text(
                  '• ${source.title} — ${source.url}',
                  style: theme.textTheme.bodySmall,
                ),
              ),
          ],
        ],
      ),
    );
  }
}

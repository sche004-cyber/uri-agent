import 'package:flutter/material.dart';

import '../../models/activity_event.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/screen_header.dart';

/// Shows structured activity — proposals, approvals, executions,
/// cancellations, system events — the same categories the runtime's
/// AuditTrail records. This is deliberately not a transcript of model
/// reasoning: only outcomes a human would want to audit.
class ActivityScreen extends StatefulWidget {
  const ActivityScreen({super.key});

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AppStateScope.of(context).loadActivity();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const ScreenHeader(
                title: 'Activity',
                subtitle:
                    'A structured record of what URI proposed, what you decided, '
                    'and what it actually did.',
              ),
              if (!state.hasLoadedActivity)
                const LoadingState()
              else if (state.activity.isEmpty)
                const EmptyState(
                  icon: Icons.receipt_long_outlined,
                  title: 'No activity yet',
                  message: 'Once you ask URI to do something, every proposal, approval, '
                      'and execution will show up here.',
                )
              else
                Column(
                  children: [
                    for (final event in state.activity) _ActivityRow(event: event),
                  ],
                ),
            ],
          ),
        );
      },
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.event});

  final ActivityEvent event;

  ({IconData icon, Color color}) _visual(UriColors colors) {
    switch (event.kind) {
      case ActivityKind.proposal:
        return (icon: Icons.bolt_rounded, color: colors.accentInk);
      case ActivityKind.approval:
        return (icon: Icons.check_rounded, color: colors.success);
      case ActivityKind.execution:
        return (icon: Icons.check_circle_rounded, color: colors.success);
      case ActivityKind.cancellation:
        return (icon: Icons.block_rounded, color: colors.inkFaint);
      case ActivityKind.system:
        return (icon: Icons.settings_outlined, color: colors.inkFaint);
    }
  }

  String _relativeTime(DateTime timestamp) {
    final diff = DateTime.now().difference(timestamp);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    final visual = _visual(colors);

    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: visual.color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(999),
                ),
                alignment: Alignment.center,
                child: Icon(visual.icon, size: 15, color: visual.color),
              ),
              const SizedBox(width: UriSpace.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(event.summary, style: theme.textTheme.bodyLarge?.copyWith(color: colors.ink)),
                    if (event.detail != null) ...[
                      const SizedBox(height: 2),
                      Text(event.detail!, style: theme.textTheme.bodyMedium),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              Text(_relativeTime(event.timestamp), style: theme.textTheme.labelSmall),
            ],
          ),
        ),
      ),
    );
  }
}

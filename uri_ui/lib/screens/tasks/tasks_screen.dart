import 'package:flutter/material.dart';

import '../../models/task_item.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../utils/capability_display.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_pill.dart';

/// Cross-session "what needs my attention" view — every proposed
/// action still awaiting a decision, across every conversation, not
/// only whatever's currently open in Ask URI. Approving or cancelling
/// here calls the exact same runtime approval gate Ask URI's TurnCard
/// does (see AppState.approveTask/cancelTask) — this screen is a
/// different way to reach the same decision point, never a second
/// authority over it.
class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AppStateScope.of(context).loadTasks();
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
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ScreenHeader(
                  title: 'Tasks',
                  subtitle:
                      'Everything URI has proposed and is waiting on you for — '
                      'across every conversation, not just the one you have open.',
                  trailing: IconButton(
                    tooltip: 'Refresh',
                    onPressed: () => state.loadTasks(),
                    icon: const Icon(Icons.refresh_rounded),
                  ),
                ),
                if (state.isLoadingTasks && state.tasks.isEmpty)
                  const LoadingState(message: 'Checking for pending tasks…')
                else if (state.tasks.isEmpty)
                  const EmptyState(
                    icon: Icons.task_alt_outlined,
                    title: 'Nothing waiting on you',
                    message:
                        'When URI proposes something that needs your approval, '
                        'it will show up here until you approve or cancel it.',
                  )
                else
                  Column(
                    children: [
                      for (final task in state.tasks)
                        _TaskCard(
                          task: task,
                          onApprove: () => state.approveTask(task.id),
                          onCancel: () => state.cancelTask(task.id),
                        ),
                    ],
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _TaskCard extends StatelessWidget {
  const _TaskCard({required this.task, required this.onApprove, required this.onCancel});

  final TaskItem task;
  final VoidCallback onApprove;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.md),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      humanizeIdentifier(task.capabilityId),
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                  const SizedBox(width: UriSpace.sm),
                  StatusPill.forImpact(impactFromRisk(task.risk)),
                ],
              ),
              if (task.description.isNotEmpty) ...[
                const SizedBox(height: UriSpace.xs),
                Text(task.description, style: theme.textTheme.bodyMedium),
              ],
              const SizedBox(height: UriSpace.md),
              Row(
                children: [
                  ElevatedButton(onPressed: onApprove, child: const Text('Approve')),
                  const SizedBox(width: UriSpace.sm),
                  OutlinedButton(onPressed: onCancel, child: const Text('Cancel')),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

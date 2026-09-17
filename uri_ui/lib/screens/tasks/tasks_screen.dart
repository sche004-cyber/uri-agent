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
///
/// Per Hybrid Blueprint §4.5: header + 4 client-computed summary tiles
/// (Total Pending, Low Risk, Needs Review, High Risk — bucketed from
/// [TaskItem.risk], the one real field GET /tasks returns; no second
/// endpoint) + a search/filter row + a real-rows-only data table.
class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

/// The three risk buckets shown in the filter chip and tiles, each a
/// display-only grouping of the backend's own risk string — never a
/// separate classification the backend doesn't already report.
enum _RiskBucket { all, low, review, high }

class _TasksScreenState extends State<TasksScreen> {
  final _searchController = TextEditingController();
  String _query = '';
  _RiskBucket _riskFilter = _RiskBucket.all;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AppStateScope.of(context).loadTasks();
    });
    _searchController.addListener(() {
      setState(() => _query = _searchController.text.trim().toLowerCase());
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  static _RiskBucket _bucketOf(String risk) {
    switch (risk) {
      case 'low':
      case 'controlled':
        return _RiskBucket.low;
      case 'high':
        return _RiskBucket.high;
      default:
        return _RiskBucket.review;
    }
  }

  List<TaskItem> _filtered(List<TaskItem> tasks) {
    return tasks.where((task) {
      if (_riskFilter != _RiskBucket.all && _bucketOf(task.risk) != _riskFilter) {
        return false;
      }
      if (_query.isEmpty) return true;
      return task.description.toLowerCase().contains(_query) ||
          humanizeIdentifier(task.capabilityId).toLowerCase().contains(_query);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final tasks = state.tasks;
        final visible = _filtered(tasks);

        final total = tasks.length;
        final low = tasks.where((t) => _bucketOf(t.risk) == _RiskBucket.low).length;
        final review = tasks.where((t) => _bucketOf(t.risk) == _RiskBucket.review).length;
        final high = tasks.where((t) => _bucketOf(t.risk) == _RiskBucket.high).length;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1080),
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
                const SizedBox(height: UriSpace.lg),
                if (state.isLoadingTasks && tasks.isEmpty)
                  const LoadingState(message: 'Checking for pending tasks…')
                else ...[
                  _SummaryTiles(total: total, low: low, review: review, high: high),
                  const SizedBox(height: UriSpace.lg),
                  _FilterRow(
                    controller: _searchController,
                    riskFilter: _riskFilter,
                    onRiskFilterChanged: (bucket) =>
                        setState(() => _riskFilter = bucket),
                  ),
                  const SizedBox(height: UriSpace.md),
                  if (tasks.isEmpty)
                    const EmptyState(
                      icon: Icons.task_alt_outlined,
                      title: 'Nothing waiting on you',
                      message:
                          'When URI proposes something that needs your approval, '
                          'it will show up here until you approve or cancel it.',
                    )
                  else if (visible.isEmpty)
                    EmptyState(
                      icon: Icons.filter_alt_off_outlined,
                      title: 'No tasks match this filter',
                      message: 'Clear the search or risk filter to see the full list.',
                      action: TextButton(
                        onPressed: () => setState(() {
                          _searchController.clear();
                          _query = '';
                          _riskFilter = _RiskBucket.all;
                        }),
                        child: const Text('Clear filters'),
                      ),
                    )
                  else
                    LayoutBuilder(
                      builder: (context, constraints) {
                        // Batch 4 (§4.5/§8): genuine new mobile design -
                        // no reference mockup exists for Tasks (§8.1),
                        // built from the desktop structure with the
                        // standard table-rows-to-cards conversion.
                        if (constraints.maxWidth < UriBreakpoints.wide) {
                          return _TasksCardList(
                            tasks: visible,
                            onApprove: (id) => state.approveTask(id),
                            onCancel: (id) => state.cancelTask(id),
                          );
                        }
                        return _TasksTable(
                          tasks: visible,
                          onApprove: (id) => state.approveTask(id),
                          onCancel: (id) => state.cancelTask(id),
                        );
                      },
                    ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SummaryTiles extends StatelessWidget {
  const _SummaryTiles({
    required this.total,
    required this.low,
    required this.review,
    required this.high,
  });

  final int total;
  final int low;
  final int review;
  final int high;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 720 ? 4 : 2;
        final tiles = [
          _SummaryTile(label: 'TOTAL PENDING', value: '$total'),
          _SummaryTile(label: 'LOW RISK', value: '$low'),
          _SummaryTile(label: 'NEEDS REVIEW', value: '$review'),
          _SummaryTile(label: 'HIGH RISK', value: '$high'),
        ];
        return GridView.count(
          crossAxisCount: columns,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: UriSpace.md,
          crossAxisSpacing: UriSpace.md,
          // Batch 4: 2.4 only fits a tile's two-line label+value at the
          // 4-column width; at 2 columns each tile is much narrower, so
          // the same ratio made it too short for its own content
          // (never exercised below 720px until this batch's mobile
          // pass).
          childAspectRatio: columns >= 4 ? 2.4 : 1.6,
          children: tiles,
        );
      },
    );
  }
}

class _SummaryTile extends StatelessWidget {
  const _SummaryTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(UriRadius.md),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: colors.inkFaint,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 4),
          Text(value, style: theme.textTheme.headlineSmall),
        ],
      ),
    );
  }
}

class _FilterRow extends StatelessWidget {
  const _FilterRow({
    required this.controller,
    required this.riskFilter,
    required this.onRiskFilterChanged,
  });

  final TextEditingController controller;
  final _RiskBucket riskFilter;
  final ValueChanged<_RiskBucket> onRiskFilterChanged;

  static const _labels = {
    _RiskBucket.all: 'All risk levels',
    _RiskBucket.low: 'Low risk',
    _RiskBucket.review: 'Needs review',
    _RiskBucket.high: 'High risk',
  };

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: controller,
            decoration: const InputDecoration(
              hintText: 'Search tasks…',
              prefixIcon: Icon(Icons.search_rounded, size: 20),
              isDense: true,
            ),
          ),
        ),
        const SizedBox(width: UriSpace.sm),
        PopupMenuButton<_RiskBucket>(
          tooltip: 'Filter by risk level',
          initialValue: riskFilter,
          onSelected: onRiskFilterChanged,
          itemBuilder: (context) => _labels.entries
              .map(
                (e) => PopupMenuItem<_RiskBucket>(value: e.key, child: Text(e.value)),
              )
              .toList(),
          child: Chip(
            label: Text(_labels[riskFilter]!),
            avatar: const Icon(Icons.filter_list_rounded, size: 16),
          ),
        ),
      ],
    );
  }
}

String _formatTaskDate(DateTime dt) {
  final local = dt.toLocal();
  return '${local.year}-${local.month.toString().padLeft(2, '0')}-'
      '${local.day.toString().padLeft(2, '0')}';
}

class _TasksTable extends StatelessWidget {
  const _TasksTable({
    required this.tasks,
    required this.onApprove,
    required this.onCancel,
  });

  final List<TaskItem> tasks;
  final ValueChanged<String> onApprove;
  final ValueChanged<String> onCancel;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Container(
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(UriRadius.md),
        border: Border.all(color: colors.border),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: const [
            DataColumn(label: Text('Description')),
            DataColumn(label: Text('Capability')),
            DataColumn(label: Text('Risk')),
            DataColumn(label: Text('Created')),
            DataColumn(label: Text('')),
          ],
          rows: [
            for (final task in tasks)
              DataRow(
                cells: [
                  DataCell(
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 320),
                      child: Text(
                        task.description.isEmpty ? '(no description)' : task.description,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  DataCell(Text(humanizeIdentifier(task.capabilityId))),
                  DataCell(StatusPill.forImpact(context, impactFromRisk(task.risk))),
                  DataCell(Text(_formatTaskDate(task.createdAt))),
                  DataCell(
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          tooltip: 'Approve',
                          icon: const Icon(Icons.check_circle_outline_rounded, size: 20),
                          onPressed: () => onApprove(task.id),
                        ),
                        IconButton(
                          tooltip: 'Cancel',
                          icon: const Icon(Icons.cancel_outlined, size: 20),
                          onPressed: () => onCancel(task.id),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

/// Batch 4 / Blueprint §8.1: Tasks has no mobile mockup in the
/// reference - this is genuine new responsive design, built from the
/// desktop table's own real fields/actions (§4.5) rather than any
/// mobile reference, per the standard table-rows-to-cards conversion
/// the blueprint names for this exact gap. Every field and both real
/// actions (approve/cancel) carry over unchanged; nothing is dropped.
class _TasksCardList extends StatelessWidget {
  const _TasksCardList({
    required this.tasks,
    required this.onApprove,
    required this.onCancel,
  });

  final List<TaskItem> tasks;
  final ValueChanged<String> onApprove;
  final ValueChanged<String> onCancel;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Column(
      children: [
        for (final task in tasks)
          Container(
            margin: const EdgeInsets.only(bottom: UriSpace.md),
            padding: const EdgeInsets.all(UriSpace.md),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(UriRadius.md),
              border: Border.all(color: colors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        task.description.isEmpty
                            ? '(no description)'
                            : task.description,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    const SizedBox(width: UriSpace.sm),
                    StatusPill.forImpact(context, impactFromRisk(task.risk)),
                  ],
                ),
                const SizedBox(height: UriSpace.xs),
                Text(
                  humanizeIdentifier(task.capabilityId),
                  style: Theme.of(context).textTheme.bodyMedium
                      ?.copyWith(color: colors.inkSoft),
                ),
                const SizedBox(height: 4),
                Text(
                  _formatTaskDate(task.createdAt),
                  style: Theme.of(
                    context,
                  ).textTheme.labelSmall?.copyWith(color: colors.inkFaint),
                ),
                const SizedBox(height: UriSpace.sm),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    IconButton(
                      tooltip: 'Approve',
                      icon: const Icon(Icons.check_circle_outline_rounded, size: 20),
                      onPressed: () => onApprove(task.id),
                    ),
                    IconButton(
                      tooltip: 'Cancel',
                      icon: const Icon(Icons.cancel_outlined, size: 20),
                      onPressed: () => onCancel(task.id),
                    ),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }
}

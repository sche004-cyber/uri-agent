import 'package:flutter/material.dart';

import '../../models/activity_event.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/attachment_opener_service.dart';
import '../../services/file_picker_service.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/loading_state.dart';
import '../ask/ask_uri_screen.dart';

/// Home: a real, verifiable dashboard plus the one canonical Ask URI
/// conversation — not two separate screens for "ask" and "everything
/// else". Every number shown here comes from an endpoint that already
/// exists and already reports real state (/tasks, /connections,
/// /capabilities, /memory, /activity); nothing is invented, and a
/// statistic this build cannot back with a real call is left out
/// rather than faked.
///
/// Responsive: a phone gets a compact stat row above the conversation;
/// a tablet/desktop gets a persistent dashboard side panel next to a
/// wider conversation pane, split at the same breakpoint the rest of
/// the shell uses (see UriBreakpoints).
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.filePicker, this.attachmentOpener});

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      state.loadHome();
      state.loadConnections();
      if (!state.hasLoadedCapabilities) state.loadCapabilities();
      if (!state.hasLoadedMemory) state.loadMemory();
      if (!state.hasLoadedActivity) state.loadActivity();
    });
  }

  void _goTo(int index) {
    context.findAncestorStateOfType<AppShellState>()?.goTo(index);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final conversation = AskUriScreen(
          filePicker: widget.filePicker,
          attachmentOpener: widget.attachmentOpener,
        );

        if (UriBreakpoints.isWide(context)) {
          final colors = UriColors.of(context);
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                width: 320,
                child: Container(
                  decoration: BoxDecoration(border: Border(right: BorderSide(color: colors.border))),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(UriSpace.lg),
                    child: _Dashboard(state: state, onGoTo: _goTo),
                  ),
                ),
              ),
              Expanded(child: conversation),
            ],
          );
        }

        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(UriSpace.lg, UriSpace.lg, UriSpace.lg, 0),
              child: _CompactDashboard(state: state, onGoTo: _goTo),
            ),
            Expanded(child: conversation),
          ],
        );
      },
    );
  }
}

/// Wide-layout dashboard: greeting, every real stat, and recent
/// activity, stacked in a persistent side panel.
class _Dashboard extends StatelessWidget {
  const _Dashboard({required this.state, required this.onGoTo});

  final AppState state;
  final ValueChanged<int> onGoTo;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Good to see you.', style: theme.textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(
          'Tell URI what you need — it will check with you before anything happens.',
          style: theme.textTheme.bodyMedium,
        ),
        const SizedBox(height: UriSpace.lg),
        _StatTile(
          icon: Icons.pending_actions_outlined,
          label: 'Pending approvals',
          value: '${state.homeSummary?.pendingApprovalCount ?? 0}',
          accent: (state.homeSummary?.pendingApprovalCount ?? 0) > 0,
          onTap: () => onGoTo(ShellIndex.tasks),
        ),
        const SizedBox(height: UriSpace.sm),
        _StatTile(
          icon: Icons.hub_outlined,
          label: 'Connected services',
          value:
              '${state.homeSummary?.connectedServiceCount ?? 0} of ${state.homeSummary?.totalServiceCount ?? 0}',
          onTap: () => onGoTo(ShellIndex.connections),
        ),
        const SizedBox(height: UriSpace.sm),
        _StatTile(
          icon: Icons.checklist_rounded,
          label: 'Capabilities available',
          value: state.hasLoadedCapabilities
              ? '${state.capabilities.where((c) => c.isUsable).length} of ${state.capabilities.length}'
              : '…',
          onTap: () {
            state.openSettingsCategory('Capabilities');
            onGoTo(ShellIndex.settings);
          },
        ),
        const SizedBox(height: UriSpace.sm),
        _StatTile(
          icon: Icons.psychology_outlined,
          label: 'Memory entries',
          value: state.hasLoadedMemory ? '${state.memories.length}' : '…',
          onTap: () {
            state.openSettingsCategory('Memory');
            onGoTo(ShellIndex.settings);
          },
        ),
        const SizedBox(height: UriSpace.xl),
        Text('Recent activity', style: theme.textTheme.headlineSmall),
        const SizedBox(height: UriSpace.sm),
        _RecentActivity(state: state, onGoTo: onGoTo),
      ],
    );
  }
}

/// Phone-layout dashboard: the same real numbers, as a compact
/// horizontal row of small cards above the conversation rather than a
/// full side panel — the conversation itself gets most of the screen.
class _CompactDashboard extends StatelessWidget {
  const _CompactDashboard({required this.state, required this.onGoTo});

  final AppState state;
  final ValueChanged<int> onGoTo;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 84,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          _CompactStat(
            icon: Icons.pending_actions_outlined,
            label: 'Approvals',
            value: '${state.homeSummary?.pendingApprovalCount ?? 0}',
            accent: (state.homeSummary?.pendingApprovalCount ?? 0) > 0,
            onTap: () => onGoTo(ShellIndex.tasks),
          ),
          _CompactStat(
            icon: Icons.hub_outlined,
            label: 'Connected',
            value:
                '${state.homeSummary?.connectedServiceCount ?? 0}/${state.homeSummary?.totalServiceCount ?? 0}',
            onTap: () => onGoTo(ShellIndex.connections),
          ),
          _CompactStat(
            icon: Icons.checklist_rounded,
            label: 'Capable',
            value: state.hasLoadedCapabilities
                ? '${state.capabilities.where((c) => c.isUsable).length}/${state.capabilities.length}'
                : '…',
            onTap: () => onGoTo(ShellIndex.settings),
          ),
          _CompactStat(
            icon: Icons.psychology_outlined,
            label: 'Memory',
            value: state.hasLoadedMemory ? '${state.memories.length}' : '…',
            onTap: () => onGoTo(ShellIndex.settings),
          ),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.onTap,
    this.accent = false,
  });

  final IconData icon;
  final String label;
  final String value;
  final VoidCallback onTap;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(UriRadius.md),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: accent ? colors.accentSoft : colors.surfaceSunken,
                  borderRadius: BorderRadius.circular(UriRadius.sm),
                ),
                alignment: Alignment.center,
                child: Icon(icon, size: 17, color: accent ? colors.accentInk : colors.inkSoft),
              ),
              const SizedBox(width: UriSpace.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(value, style: theme.textTheme.titleMedium),
                    Text(label, style: theme.textTheme.bodySmall),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: colors.inkFaint, size: 18),
            ],
          ),
        ),
      ),
    );
  }
}

class _CompactStat extends StatelessWidget {
  const _CompactStat({
    required this.icon,
    required this.label,
    required this.value,
    required this.onTap,
    this.accent = false,
  });

  final IconData icon;
  final String label;
  final String value;
  final VoidCallback onTap;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(right: UriSpace.sm),
      child: Material(
        color: accent ? colors.accentSoft : colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.sm),
          onTap: onTap,
          child: Container(
            width: 108,
            padding: const EdgeInsets.all(UriSpace.sm),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 16, color: accent ? colors.accentInk : colors.inkSoft),
                const SizedBox(height: 4),
                Text(value, style: theme.textTheme.titleMedium),
                Text(label, style: theme.textTheme.labelSmall),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Real audit-trail activity (see AppState.loadActivity / GET
/// /activity) — not the previous version's client-only "recent turns",
/// which reset on every app restart and never reflected anything the
/// backend could actually evidence.
class _RecentActivity extends StatelessWidget {
  const _RecentActivity({required this.state, required this.onGoTo});

  final AppState state;
  final ValueChanged<int> onGoTo;

  @override
  Widget build(BuildContext context) {
    if (!state.hasLoadedActivity) {
      return const LoadingState();
    }
    if (state.activity.isEmpty) {
      return Text(
        'Once you ask URI to do something, activity will show up here.',
        style: Theme.of(context).textTheme.bodyMedium,
      );
    }
    final colors = UriColors.of(context);
    final recent = state.activity.take(5);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final event in recent)
          Padding(
            padding: const EdgeInsets.only(bottom: UriSpace.sm),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(_iconFor(event.kind), size: 14, color: colors.inkFaint),
                const SizedBox(width: UriSpace.xs),
                Expanded(
                  child: Text(
                    event.summary,
                    style: Theme.of(context).textTheme.bodySmall,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        TextButton(
          onPressed: () => onGoTo(ShellIndex.activity),
          child: const Text('See all activity'),
        ),
      ],
    );
  }

  static IconData _iconFor(ActivityKind kind) {
    switch (kind) {
      case ActivityKind.proposal:
        return Icons.bolt_rounded;
      case ActivityKind.approval:
        return Icons.check_rounded;
      case ActivityKind.execution:
        return Icons.check_circle_outline;
      case ActivityKind.cancellation:
        return Icons.block_rounded;
      case ActivityKind.system:
        return Icons.settings_outlined;
    }
  }
}

import 'package:flutter/material.dart';

import '../../models/connection.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';

/// Truthful companion dashboard per Hybrid UI Frozen Blueprint §4.2.
///
/// Builds exactly 4 metric tiles (Pending Approvals, Unread Email,
/// Connected Services, Brain / Provider) and an actionable Suggested
/// Actions panel. Omit "Upcoming Deadline" and "Halted Workflows".
/// No composer or transcript on Home.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _refreshData();
    });
  }

  void _refreshData() {
    final state = AppStateScope.of(context);
    state.loadHome();
    state.loadConnections();
    state.loadTasks();
    if (!state.hasLoadedUnreadEmailCount) state.loadUnreadEmailCount();
    if (state.activeBrain == null) state.loadActiveBrain();
  }

  void _goTo(int index, {String? settingsCategory}) {
    context.findAncestorStateOfType<AppShellState>()?.goTo(
      index,
      settingsCategory: settingsCategory,
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);

        return RefreshIndicator(
          onRefresh: () async {
            _refreshData();
          },
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(UriSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _GreetingBanner(state: state, onRefresh: _refreshData),
                const SizedBox(height: UriSpace.lg),
                Text(
                  'SYSTEM OVERVIEW',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: colors.inkFaint,
                  ),
                ),
                const SizedBox(height: UriSpace.sm),
                // Exactly 4 tiles per Frozen Blueprint §4.2
                _MetricTilesGrid(
                  state: state,
                  onGoTo: _goTo,
                  onRetry: _refreshData,
                ),
                const SizedBox(height: UriSpace.xl),
                Text(
                  'SUGGESTED ACTIONS',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: colors.inkFaint,
                  ),
                ),
                const SizedBox(height: UriSpace.sm),
                _SuggestedActionsPanel(state: state, onGoTo: _goTo),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _GreetingBanner extends StatelessWidget {
  const _GreetingBanner({required this.state, required this.onRefresh});

  final AppState state;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final username = state.currentUsername ?? 'User';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Welcome back, $username',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: colors.ink,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Here is your current operational status and pending actions.',
                style: TextStyle(
                  fontSize: 13,
                  color: colors.inkSoft,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          icon: const Icon(Icons.refresh, size: 20),
          tooltip: 'Refresh metrics',
          color: colors.inkSoft,
          onPressed: onRefresh,
        ),
      ],
    );
  }
}

/// 4-Tile grid using the reference's .tile/.tile-label/.tile-value/.tile-hint pattern.
class _MetricTilesGrid extends StatelessWidget {
  const _MetricTilesGrid({
    required this.state,
    required this.onGoTo,
    required this.onRetry,
  });

  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final summary = state.homeSummary;

    // Tile 1: Pending Approvals
    final tasksFailed = summary?.tasksFailed ?? state.tasksFetchFailed;
    final pendingCount = summary?.pendingApprovalCount ??
        (tasksFailed ? null : state.tasks.length);
    final String tasksValue;
    final String tasksHint;
    if (state.isLoadingTasks || state.isLoadingHome && summary == null) {
      tasksValue = '…';
      tasksHint = 'Checking pending queue';
    } else if (tasksFailed) {
      tasksValue = 'Unavailable';
      tasksHint = 'Tap to retry';
    } else {
      tasksValue = '$pendingCount';
      tasksHint = (pendingCount ?? 0) > 0
          ? 'Requires your review'
          : 'Queue is clear';
    }

    // Tile 2: Unread Email
    final emailFailed = state.unreadEmailFailed;
    final String emailValue;
    final String emailHint;
    if (!state.hasLoadedUnreadEmailCount) {
      emailValue = '…';
      emailHint = 'Checking inbox';
    } else if (emailFailed) {
      emailValue = 'Unavailable';
      emailHint = 'Connection issue';
    } else if (state.unreadEmailCount == null) {
      emailValue = 'Not connected';
      emailHint = 'Gmail account';
    } else {
      emailValue = '${state.unreadEmailCount}';
      emailHint = (state.unreadEmailCount ?? 0) > 0
          ? 'Unread messages'
          : 'Inbox caught up';
    }

    // Tile 3: Connected Services
    final connectionsFailed =
        summary?.connectionsFailed ?? state.connectionsFetchFailed;
    final connectedCount = summary?.connectedServiceCount ??
        (connectionsFailed
            ? null
            : state.connections
                .where((c) => c.status == ConnectionStatus.connected)
                .length);
    final totalCount = summary?.totalServiceCount ??
        (connectionsFailed ? null : state.connections.length);
    final String connValue;
    final String connHint;
    if (state.isLoadingConnections || state.isLoadingHome && summary == null) {
      connValue = '…';
      connHint = 'Loading connections';
    } else if (connectionsFailed) {
      connValue = 'Unavailable';
      connHint = 'Tap to retry';
    } else {
      connValue = '$connectedCount / $totalCount';
      connHint = 'Active integrations';
    }

    // Tile 4: Brain / Provider
    //
    // Post-Launch Brain Setup Repair: GET /providers/active-brain never
    // returns null - an account that never configured anything still
    // gets back the deployment-wide default provider/model (isConfigured
    // false), so a null-check alone showed that default as if it were a
    // real, user-chosen Active Brain the instant loadActiveBrain()
    // resolved. isConfigured is the real signal; never trust the
    // provider/model fields when it's false.
    final brainFailed = state.activeBrainFailed;
    final activeBrain = state.activeBrain;
    final String brainValue;
    final String brainHint;
    if (brainFailed) {
      brainValue = 'Unavailable';
      brainHint = 'Provider check failed';
    } else if (activeBrain == null || !activeBrain.isConfigured) {
      brainValue = 'No Active Brain';
      brainHint = 'Configure Brain';
    } else {
      brainValue = activeBrain.displayName ?? activeBrain.providerId;
      brainHint = activeBrain.model.isNotEmpty
          ? activeBrain.model
          : 'Active model';
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth > 900 ? 4 : 2;
        final itemWidth = (constraints.maxWidth -
                (crossAxisCount - 1) * UriSpace.md) /
            crossAxisCount;

        return Wrap(
          spacing: UriSpace.md,
          runSpacing: UriSpace.md,
          children: [
            SizedBox(
              width: itemWidth,
              child: _MetricTileCard(
                label: 'PENDING APPROVALS',
                value: tasksValue,
                hint: tasksHint,
                isError: tasksFailed,
                icon: Icons.pending_actions_outlined,
                onTap: tasksFailed ? onRetry : () => onGoTo(ShellIndex.tasks),
              ),
            ),
            SizedBox(
              width: itemWidth,
              child: _MetricTileCard(
                label: 'UNREAD EMAIL',
                value: emailValue,
                hint: emailHint,
                isError: emailFailed,
                icon: Icons.mail_outline,
                onTap: () => onGoTo(ShellIndex.connections),
              ),
            ),
            SizedBox(
              width: itemWidth,
              child: _MetricTileCard(
                label: 'CONNECTED SERVICES',
                value: connValue,
                hint: connHint,
                isError: connectionsFailed,
                icon: Icons.hub_outlined,
                onTap: connectionsFailed
                    ? onRetry
                    : () => onGoTo(ShellIndex.connections),
              ),
            ),
            SizedBox(
              width: itemWidth,
              child: _MetricTileCard(
                label: 'BRAIN / PROVIDER',
                value: brainValue,
                hint: brainHint,
                isError: brainFailed,
                icon: Icons.psychology_outlined,
                onTap: () => onGoTo(ShellIndex.connections),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _MetricTileCard extends StatelessWidget {
  const _MetricTileCard({
    required this.label,
    required this.value,
    required this.hint,
    required this.isError,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final String value;
  final String hint;
  final bool isError;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    return Material(
      color: colors.surface,
      borderRadius: BorderRadius.circular(UriRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(UriRadius.md),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(UriSpace.md),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(UriRadius.md),
            border: Border.all(
              color: isError ? colors.warning.withValues(alpha: 0.5) : colors.border,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                        color: colors.inkFaint,
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    icon,
                    size: 16,
                    color: isError ? colors.warning : colors.inkFaint,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: isError ? colors.warning : colors.ink,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                hint,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 12,
                  color: isError ? colors.warning : colors.inkSoft,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Suggested Actions / Needs Attention panel per §4.2 and COMPONENT_MAPPING.md.
/// Strictly read-only navigation or prompt-prefill; never executes a write on tap.
class _SuggestedActionsPanel extends StatelessWidget {
  const _SuggestedActionsPanel({
    required this.state,
    required this.onGoTo,
  });

  final AppState state;
  final void Function(int, {String? settingsCategory}) onGoTo;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final suggestions = <_SuggestionItem>[];

    final pendingTasks = state.homeSummary?.pendingApprovalCount ?? state.tasks.length;
    if (pendingTasks > 0) {
      suggestions.add(
        _SuggestionItem(
          icon: Icons.pending_actions_outlined,
          title: 'Review $pendingTasks pending approval${pendingTasks > 1 ? 's' : ''}',
          subtitle: 'Safety gate confirmation required before execution proceeds.',
          buttonLabel: 'View Tasks',
          onTap: () => onGoTo(ShellIndex.tasks),
        ),
      );
    }

    final unread = state.unreadEmailCount ?? 0;
    if (unread > 0) {
      suggestions.add(
        _SuggestionItem(
          icon: Icons.mail_outline,
          title: 'Address $unread unread email message${unread > 1 ? 's' : ''}',
          subtitle: 'Urgent communications detected in connected Gmail inbox.',
          buttonLabel: 'Open Chat',
          onTap: () {
            state.setComposerDraft('Summarize my unread emails and draft replies.');
            onGoTo(ShellIndex.chat);
          },
        ),
      );
    }

    if (state.connections.any((c) => c.status == ConnectionStatus.needsAuthorization)) {
      suggestions.add(
        _SuggestionItem(
          icon: Icons.link_off_outlined,
          title: 'Service connections require authorization',
          subtitle: 'Complete OAuth authorization to grant requested capabilities.',
          buttonLabel: 'Connect',
          onTap: () => onGoTo(ShellIndex.connections),
        ),
      );
    }

    // Same isConfigured check as the Brain/Provider tile above -
    // state.activeBrain is never actually null once loaded, and
    // needsBrainSetup only reflects whether *some* provider is reachable
    // (e.g. any local Ollama), not whether this user picked one.
    if (state.needsBrainSetup ||
        state.activeBrain == null ||
        !state.activeBrain!.isConfigured) {
      suggestions.add(
        _SuggestionItem(
          icon: Icons.psychology_outlined,
          title: 'Configure primary Brain provider',
          subtitle: 'Select and verify an active model provider to power URI.',
          buttonLabel: 'Configure',
          onTap: () => onGoTo(ShellIndex.connections),
        ),
      );
    }

    if (suggestions.isEmpty) {
      suggestions.add(
        _SuggestionItem(
          icon: Icons.chat_bubble_outline,
          title: 'All systems nominal',
          subtitle: 'No pending approvals or alerts. Ask URI a question to begin work.',
          buttonLabel: 'Start Conversation',
          onTap: () => onGoTo(ShellIndex.chat),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(UriRadius.md),
        border: Border.all(color: colors.border),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: suggestions.length,
        separatorBuilder: (_, _) => Divider(height: 1, color: colors.border),
        itemBuilder: (context, i) {
          final item = suggestions[i];
          return Padding(
            padding: const EdgeInsets.all(UriSpace.md),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: colors.accentSoft,
                    borderRadius: BorderRadius.circular(UriRadius.sm),
                  ),
                  child: Center(
                    child: Icon(item.icon, size: 18, color: colors.accent),
                  ),
                ),
                const SizedBox(width: UriSpace.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: colors.ink,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        item.subtitle,
                        style: TextStyle(
                          fontSize: 12,
                          color: colors.inkSoft,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: UriSpace.md),
                OutlinedButton(
                  onPressed: item.onTap,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  child: Text(item.buttonLabel, style: const TextStyle(fontSize: 12)),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SuggestionItem {
  const _SuggestionItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.buttonLabel,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String buttonLabel;
  final VoidCallback onTap;
}

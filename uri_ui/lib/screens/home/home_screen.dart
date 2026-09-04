import 'package:flutter/material.dart';

import '../../models/uri_turn.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/status_pill.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _askController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = AppStateScope.of(context);
      state.loadHome();
      state.loadConnections();
    });
  }

  @override
  void dispose() {
    _askController.dispose();
    super.dispose();
  }

  void _goTo(int index) {
    context.findAncestorStateOfType<AppShellState>()?.goTo(index);
  }

  Future<void> _submitAsk() async {
    final text = _askController.text.trim();
    if (text.isEmpty) return;
    _askController.clear();
    final state = AppStateScope.of(context);
    await state.ask(text);
    if (!mounted) return;
    _goTo(ShellIndex.ask);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final summary = state.homeSummary;
        final theme = Theme.of(context);

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 920),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Good to see you.', style: theme.textTheme.displaySmall),
                const SizedBox(height: 6),
                Text(
                  'Tell URI what you need — it will work out how, using what it '
                  'already has access to, and check with you before anything happens.',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: UriSpace.lg),

                // ---- Ask URI ----
                Container(
                  padding: const EdgeInsets.all(UriSpace.md),
                  decoration: BoxDecoration(
                    color: UriColors.surface,
                    borderRadius: BorderRadius.circular(UriRadius.lg),
                    border: Border.all(color: UriColors.border),
                    boxShadow: [
                      BoxShadow(color: UriColors.ink.withValues(alpha: 0.04), blurRadius: 24, offset: const Offset(0, 10)),
                    ],
                  ),
                  child: Row(
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(left: 6, right: 4),
                        child: Icon(Icons.auto_awesome_rounded, size: 18, color: UriColors.accentInk),
                      ),
                      Expanded(
                        child: TextField(
                          controller: _askController,
                          onSubmitted: (_) => _submitAsk(),
                          decoration: const InputDecoration(
                            border: InputBorder.none,
                            hintText: 'Ask URI anything — "draft a note about…", "what\'s pending on…"',
                          ),
                        ),
                      ),
                      ElevatedButton(onPressed: _submitAsk, child: const Text('Ask URI')),
                    ],
                  ),
                ),

                const SizedBox(height: UriSpace.xl),

                // ---- summary row ----
                LayoutBuilder(
                  builder: (context, constraints) {
                    final wide = constraints.maxWidth >= 620;
                    final cards = [
                      _SummaryCard(
                        icon: Icons.pending_actions_outlined,
                        label: 'Pending approvals',
                        value: '${summary?.pendingApprovalCount ?? 0}',
                        onTap: () => _goTo(ShellIndex.tasks),
                        accent: (summary?.pendingApprovalCount ?? 0) > 0,
                      ),
                      _SummaryCard(
                        icon: Icons.hub_outlined,
                        label: 'Connected services',
                        value: '${summary?.connectedServiceCount ?? 0} of ${summary?.totalServiceCount ?? 0}',
                        onTap: () => _goTo(ShellIndex.connections),
                        accent: false,
                      ),
                    ];
                    return wide
                        ? Row(
                            children: [
                              Expanded(child: cards[0]),
                              const SizedBox(width: UriSpace.md),
                              Expanded(child: cards[1]),
                            ],
                          )
                        : Column(
                            children: [
                              cards[0],
                              const SizedBox(height: UriSpace.md),
                              cards[1],
                            ],
                          );
                  },
                ),

                const SizedBox(height: UriSpace.xl),

                // ---- recent work ----
                Row(
                  children: [
                    Text('Recent work', style: theme.textTheme.headlineSmall),
                    const Spacer(),
                    TextButton(onPressed: () => _goTo(ShellIndex.ask), child: const Text('Open Ask URI')),
                  ],
                ),
                const SizedBox(height: UriSpace.sm),
                if (summary == null)
                  const LoadingState()
                else if (summary.recentTurns.isEmpty)
                  EmptyState(
                    icon: Icons.inbox_outlined,
                    title: 'No work yet',
                    message: 'Once you ask URI for something, it will show up here.',
                    action: OutlinedButton(
                      onPressed: () => _goTo(ShellIndex.ask),
                      child: const Text('Ask URI something'),
                    ),
                  )
                else
                  Column(
                    children: [
                      for (final turn in summary.recentTurns)
                        _RecentWorkTile(turn: turn, onTap: () => _goTo(ShellIndex.ask)),
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

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.onTap,
    required this.accent,
  });

  final IconData icon;
  final String label;
  final String value;
  final VoidCallback onTap;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(UriRadius.md),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.lg),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent ? UriColors.accentSoft : UriColors.surfaceSunken,
                  borderRadius: BorderRadius.circular(UriRadius.sm),
                ),
                alignment: Alignment.center,
                child: Icon(icon, size: 19, color: accent ? UriColors.accentInk : UriColors.inkSoft),
              ),
              const SizedBox(width: UriSpace.md),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value, style: theme.textTheme.headlineSmall),
                  Text(label, style: theme.textTheme.bodyMedium),
                ],
              ),
              const Spacer(),
              const Icon(Icons.chevron_right_rounded, color: UriColors.inkFaint),
            ],
          ),
        ),
      ),
    );
  }
}

class _RecentWorkTile extends StatelessWidget {
  const _RecentWorkTile({required this.turn, required this.onTap});

  final UriTurn turn;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.md),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(UriSpace.md),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(turn.userText, style: theme.textTheme.titleMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                      if (turn.proposedAction != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          turn.proposedAction!.title,
                          style: theme.textTheme.bodyMedium,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: UriSpace.sm),
                StatusPill.forStage(turn.stage),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

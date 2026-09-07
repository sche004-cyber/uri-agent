import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show ConversationSummary;
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

/// M18: the user's past conversations, from the durable per-user
/// transcript (GET /history). Each can be resumed (its turns load into
/// the Home conversation and the next message continues that session)
/// or deleted. Read-only reconstruction — nothing is re-run.
class HistorySettingsScreen extends StatefulWidget {
  const HistorySettingsScreen({super.key});

  @override
  State<HistorySettingsScreen> createState() => _HistorySettingsScreenState();
}

class _HistorySettingsScreenState extends State<HistorySettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      AppStateScope.of(context).loadHistory();
    });
  }

  Future<void> _resume(AppState state, String sessionId) async {
    await state.resumeSession(sessionId);
    if (!mounted) return;
    // Jump to Home, which holds the one canonical conversation.
    context.findAncestorStateOfType<AppShellState>()?.goTo(ShellIndex.home);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);

        if (!state.hasLoadedHistory) {
          return const LoadingState(message: 'Loading past conversations…');
        }
        if (state.history.isEmpty) {
          return const EmptyState(
            icon: Icons.forum_outlined,
            title: 'No past conversations',
            message: 'Conversations you have with URI are saved here so you can '
                'reopen or continue them later.',
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final summary in state.history)
              _HistoryTile(
                summary: summary,
                onResume: () => _resume(state, summary.sessionId),
                onDelete: () => state.deleteHistory(summary.sessionId),
              ),
          ],
        );
      },
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({
    required this.summary,
    required this.onResume,
    required this.onDelete,
  });

  final ConversationSummary summary;
  final VoidCallback onResume;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      summary.preview.isEmpty ? '(no messages)' : summary.preview,
                      style: theme.textTheme.titleMedium,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${summary.turnCount} message${summary.turnCount == 1 ? '' : 's'}',
                      style: theme.textTheme.labelSmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              TextButton(onPressed: onResume, child: const Text('Resume')),
              IconButton(
                onPressed: onDelete,
                icon: const Icon(Icons.delete_outline_rounded, size: 18),
                tooltip: 'Delete conversation',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

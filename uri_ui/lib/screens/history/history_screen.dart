import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show ConversationSummary;
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/screen_header.dart';

/// M18/M19: the user's past conversations with URI, from the durable
/// per-user transcript (GET /history) — a top-level destination (not
/// nested inside Settings) so it is genuinely visible, not three taps
/// deep. Each conversation can be resumed (its turns load into the
/// Home conversation and the next message continues that session) or
/// deleted. Read-only reconstruction — nothing is re-run.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
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

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const ScreenHeader(
                title: 'History',
                subtitle: 'Your past conversations with URI — reopen, continue, '
                    'or delete them.',
              ),
              if (!state.hasLoadedHistory)
                const LoadingState(message: 'Loading past conversations…')
              else if (state.history.isEmpty)
                const EmptyState(
                  icon: Icons.forum_outlined,
                  title: 'No past conversations',
                  message: 'Conversations you have with URI are saved here so '
                      'you can reopen or continue them later.',
                )
              else
                for (final summary in state.history)
                  _HistoryTile(
                    summary: summary,
                    onResume: () => _resume(state, summary.sessionId),
                    onDelete: () => state.deleteHistory(summary.sessionId),
                  ),
            ],
          ),
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

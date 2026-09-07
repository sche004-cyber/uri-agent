import 'package:flutter/material.dart';

import '../../models/memory_entry.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

/// Real CRUD against GET/POST/DELETE /memory — every fact shown here
/// is something URI actually holds and could use, never a mock list.
/// consent is always "user_provided" (see server.py's add_memory):
/// there is no path yet for URI to write a memory on its own, so this
/// screen has nothing to distinguish for that case.
class MemorySettingsScreen extends StatefulWidget {
  const MemorySettingsScreen({super.key});

  @override
  State<MemorySettingsScreen> createState() => _MemorySettingsScreenState();
}

class _MemorySettingsScreenState extends State<MemorySettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedMemory) state.loadMemory();
    });
  }

  Future<void> _openAddDialog(AppState state) async {
    final categoryController = TextEditingController();
    final contentController = TextEditingController();

    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Remember something'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: categoryController,
              decoration: const InputDecoration(labelText: 'Category', hintText: 'e.g. preference'),
            ),
            const SizedBox(height: UriSpace.sm),
            TextField(
              controller: contentController,
              decoration: const InputDecoration(labelText: 'What should URI remember?'),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (saved != true || !mounted) return;
    await state.addMemory(
      category: categoryController.text.trim().isEmpty ? 'general' : categoryController.text.trim(),
      content: contentController.text.trim(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: state.isSavingMemory ? null : () => _openAddDialog(state),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Remember something'),
              ),
            ),
            if (state.memoryError != null) ...[
              const SizedBox(height: UriSpace.sm),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(UriSpace.md),
                decoration: BoxDecoration(
                  color: colors.dangerSoft,
                  borderRadius: BorderRadius.circular(UriRadius.sm),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline_rounded, size: 16, color: colors.danger),
                    const SizedBox(width: UriSpace.sm),
                    Expanded(child: Text(state.memoryError!, style: TextStyle(color: colors.danger))),
                    IconButton(
                      onPressed: state.clearMemoryError,
                      icon: const Icon(Icons.close_rounded, size: 16),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: UriSpace.md),
            if (!state.hasLoadedMemory)
              const LoadingState(message: 'Loading memory…')
            else if (state.memories.isEmpty)
              const EmptyState(
                icon: Icons.psychology_outlined,
                title: 'Nothing remembered yet',
                message: 'Anything you explicitly ask URI to remember will show up here.',
              )
            else ...[
              // M18: URI-proposed memories awaiting the user's decision.
              // Shown first, with Confirm/Reject — until confirmed they
              // never influence URI (the backend keeps them
              // pending_confirmation and excludes them from
              // personalization).
              for (final entry in state.memories
                  .where((m) => m.consent == 'pending_confirmation'))
                _MemoryTile(
                  entry: entry,
                  pending: true,
                  onConfirm: () => state.confirmMemory(entry.memoryId),
                  onReject: () => state.rejectMemory(entry.memoryId),
                  onDelete: () => state.deleteMemory(entry.memoryId),
                ),
              // Established memories.
              for (final entry in state.memories
                  .where((m) => m.consent != 'pending_confirmation'))
                _MemoryTile(
                  entry: entry,
                  pending: false,
                  onConfirm: () {},
                  onReject: () {},
                  onDelete: () => state.deleteMemory(entry.memoryId),
                ),
            ],
          ],
        );
      },
    );
  }
}

class _MemoryTile extends StatelessWidget {
  const _MemoryTile({
    required this.entry,
    required this.pending,
    required this.onConfirm,
    required this.onReject,
    required this.onDelete,
  });

  final MemoryEntry entry;
  final bool pending;
  final VoidCallback onConfirm;
  final VoidCallback onReject;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(entry.category, style: theme.textTheme.labelSmall),
                            if (pending) ...[
                              const SizedBox(width: UriSpace.sm),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                decoration: BoxDecoration(
                                  color: colors.warningSoft,
                                  borderRadius: BorderRadius.circular(999),
                                ),
                                child: Text(
                                  'URI suggests remembering',
                                  style: theme.textTheme.labelSmall?.copyWith(color: colors.warning),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(entry.content, style: theme.textTheme.bodyLarge),
                        if (entry.notes != null && entry.notes!.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(entry.notes!, style: theme.textTheme.bodyMedium),
                        ],
                      ],
                    ),
                  ),
                  if (!pending)
                    IconButton(
                      onPressed: onDelete,
                      icon: const Icon(Icons.delete_outline_rounded, size: 18),
                      tooltip: 'Forget this',
                    ),
                ],
              ),
              if (pending) ...[
                const SizedBox(height: UriSpace.sm),
                Row(
                  children: [
                    ElevatedButton(onPressed: onConfirm, child: const Text('Confirm')),
                    const SizedBox(width: UriSpace.sm),
                    OutlinedButton(onPressed: onReject, child: const Text('Reject')),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

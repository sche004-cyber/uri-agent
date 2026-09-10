import 'package:flutter/material.dart';

import '../../models/memory_entry.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/loading_state.dart';

/// The exact category vocabulary user_memory.py's VALID_CATEGORIES
/// accepts - kept as a fixed picker rather than free text, because a
/// category outside this set is unconditionally rejected by the
/// backend (see MemoryValidationError). A free-text field's plausible
/// default ("general") is not actually one of these values and would
/// always be rejected - this picker exists specifically so that
/// mismatch can never happen.
const _kMemoryCategories = <String, String>{
  'preference': 'Preference',
  'interest': 'Interest',
  'interaction_pattern': 'Interaction pattern',
  'explicit_statement': 'Explicit statement',
  'other': 'Other',
};

/// Real CRUD against GET/POST/PUT/DELETE /memory — every fact shown
/// here is something URI actually holds and could use, never a mock
/// list. consent is always "user_provided" for a user-created entry
/// (see server.py's add_memory): there is no path yet for URI to write
/// a memory on its own, so this screen has nothing to distinguish for
/// that case. Editing (PUT) preserves the existing consent value -
/// this screen never changes it.
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
    final result = await _showMemoryDialog(title: 'Remember something', saveLabel: 'Save');
    if (result == null || !mounted) return;
    await state.addMemory(category: result.category, content: result.content);
  }

  Future<void> _openEditDialog(AppState state, MemoryEntry entry) async {
    final result = await _showMemoryDialog(
      title: 'Edit this memory',
      saveLabel: 'Save changes',
      initialCategory: entry.category,
      initialContent: entry.content,
    );
    if (result == null || !mounted) return;
    await state.updateMemory(
      memoryId: entry.memoryId,
      category: result.category,
      content: result.content,
      confidence: entry.confidence,
      notes: entry.notes,
    );
  }

  Future<_MemoryDialogResult?> _showMemoryDialog({
    required String title,
    required String saveLabel,
    String? initialCategory,
    String? initialContent,
  }) async {
    final contentController = TextEditingController(text: initialContent ?? '');
    // Falls back to the first valid category rather than an invalid
    // default - every value this picker can ever produce is one the
    // backend actually accepts (see _kMemoryCategories's own doc).
    var category = _kMemoryCategories.containsKey(initialCategory)
        ? initialCategory!
        : _kMemoryCategories.keys.first;

    return showDialog<_MemoryDialogResult>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButtonFormField<String>(
                initialValue: category,
                decoration: const InputDecoration(labelText: 'Category'),
                items: [
                  for (final entry in _kMemoryCategories.entries)
                    DropdownMenuItem(value: entry.key, child: Text(entry.value)),
                ],
                onChanged: (value) {
                  if (value != null) setDialogState(() => category = value);
                },
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
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(dialogContext).pop(
                _MemoryDialogResult(category, contentController.text.trim()),
              ),
              child: Text(saveLabel),
            ),
          ],
        ),
      ),
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
                  onEdit: null,
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
                  onEdit: () => _openEditDialog(state, entry),
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
    required this.onEdit,
    required this.onDelete,
  });

  final MemoryEntry entry;
  final bool pending;
  final VoidCallback onConfirm;
  final VoidCallback onReject;
  final VoidCallback? onEdit;
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
                            Text(
                              _kMemoryCategories[entry.category] ?? entry.category,
                              style: theme.textTheme.labelSmall,
                            ),
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
                  if (!pending && onEdit != null)
                    IconButton(
                      onPressed: onEdit,
                      icon: const Icon(Icons.edit_outlined, size: 18),
                      tooltip: 'Edit this',
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

class _MemoryDialogResult {
  const _MemoryDialogResult(this.category, this.content);

  final String category;
  final String content;
}

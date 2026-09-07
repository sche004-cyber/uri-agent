import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/file_picker_service.dart';
import '../../services/uri_client.dart' show Attachment;
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/turn_card.dart';

class AskUriScreen extends StatefulWidget {
  const AskUriScreen({super.key, this.filePicker});

  /// M16: how the user chooses a file to attach. Injected (see
  /// main.dart) rather than imported, so this screen — and every
  /// widget test that builds it — stays free of the file_picker
  /// plugin. When null, the attach control is simply not offered:
  /// the UI never shows an affordance it cannot actually fulfil.
  final FilePickerFn? filePicker;

  @override
  State<AskUriScreen> createState() => _AskUriScreenState();
}

class _AskUriScreenState extends State<AskUriScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Jump to the latest turn if arriving here with existing history
    // (e.g. after asking something from Home).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _openConnections(String connectionId) {
    context.findAncestorStateOfType<AppShellState>()?.goTo(ShellIndex.connections);
  }

  Future<void> _send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    _controller.clear();
    final state = AppStateScope.of(context);
    await state.ask(trimmed);
    if (!mounted) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);

        return Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(UriSpace.xl, UriSpace.xl, UriSpace.xl, 0),
              child: ScreenHeader(
                title: 'Ask URI',
                subtitle:
                    'Tell URI what you need. It will explain what it understood '
                    'before it proposes doing anything.',
              ),
            ),
            Expanded(
              child: state.conversation.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(UriSpace.xl),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 460),
                          child: const EmptyState(
                            icon: Icons.forum_outlined,
                            title: 'Nothing here yet',
                            message:
                                'Ask about anything you need help with — a document, an email, '
                                'a schedule question, a record lookup. URI will work out what to '
                                'do from what you actually type, not from a fixed menu.',
                          ),
                        ),
                      ),
                    )
                  : ListView.separated(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(horizontal: UriSpace.xl, vertical: UriSpace.md),
                      itemCount: state.conversation.length,
                      separatorBuilder: (_, _) => const SizedBox(height: UriSpace.md),
                      itemBuilder: (context, index) {
                        final turn = state.conversation[index];
                        return TurnCard(
                          turn: turn,
                          onApprove: () => state.approve(turn.id),
                          onCancel: () => state.cancel(turn.id),
                          onConnectService: _openConnections,
                        );
                      },
                    ),
            ),
            _Composer(
              controller: _controller,
              sending: state.isSendingAsk,
              onSend: _send,
              attachments: state.attachments,
              uploading: state.isUploadingAttachment,
              attachmentError: state.attachmentError,
              onAttach: widget.filePicker == null
                  ? null
                  : () => _attach(state),
              onRemoveAttachment: state.removeAttachment,
              onDismissAttachmentError: state.clearAttachmentError,
            ),
          ],
        );
      },
    );
  }

  /// M16: opens the platform file picker and hands the bytes to
  /// [AppState.attachFile]. Deliberately does NOT filter by extension
  /// here — the backend's allow-list is the single source of truth for
  /// what is acceptable (see file_store.py), so the user gets one
  /// consistent, real reason for a rejection rather than a client-side
  /// rule that could drift out of step with it.
  Future<void> _attach(AppState state) async {
    final picker = widget.filePicker;
    if (picker == null) return;

    final file = await picker();
    if (file == null) return;

    await state.attachFile(filename: file.name, bytes: file.bytes);
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
    required this.attachments,
    required this.uploading,
    required this.attachmentError,
    required this.onAttach,
    required this.onRemoveAttachment,
    required this.onDismissAttachmentError,
  });

  final TextEditingController controller;
  final bool sending;
  final ValueChanged<String> onSend;
  final List<Attachment> attachments;
  final bool uploading;
  final String? attachmentError;
  /// Null when no picker is available — the attach control is then
  /// not rendered at all rather than shown inert.
  final VoidCallback? onAttach;
  final ValueChanged<String> onRemoveAttachment;
  final VoidCallback onDismissAttachmentError;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(UriSpace.lg),
      decoration: const BoxDecoration(
        color: UriColors.surface,
        border: Border(top: BorderSide(color: UriColors.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (attachmentError != null)
            _AttachmentError(
              message: attachmentError!,
              onDismiss: onDismissAttachmentError,
            ),
          if (attachments.isNotEmpty)
            _AttachmentStrip(
              attachments: attachments,
              onRemove: onRemoveAttachment,
            ),
          Row(
            children: [
              if (onAttach != null)
                IconButton(
                  onPressed: (sending || uploading) ? null : onAttach,
                  tooltip: 'Attach a file',
                  icon: uploading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.attach_file_rounded),
                ),
              Expanded(
                child: TextField(
                  controller: controller,
                  minLines: 1,
                  maxLines: 4,
                  enabled: !sending,
                  onSubmitted: onSend,
                  decoration: const InputDecoration(
                    hintText: 'Ask URI to help with something…',
                  ),
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              IconButton.filled(
                onPressed: sending ? null : () => onSend(controller.text),
                style: IconButton.styleFrom(
                  backgroundColor: UriColors.accent,
                  disabledBackgroundColor: UriColors.border,
                  padding: const EdgeInsets.all(14),
                ),
                icon: sending
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(
                        Icons.arrow_upward_rounded,
                        color: Colors.white,
                      ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// The files currently attached to this conversation. Shows exactly
/// what URI actually holds — each chip is a real stored file the
/// backend confirmed, never an optimistic local entry.
class _AttachmentStrip extends StatelessWidget {
  const _AttachmentStrip({required this.attachments, required this.onRemove});

  final List<Attachment> attachments;
  final ValueChanged<String> onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Wrap(
        spacing: UriSpace.sm,
        runSpacing: UriSpace.sm,
        children: [
          for (final attachment in attachments)
            Chip(
              avatar: const Icon(Icons.description_outlined, size: 18),
              label: Text(
                '${attachment.filename} · ${_formatSize(attachment.sizeBytes)}',
              ),
              onDeleted: () => onRemove(attachment.fileId),
              deleteButtonTooltipMessage: 'Remove attachment',
            ),
        ],
      ),
    );
  }

  static String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).round()} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

/// The backend's real rejection reason (unsupported type, too large,
/// empty) shown verbatim — never a generic "upload failed".
class _AttachmentError extends StatelessWidget {
  const _AttachmentError({required this.message, required this.onDismiss});

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 18),
          const SizedBox(width: UriSpace.sm),
          Expanded(child: Text(message)),
          IconButton(
            onPressed: onDismiss,
            icon: const Icon(Icons.close_rounded, size: 18),
            tooltip: 'Dismiss',
          ),
        ],
      ),
    );
  }
}

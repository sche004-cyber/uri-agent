import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/attachment_opener_service.dart';
import '../../services/file_picker_service.dart';
import '../../services/uri_client.dart' show Attachment, ProviderEntry;
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/turn_card.dart';

/// The canonical Ask URI surface. Home composes [UriConversationPane] and
/// [UriCommandDock] directly for the dashboard, while this wrapper retains
/// the focused conversation view. Both paths use the same [AppState].
class AskUriScreen extends StatelessWidget {
  const AskUriScreen({super.key, this.filePicker, this.attachmentOpener});

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Expanded(child: UriConversationPane(attachmentOpener: attachmentOpener)),
      UriCommandDock(filePicker: filePicker),
    ],
  );
}

/// The one persisted transcript. This has no composer: [UriCommandDock] is
/// mounted once by its host, so no UI can create a second chat state.
class UriConversationPane extends StatefulWidget {
  const UriConversationPane({
    super.key,
    this.attachmentOpener,
    this.compact = false,
  });

  final AttachmentOpenerFn? attachmentOpener;
  final bool compact;

  @override
  State<UriConversationPane> createState() => _UriConversationPaneState();
}

class _UriConversationPaneState extends State<UriConversationPane> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToLatest());
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToLatest() {
    if (mounted && _scrollController.hasClients) {
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    }
  }

  void _openConnections() {
    context.findAncestorStateOfType<AppShellState>()?.goTo(
      ShellIndex.connections,
    );
  }

  Future<void> _openAttachment(AppState state, Attachment attachment) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    final List<int> bytes;
    try {
      bytes = await state.downloadAttachment(attachment.fileId);
    } catch (error) {
      if (mounted) {
        messenger?.showSnackBar(
          SnackBar(
            content: Text('Could not open ${attachment.filename}: $error'),
          ),
        );
      }
      return;
    }

    final opener = widget.attachmentOpener;
    if (opener == null) {
      if (mounted) {
        messenger?.showSnackBar(
          SnackBar(
            content: Text(
              '${attachment.filename} downloaded, but this build cannot open it.',
            ),
          ),
        );
      }
      return;
    }

    final outcome = await opener(filename: attachment.filename, bytes: bytes);
    if (!mounted) return;
    switch (outcome) {
      case AttachmentOpenOutcome.opened:
        break;
      case AttachmentOpenOutcome.noViewerAvailable:
        messenger?.showSnackBar(
          SnackBar(
            content: Text(
              'No app on this device can open ${attachment.filename}.',
            ),
          ),
        );
      case AttachmentOpenOutcome.failed:
        messenger?.showSnackBar(
          SnackBar(content: Text('Could not open ${attachment.filename}.')),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final horizontal = widget.compact ? UriSpace.md : UriSpace.xl;
        if (state.conversation.isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(UriSpace.xl),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 460),
                child: const EmptyState(
                  icon: Icons.forum_outlined,
                  title: 'Start a conversation',
                  message: 'Ask URI about an email, document, schedule, or record. URI will use the capabilities the runtime makes available.',
                ),
              ),
            ),
          );
        }

        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToLatest());
        return Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: state.isSendingAsk ? null : state.startNewChat,
                icon: const Icon(Icons.add_comment_outlined, size: 18),
                label: const Text('New chat'),
              ),
            ),
            Expanded(
              child: ListView.separated(
                controller: _scrollController,
                padding: EdgeInsets.symmetric(
                  horizontal: horizontal,
                  vertical: UriSpace.md,
                ),
                itemCount: state.conversation.length,
                separatorBuilder: (_, _) => const SizedBox(height: UriSpace.md),
                itemBuilder: (context, index) {
                  final turn = state.conversation[index];
                  return TurnCard(
                    turn: turn,
                    onApprove: () => state.approve(turn.id),
                    onCancel: () => state.cancel(turn.id),
                    onConnectService: (_) => _openConnections(),
                    onOpenAttachment: (attachment) =>
                        _openAttachment(state, attachment),
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Persistent command dock for the real, approval-aware `/ask` path.
class UriCommandDock extends StatefulWidget {
  const UriCommandDock({
    super.key,
    this.filePicker,
    this.compact = false,
    this.showTip = false,
  });

  final FilePickerFn? filePicker;
  final bool compact;
  final bool showTip;

  @override
  State<UriCommandDock> createState() => _UriCommandDockState();
}

class _UriCommandDockState extends State<UriCommandDock> {
  final _controller = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
      (_) => AppStateScope.of(context).loadProviderInventory(),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    _controller.clear();
    await AppStateScope.of(context).ask(trimmed);
  }

  Future<void> _attach(AppState state) async {
    final picker = widget.filePicker;
    if (picker == null) return;
    final file = await picker();
    if (file != null) {
      await state.attachFile(filename: file.name, bytes: file.bytes);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        return _ComposerBody(
          controller: _controller,
          sending: state.isSendingAsk,
          onSend: _send,
          attachments: state.attachments,
          uploading: state.isUploadingAttachment,
          attachmentError: state.attachmentError,
          onAttach: widget.filePicker == null ? null : () => _attach(state),
          onRemoveAttachment: state.removeAttachment,
          onDismissAttachmentError: state.clearAttachmentError,
          compact: widget.compact,
          showTip: widget.showTip,
          modelOverride: state.conversationModelOverride,
          providers: state.providerInventory,
          onChooseModel: state.setConversationModelOverride,
        );
      },
    );
  }
}

class _ComposerBody extends StatelessWidget {
  const _ComposerBody({
    required this.controller,
    required this.sending,
    required this.onSend,
    required this.attachments,
    required this.uploading,
    required this.attachmentError,
    required this.onAttach,
    required this.onRemoveAttachment,
    required this.onDismissAttachmentError,
    required this.compact,
    required this.showTip,
    required this.modelOverride,
    required this.providers,
    required this.onChooseModel,
  });

  final TextEditingController controller;
  final bool sending;
  final ValueChanged<String> onSend;
  final List<Attachment> attachments;
  final bool uploading;
  final String? attachmentError;
  final VoidCallback? onAttach;
  final ValueChanged<String> onRemoveAttachment;
  final VoidCallback onDismissAttachmentError;
  final bool compact;
  final bool showTip;
  final Object? modelOverride;
  final List<ProviderEntry> providers;
  final ValueChanged<Object?> onChooseModel;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      padding: EdgeInsets.fromLTRB(
        compact ? UriSpace.md : UriSpace.lg,
        UriSpace.sm,
        compact ? UriSpace.md : UriSpace.lg,
        compact ? UriSpace.md : UriSpace.lg,
      ),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xff061a29) : colors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isDark ? const Color(0xff198ae1) : colors.accent,
        ),
        boxShadow: isDark
            ? const [BoxShadow(color: Color(0x380f85ff), blurRadius: 15)]
            : [
                BoxShadow(
                  color: colors.accent.withValues(alpha: .12),
                  blurRadius: 15,
                ),
              ],
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
                child: Focus(
                  onKeyEvent: (node, event) {
                    if (event is KeyDownEvent &&
                        event.logicalKey == LogicalKeyboardKey.enter &&
                        !HardwareKeyboard.instance.isShiftPressed) {
                      if (!sending) onSend(controller.text);
                      return KeyEventResult.handled;
                    }
                    return KeyEventResult.ignored;
                  },
                  child: TextField(
                    controller: controller,
                    style: TextStyle(
                      color: isDark ? const Color(0xffccdded) : colors.ink,
                    ),
                    minLines: 1,
                    maxLines: compact ? 5 : 10,
                    keyboardType: TextInputType.multiline,
                    textInputAction: TextInputAction.newline,
                    enabled: !sending,
                    decoration: const InputDecoration(
                      hintText: 'Ask URI anything…',
                    ),
                  ),
                ),
              ),
              _ModelSelectorChip(
                value: modelOverride,
                providers: providers,
                onChanged: onChooseModel,
              ),
              Tooltip(
                message: 'Voice input is not available yet',
                child: Icon(
                  Icons.mic_none,
                  color: isDark ? const Color(0xffaac5d8) : colors.inkFaint,
                  size: 22,
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              Tooltip(
                message: 'Send to URI',
                child: IconButton.filled(
                  onPressed: sending ? null : () => onSend(controller.text),
                  style: IconButton.styleFrom(
                    backgroundColor: const Color(0xff198aff),
                    disabledBackgroundColor: colors.border,
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
                          Icons.arrow_forward_rounded,
                          color: Colors.white,
                        ),
                ),
              ),
            ],
          ),
          if (showTip)
            Padding(
              padding: const EdgeInsets.only(top: UriSpace.xs, left: 44),
              child: Text(
                'Tip: You can ask in natural language, for example: "Summarize my unread emails" or "Create a plan for next week." · Shift+Enter for a new line.',
                style: Theme.of(context).textTheme.labelSmall
                    ?.copyWith(color: UriColors.of(context).inkFaint),
              ),
            ),
        ],
      ),
    );
  }
}

class _AttachmentStrip extends StatelessWidget {
  const _AttachmentStrip({required this.attachments, required this.onRemove});

  final List<Attachment> attachments;
  final ValueChanged<String> onRemove;

  @override
  Widget build(BuildContext context) => Padding(
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

  static String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).round()} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}

/// The chat's only interactive model control.  It writes a session-level
/// request preference; the global Active Brain is deliberately untouched.
class _ModelSelectorChip extends StatelessWidget {
  const _ModelSelectorChip({
    required this.value,
    required this.providers,
    required this.onChanged,
  });
  final Object? value;
  final List<ProviderEntry> providers;
  final ValueChanged<Object?> onChanged;

  String get _label => value is Map
      ? ((value as Map)['model'] as String? ?? 'URI Auto')
      : 'URI Auto';

  @override
  Widget build(BuildContext context) => PopupMenuButton<Object?>(
    tooltip: 'Choose conversation model',
    onSelected: onChanged,
    itemBuilder: (context) => [
      const PopupMenuItem<Object?>(
        value: 'auto',
        child: _ModelChoice(
          label: 'URI Auto',
          detail: 'Auto routing',
          enabled: true,
        ),
      ),
      const PopupMenuDivider(),
      const PopupMenuItem<Object?>(
        enabled: false,
        child: Text(
          'Model choice can be changed from conversation without rewriting global defaults.',
        ),
      ),
      for (final provider in providers)
        for (final model in provider.models)
          PopupMenuItem<Object?>(
            value: model.verified
                ? {'provider_id': provider.providerId, 'model': model.modelId}
                : null,
            enabled: model.verified,
            child: _ModelChoice(
              label: model.displayName,
              detail: model.verified ? provider.displayName : 'Not verified',
              enabled: model.verified,
            ),
          ),
    ],
    // RawChip (not Chip) so this control has a distinct widget type from
    // the attachment strip's Chip widgets below — attachment_ui_test.dart
    // asserts on find.byType(Chip) as a regression guard for the attach
    // flow, and this selector must never be counted as an attachment chip.
    child: RawChip(
      avatar: const Icon(Icons.tune_rounded, size: 16),
      label: Text(_label, overflow: TextOverflow.ellipsis),
    ),
  );
}

class _ModelChoice extends StatelessWidget {
  const _ModelChoice({
    required this.label,
    required this.detail,
    required this.enabled,
  });
  final String label;
  final String detail;
  final bool enabled;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Icon(
        Icons.circle,
        size: 10,
        color: enabled ? Colors.teal : Colors.red.withValues(alpha: .55),
      ),
      const SizedBox(width: UriSpace.sm),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label),
            Text(detail, style: Theme.of(context).textTheme.labelSmall),
          ],
        ),
      ),
    ],
  );
}

class _AttachmentError extends StatelessWidget {
  const _AttachmentError({required this.message, required this.onDismiss});

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => Padding(
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

import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/turn_card.dart';

class AskUriScreen extends StatefulWidget {
  const AskUriScreen({super.key});

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
            _Composer(controller: _controller, sending: state.isSendingAsk, onSend: _send),
          ],
        );
      },
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({required this.controller, required this.sending, required this.onSend});

  final TextEditingController controller;
  final bool sending;
  final ValueChanged<String> onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(UriSpace.lg),
      decoration: const BoxDecoration(
        color: UriColors.surface,
        border: Border(top: BorderSide(color: UriColors.border)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              minLines: 1,
              maxLines: 4,
              enabled: !sending,
              onSubmitted: onSend,
              decoration: const InputDecoration(hintText: 'Ask URI to help with something…'),
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
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.arrow_upward_rounded, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

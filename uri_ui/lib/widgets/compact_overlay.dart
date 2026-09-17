import 'package:flutter/material.dart';

import '../screens/ask/ask_uri_screen.dart';
import '../services/app_state_scope.dart';
import '../services/attachment_opener_service.dart';
import '../services/file_picker_service.dart';
import '../theme/uri_theme.dart';
import 'uri_wordmark.dart';

/// Compact is a presentation-mode switch, never a new session. It reuses
/// the exact same [UriConversationPane]/[UriCommandDock] widgets the
/// Workspace Chat destination mounts — both read/write [AppState]
/// directly (session, transcript, composer draft, attachments, model
/// override, in-flight request), so toggling into or out of Compact can
/// never create a second session, duplicate a request, or drop any of
/// that state.
///
/// This widget still fills its parent (`Positioned.fill`) exactly as it
/// did after the Live UX Repair - what makes Compact "small" again is
/// no longer a floating card drawn over a still full-size Workspace
/// window (the original Frozen Blueprint §4.4 treatment), nor the Live
/// UX Repair's full-bleed-over-a-large-window fill it replaced that
/// with. Instead, `app.dart`'s [UriHome] resizes the real OS window down
/// to a small, fixed, non-resizable companion size the moment Compact
/// engages (see `services/platform_window_controller.dart`), and
/// restores the Workspace window's previous size/position on Expand -
/// so this widget filling its parent is exactly correct, because its
/// parent (the window) is now genuinely small. "Expand to Workspace"
/// ([_CompactHeader]'s button) remains the one, clear way back.
class CompactOverlay extends StatelessWidget {
  const CompactOverlay({super.key, this.filePicker, this.attachmentOpener});

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final state = AppStateScope.of(context);

    return Positioned.fill(
      child: Material(
        color: colors.canvas,
        child: Column(
          children: [
            _CompactHeader(onExpand: () => state.setCompact(false)),
            Expanded(
              child: UriConversationPane(
                attachmentOpener: attachmentOpener,
                compact: true,
              ),
            ),
            UriCommandDock(filePicker: filePicker, compact: true),
          ],
        ),
      ),
    );
  }
}

class _CompactHeader extends StatelessWidget {
  const _CompactHeader({required this.onExpand});

  final VoidCallback onExpand;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        border: Border(bottom: BorderSide(color: colors.border)),
      ),
      child: Row(
        children: [
          // Live UX Repair §12 (branding consistency): the same
          // canonical UriWordmark every other screen uses, not a plain
          // "URI" text label - Compact is the app's actual active UI
          // now (see this file's own class doc), not a lesser surface
          // that gets a different mark.
          const Expanded(child: UriWordmark(markSize: 20)),
          IconButton(
            icon: const Icon(Icons.open_in_full_rounded, size: 16),
            tooltip: 'Expand to Workspace',
            onPressed: onExpand,
            color: colors.inkSoft,
            splashRadius: 16,
          ),
        ],
      ),
    );
  }
}

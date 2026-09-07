import 'package:flutter/material.dart';

import '../services/app_state.dart' show BackendConnectionStatus;
import '../theme/uri_theme.dart';

/// Prototype 2 (multi-client + runtime awareness): lets a device be
/// pointed at a specific backend address, and proves reconnect/
/// disconnect with a clear, explicit "Test connection" action rather
/// than only surfacing connectivity problems as a failed Ask URI
/// request later.
///
/// Shared, not duplicated: used both by the authenticated
/// Settings > "URI server" section and by [BootstrapScreen]
/// (see screens/bootstrap/bootstrap_screen.dart) - the same widget,
/// wired to the same AppState.setBaseUrl/checkConnection methods, so
/// there is exactly one implementation of "type an address, test it,
/// save it" in this app.
class ServerAddressSection extends StatefulWidget {
  const ServerAddressSection({
    super.key,
    required this.baseUrl,
    required this.connectionStatus,
    required this.connectionErrorDetail,
    required this.onSave,
    required this.onTestConnection,
  });

  final String baseUrl;
  final BackendConnectionStatus connectionStatus;
  final String? connectionErrorDetail;
  final ValueChanged<String> onSave;

  /// Tests the given address as typed - see AppState.checkConnection's
  /// addressOverride. Called with whatever is currently in the text
  /// field, regardless of whether [onSave] has been pressed yet.
  final Future<bool> Function(String address) onTestConnection;

  @override
  State<ServerAddressSection> createState() => _ServerAddressSectionState();
}

class _ServerAddressSectionState extends State<ServerAddressSection> {
  late final TextEditingController _controller = TextEditingController(text: widget.baseUrl);
  bool _isTesting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() => _isTesting = true);
    // Fix: test whatever is currently typed, not whatever was last
    // saved - a user should be able to check an address before
    // committing to it (see the diagnosis this fixes: Test Connection
    // previously ignored unsaved edits and silently tested the old/
    // default address instead).
    await widget.onTestConnection(_controller.text.trim());
    if (mounted) setState(() => _isTesting = false);
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final showDetail =
        widget.connectionStatus == BackendConnectionStatus.unreachable &&
        widget.connectionErrorDetail != null &&
        widget.connectionErrorDetail!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _controller,
          decoration: const InputDecoration(
            labelText: 'Backend address',
            hintText: 'http://192.168.1.23:8000',
          ),
          onSubmitted: widget.onSave,
        ),
        const SizedBox(height: UriSpace.sm),
        // Wrap, not Row: at phone-narrow widths (this section is now
        // reused both in Settings and in the pre-login bootstrap
        // screen's narrower card - see screens/bootstrap/
        // bootstrap_screen.dart) three inline controls don't reliably
        // fit on one line: Save/Test connection/the status badge must
        // be able to flow onto a second line instead of overflowing.
        Wrap(
          spacing: UriSpace.sm,
          runSpacing: UriSpace.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            ElevatedButton(
              onPressed: () => widget.onSave(_controller.text.trim()),
              child: const Text('Save'),
            ),
            OutlinedButton(
              onPressed: _isTesting ? null : _testConnection,
              child: _isTesting
                  ? const SizedBox(
                      height: 14,
                      width: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Test connection'),
            ),
            ConnectionStatusBadge(status: widget.connectionStatus),
          ],
        ),
        // Kept deliberately simple - one small caption line, only shown
        // for an actual failure with something specific to say, never
        // a redesign of the status badge itself.
        if (showDetail) ...[
          const SizedBox(height: UriSpace.xs),
          Text(
            widget.connectionErrorDetail!,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: colors.inkFaint),
          ),
        ],
      ],
    );
  }
}

class ConnectionStatusBadge extends StatelessWidget {
  const ConnectionStatusBadge({super.key, required this.status});

  final BackendConnectionStatus status;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final (label, color, background) = switch (status) {
      BackendConnectionStatus.reachable => ('Connected', colors.success, colors.successSoft),
      BackendConnectionStatus.unreachable => ('Not reachable', colors.danger, colors.dangerSoft),
      BackendConnectionStatus.unknown => ('Not tested yet', colors.inkFaint, colors.surfaceSunken),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: UriSpace.sm, vertical: 4),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(UriRadius.sm)),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../models/connection.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/loading_state.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_pill.dart';

class ConnectionsScreen extends StatefulWidget {
  const ConnectionsScreen({super.key});

  @override
  State<ConnectionsScreen> createState() => _ConnectionsScreenState();
}

class _ConnectionsScreenState extends State<ConnectionsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = AppStateScope.of(context);
      state.loadConnections();
    });
  }

  /// Actually calls the backend's authorize endpoint (see
  /// AppState.authorizeConnection / server.py's authorize_connection)
  /// and always shows its real answer — a Google service can never be
  /// authorized directly from this client, so the honest response is
  /// either "already connected" or an explanation of what to do on the
  /// URI server host. Tapping Connect/Reconnect must never look like
  /// it did nothing.
  Future<void> _authorize(AppState state, String connectionId) async {
    final explanation = await state.authorizeConnection(connectionId);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Google sign-in'),
        content: Text(explanation),
        actions: [
          if (connectionId == 'gmail' || connectionId == 'drive')
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
                _configureCredentials(state);
              },
              child: const Text('Configure Credentials'),
            ),
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('OK')),
        ],
      ),
    );
  }

  Future<void> _configureCredentials(AppState state) async {
    final messenger = ScaffoldMessenger.of(context);
    final rawJson = TextEditingController();
    final clientId = TextEditingController();
    final clientSecret = TextEditingController();
    bool saving = false;
    String? error;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Configure Credentials'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Text('To connect Google services (Gmail & Drive), create an OAuth 2.0 Client ID (Desktop App) in Google Cloud Console and paste the credentials JSON below.'),
              const SizedBox(height: UriSpace.md),
              TextField(controller: rawJson, maxLines: 5, decoration: const InputDecoration(labelText: 'Credentials JSON', border: OutlineInputBorder())),
              const SizedBox(height: UriSpace.sm),
              const Text('Or enter the Client ID and Client Secret separately.'),
              const SizedBox(height: UriSpace.sm),
              TextField(controller: clientId, decoration: const InputDecoration(labelText: 'Client ID', border: OutlineInputBorder())),
              const SizedBox(height: UriSpace.sm),
              TextField(controller: clientSecret, obscureText: true, decoration: const InputDecoration(labelText: 'Client Secret', border: OutlineInputBorder())),
              if (error != null) Padding(padding: const EdgeInsets.only(top: UriSpace.sm), child: Text(error!, style: const TextStyle(color: Colors.red))),
            ]),
          ),
          actions: [
            TextButton(onPressed: saving ? null : () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
            FilledButton(
              onPressed: saving ? null : () async {
                setDialogState(() { saving = true; error = null; });
                final saveError = await state.saveGoogleCredentials(rawJson: rawJson.text.trim().isEmpty ? null : rawJson.text.trim(), clientId: clientId.text.trim().isEmpty ? null : clientId.text.trim(), clientSecret: clientSecret.text.trim().isEmpty ? null : clientSecret.text.trim());
                if (!dialogContext.mounted) return;
                if (saveError == null) {
                  // Refresh (which rebuilds this dialog's ancestor via
                  // notifyListeners()) BEFORE popping the dialog, never
                  // after - popping first and rebuilding an ancestor
                  // synchronously afterward is exactly the known
                  // Flutter race that throws
                  // "Failed assertion: '_dependents.isEmpty'" on this
                  // route's own inherited-widget dependents.
                  await state.loadConnections();
                  if (!dialogContext.mounted) return;
                  Navigator.of(dialogContext).pop();
                  if (mounted) messenger.showSnackBar(const SnackBar(content: Text('Google credentials saved.')));
                } else {
                  setDialogState(() { saving = false; error = saveError; });
                }
              },
              child: const Text('Save Credentials'),
            ),
          ],
        ),
      ),
    );
    rawJson.dispose(); clientId.dispose(); clientSecret.dispose();
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
                title: 'Connections',
                subtitle:
                    'Services URI can use on your behalf. Nothing here is used '
                    'without your say — connecting only grants access; it doesn\'t '
                    'authorize any specific action.',
              ),
              if (state.connections.isEmpty)
                const LoadingState(message: 'Checking connection status…')
              else
                LayoutBuilder(
                  builder: (context, constraints) {
                    final columns = constraints.maxWidth >= UriBreakpoints.wide ? 2 : 1;
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: state.connections.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns,
                        mainAxisExtent: 216,
                        crossAxisSpacing: UriSpace.md,
                        mainAxisSpacing: UriSpace.md,
                      ),
                      itemBuilder: (context, index) {
                        final connection = state.connections[index];
                        return _ConnectionCard(
                          connection: connection,
                          onAuthorize: () => _authorize(state, connection.id),
                          onDisconnect: () => state.disconnectConnection(connection.id),
                        );
                      },
                    );
                  },
                ),
            ],
          ),
        );
      },
    );
  }
}

class _ConnectionCard extends StatelessWidget {
  const _ConnectionCard({
    required this.connection,
    required this.onAuthorize,
    required this.onDisconnect,
  });

  final ServiceConnection connection;
  final VoidCallback onAuthorize;
  final VoidCallback onDisconnect;

  IconData get _icon {
    switch (connection.id) {
      case 'gmail':
        return Icons.mail_outline_rounded;
      case 'drive':
        return Icons.folder_outlined;
      case 'calendar':
        return Icons.calendar_today_outlined;
      case 'sheets':
        return Icons.table_chart_outlined;
      default:
        return Icons.extension_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: colors.surfaceSunken,
                    borderRadius: BorderRadius.circular(UriRadius.sm),
                  ),
                  alignment: Alignment.center,
                  child: Icon(_icon, size: 18, color: colors.ink),
                ),
                const SizedBox(width: UriSpace.sm),
                Expanded(child: Text(connection.name, style: theme.textTheme.titleMedium)),
                StatusPill.forConnection(context, connection.status),
              ],
            ),
            const SizedBox(height: UriSpace.sm),
            Expanded(
              child: Text(
                connection.description,
                style: theme.textTheme.bodyMedium,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: 4),
            // Always reserve this line's height (even with no detail
            // text) so the action button sits at the same position on
            // every card, regardless of which connections have a detail
            // string — otherwise a card without one visibly floats its
            // button lower than its neighbours.
            Text(connection.detail ?? '', style: theme.textTheme.labelSmall),
            const SizedBox(height: UriSpace.sm),
            Row(
              children: [
                _actionFor(connection.status),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // TextButton/OutlinedButton/ElevatedButton carry different default
  // padding and minimum tap-target sizes, which otherwise makes the
  // button sit at a different height on the card depending purely on
  // connection state. Forcing identical padding/minimumSize on all
  // three keeps every card's button aligned to the same position.
  static const _actionButtonPadding = EdgeInsets.symmetric(horizontal: 16, vertical: 8);
  static const _actionButtonMinSize = Size(0, 36);

  Widget _actionFor(ConnectionStatus status) {
    return Align(
      alignment: Alignment.centerLeft,
      child: switch (status) {
        ConnectionStatus.connected => TextButton(
          onPressed: onDisconnect,
          style: TextButton.styleFrom(
            padding: _actionButtonPadding,
            minimumSize: _actionButtonMinSize,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          child: const Text('Disconnect'),
        ),
        ConnectionStatus.needsAuthorization => OutlinedButton(
          onPressed: onAuthorize,
          style: OutlinedButton.styleFrom(
            padding: _actionButtonPadding,
            minimumSize: _actionButtonMinSize,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          child: const Text('Reconnect'),
        ),
        ConnectionStatus.notConnected => ElevatedButton(
          onPressed: onAuthorize,
          style: ElevatedButton.styleFrom(
            padding: _actionButtonPadding,
            minimumSize: _actionButtonMinSize,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          child: const Text('Connect'),
        ),
      },
    );
  }
}

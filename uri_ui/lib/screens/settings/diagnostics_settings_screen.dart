import 'package:flutter/material.dart';

import '../../services/app_state.dart' show BackendConnectionStatus;
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/server_address_section.dart' show ConnectionStatusBadge;

/// Real, verifiable connection health plus this device's own
/// identifiers — everything here is either already tracked in
/// [AppState] from a real GET /health call, or read from GET
/// /identity. Nothing invented, nothing simulated.
class DiagnosticsSettingsScreen extends StatefulWidget {
  const DiagnosticsSettingsScreen({super.key});

  @override
  State<DiagnosticsSettingsScreen> createState() => _DiagnosticsSettingsScreenState();
}

class _DiagnosticsSettingsScreenState extends State<DiagnosticsSettingsScreen> {
  bool _isChecking = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedIdentity) state.loadIdentity();
      if (!state.hasLoadedAccountInfo) state.loadAccountInfo();
    });
  }

  Future<void> _runHealthCheck() async {
    setState(() => _isChecking = true);
    await AppStateScope.of(context).checkConnection();
    if (mounted) setState(() => _isChecking = false);
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
            Row(
              children: [
                const Text('Backend reachability'),
                const SizedBox(width: UriSpace.sm),
                ConnectionStatusBadge(status: state.connectionStatus),
                const Spacer(),
                OutlinedButton(
                  onPressed: _isChecking ? null : _runHealthCheck,
                  child: _isChecking
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Run health check'),
                ),
              ],
            ),
            if (state.lastConnectionErrorDetail != null &&
                state.connectionStatus == BackendConnectionStatus.unreachable) ...[
              const SizedBox(height: UriSpace.xs),
              Text(
                state.lastConnectionErrorDetail!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: colors.inkFaint),
              ),
            ],
            const SizedBox(height: UriSpace.lg),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(UriSpace.md),
              decoration: BoxDecoration(
                color: colors.surfaceSunken,
                borderRadius: BorderRadius.circular(UriRadius.sm),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Backend address', style: Theme.of(context).textTheme.labelSmall),
                  Text(state.baseUrl, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: UriSpace.sm),
                  // Two deliberately distinct identifiers (see
                  // AccountInfo's own doc comment): the SERVER's own
                  // runtime install vs THIS client's own login device -
                  // two clients of the same account on the same backend
                  // always share the former but never the latter.
                  Text('Server device ID', style: Theme.of(context).textTheme.labelSmall),
                  Text(
                    state.hasLoadedIdentity
                        ? (state.identity?.deviceId ?? 'Unavailable')
                        : 'Checking…',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: UriSpace.sm),
                  Text('This device\'s ID', style: Theme.of(context).textTheme.labelSmall),
                  Text(
                    state.hasLoadedAccountInfo
                        ? (state.accountInfo?.deviceId ?? 'Not available for this login')
                        : 'Checking…',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

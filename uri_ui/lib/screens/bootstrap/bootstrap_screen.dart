import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/server_address_section.dart';

/// Bootstrap fix (multi-client connectivity): shown before login/signup
/// whenever this device has never had a working backend address
/// configured (see AppState.hasConfiguredServerAddress) - closes the
/// lockout where Settings > "URI server" was the only place to fix a
/// wrong address, but Settings itself was only reachable after logging
/// in, which could never succeed against a wrong address in the first
/// place.
///
/// Deliberately thin: reuses [ServerAddressSection] (the exact same
/// widget Settings uses) and AppState's existing
/// setBaseUrl/checkConnection - no new networking logic, no new
/// backend endpoint, no way to reach anything beyond the already-
/// unauthenticated GET /health this device would otherwise use anyway.
/// The moment a typed address tests successfully, it is applied (via
/// setBaseUrl, exactly as Save already does) and AppState.
/// hasConfiguredServerAddress flips true - main.dart's root
/// ListenableBuilder reacts immediately and swaps this screen for the
/// login screen, with no separate "Continue" step to click through.
class BootstrapScreen extends StatelessWidget {
  const BootstrapScreen({super.key});

  Future<bool> _testAndApplyIfReachable(BuildContext context, String address) async {
    final state = AppStateScope.of(context);
    final reachable = await state.checkConnection(addressOverride: address);
    if (reachable) {
      // A successful test is exactly what Save already means elsewhere
      // in this app - apply and persist it now rather than asking for
      // a second, separate confirmation tap.
      await state.setBaseUrl(address);
    }
    return reachable;
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final theme = Theme.of(context);

        return Scaffold(
          backgroundColor: UriColors.canvas,
          body: SafeArea(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Padding(
                  padding: const EdgeInsets.all(UriSpace.xl),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Connect to your URI server', style: theme.textTheme.headlineMedium),
                      const SizedBox(height: UriSpace.xs),
                      const Text(
                        "Before signing in, tell this device where your URI backend is running. "
                        "On a phone, this is your PC's address on the same network — not "
                        'localhost, which means this phone itself.',
                      ),
                      const SizedBox(height: UriSpace.lg),
                      ServerAddressSection(
                        baseUrl: state.baseUrl,
                        connectionStatus: state.connectionStatus,
                        connectionErrorDetail: state.lastConnectionErrorDetail,
                        onSave: (url) => state.setBaseUrl(url),
                        onTestConnection: (address) => _testAndApplyIfReachable(context, address),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

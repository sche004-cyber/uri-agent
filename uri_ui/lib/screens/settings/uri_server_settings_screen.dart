import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../widgets/server_address_section.dart';

/// Which backend this device talks to. On a phone, point this at your
/// PC's address on the same network — not localhost, which means this
/// phone itself.
class UriServerSettingsScreen extends StatelessWidget {
  const UriServerSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        return ServerAddressSection(
          baseUrl: state.baseUrl,
          connectionStatus: state.connectionStatus,
          connectionErrorDetail: state.lastConnectionErrorDetail,
          onSave: (url) => state.setBaseUrl(url),
          onTestConnection: (address) => state.checkConnection(addressOverride: address),
        );
      },
    );
  }
}

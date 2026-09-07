import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/app_shell.dart';

/// Deliberately NOT a second copy of the Connections screen — that
/// would be exactly the kind of duplicate surface this redesign is
/// meant to remove. This is a short, real summary (real connected/
/// total counts, same as Home's dashboard) plus a single jump to the
/// one Connections screen that actually manages them.
class ConnectionsSettingsScreen extends StatefulWidget {
  const ConnectionsSettingsScreen({super.key});

  @override
  State<ConnectionsSettingsScreen> createState() => _ConnectionsSettingsScreenState();
}

class _ConnectionsSettingsScreenState extends State<ConnectionsSettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AppStateScope.of(context).loadConnections();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);
        final connected = state.connections.where((c) => c.status.name == 'connected').length;
        final total = state.connections.length;

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(UriSpace.lg),
          decoration: BoxDecoration(
            color: colors.surfaceSunken,
            borderRadius: BorderRadius.circular(UriRadius.sm),
          ),
          child: Row(
            children: [
              Icon(Icons.hub_outlined, color: colors.inkFaint),
              const SizedBox(width: UriSpace.md),
              Expanded(
                child: Text(
                  total == 0
                      ? 'Checking connection status…'
                      : '$connected of $total services connected.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
              OutlinedButton(
                onPressed: () => context
                    .findAncestorStateOfType<AppShellState>()
                    ?.goTo(ShellIndex.connections),
                child: const Text('Open Connections'),
              ),
            ],
          ),
        );
      },
    );
  }
}

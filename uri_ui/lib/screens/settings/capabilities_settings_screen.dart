import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show CapabilityInfo;
import '../../theme/uri_theme.dart';

/// M16: renders the backend's real capability catalogue. A capability
/// that cannot run right now is shown as such, with the honest reason -
/// "not implemented" never masquerades as "temporarily unavailable",
/// because only one of those can ever be unblocked by the user.
class CapabilitiesSettingsScreen extends StatefulWidget {
  const CapabilitiesSettingsScreen({super.key});

  @override
  State<CapabilitiesSettingsScreen> createState() => _CapabilitiesSettingsScreenState();
}

class _CapabilitiesSettingsScreenState extends State<CapabilitiesSettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedCapabilities) state.loadCapabilities();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        return _CapabilityList(capabilities: state.capabilities, loaded: state.hasLoadedCapabilities);
      },
    );
  }
}

class _CapabilityList extends StatelessWidget {
  const _CapabilityList({required this.capabilities, required this.loaded});

  final List<CapabilityInfo> capabilities;
  final bool loaded;

  @override
  Widget build(BuildContext context) {
    if (!loaded) {
      return const _PlaceholderRow(label: 'Checking with the server…');
    }

    if (capabilities.isEmpty) {
      // Honest empty state: URI could not verify anything, so it
      // claims nothing.
      return const _PlaceholderRow(label: 'Could not read capabilities from the server');
    }

    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final capability in capabilities)
          Padding(
            padding: const EdgeInsets.only(bottom: UriSpace.sm),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  capability.isUsable ? Icons.check_circle_outline : Icons.remove_circle_outline,
                  size: 16,
                  color: capability.isUsable ? colors.success : colors.inkFaint,
                ),
                const SizedBox(width: UriSpace.xs),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(capability.id, style: theme.textTheme.bodyMedium?.copyWith(color: colors.ink)),
                      if (capability.description.isNotEmpty)
                        Text(capability.description, style: theme.textTheme.bodySmall),
                      if (capability.gapReason != null)
                        Text(
                          _gapLabel(capability),
                          style: theme.textTheme.bodySmall?.copyWith(color: colors.inkFaint),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  static String _gapLabel(CapabilityInfo capability) {
    if (!capability.isImplemented) {
      return 'Not built yet — nothing you do can enable this.';
    }
    final limitations = capability.limitations;
    return limitations == null
        ? 'Exists, but unavailable on this system right now.'
        : 'Unavailable right now: $limitations';
  }
}

class _PlaceholderRow extends StatelessWidget {
  const _PlaceholderRow({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline_rounded, size: 16, color: colors.inkFaint),
          const SizedBox(width: UriSpace.sm),
          Expanded(child: Text(label, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../app_info.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/uri_wordmark.dart';

/// Static, real build information — no invented statistics, no fake
/// version-check UI. The version string is the one canonical
/// [kUriAppVersion] constant (see app_info.dart), matching
/// pubspec.yaml's own `version:` field; there is no separate source of
/// truth for it to drift from short of editing both by hand.
class AboutSettingsScreen extends StatelessWidget {
  const AboutSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    final state = AppStateScope.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.lg),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const UriWordmark(markSize: 34, showWordmark: false),
              const SizedBox(width: UriSpace.sm),
              Text('URI', style: theme.textTheme.titleMedium),
              const SizedBox(width: UriSpace.sm),
              Text('v$kUriAppVersion', style: theme.textTheme.bodyMedium),
            ],
          ),
          const SizedBox(height: UriSpace.md),
          Text(
            'URI never acts without your approval unless you\'ve allowed it. '
            'Runs against a self-hosted backend on your own network — no cloud sync.',
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: UriSpace.md),
          Text('Connected to', style: theme.textTheme.labelSmall),
          Text(state.baseUrl, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}

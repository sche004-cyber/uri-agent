import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';

/// Static, real build information — no invented statistics, no fake
/// version-check UI. The version string matches pubspec.yaml's own
/// `version:` field; there is no separate source of truth for it to
/// drift from short of editing both by hand.
class AboutSettingsScreen extends StatelessWidget {
  const AboutSettingsScreen({super.key});

  static const _version = '1.0.0';

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
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(color: colors.ink, borderRadius: BorderRadius.circular(9)),
                alignment: Alignment.center,
                child: Text('U', style: TextStyle(color: colors.canvas, fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: UriSpace.sm),
              Text('URI', style: theme.textTheme.titleMedium),
              const SizedBox(width: UriSpace.sm),
              Text('v$_version', style: theme.textTheme.bodyMedium),
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

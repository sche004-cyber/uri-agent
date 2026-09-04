import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

/// The title + one-line-purpose pattern repeated at the top of every
/// utility screen (Ask URI, Connections, Activity, Settings). Pulling
/// this into one widget is what keeps that hierarchy — and the spacing
/// around it — visually identical across screens instead of drifting
/// screen by screen.
class ScreenHeader extends StatelessWidget {
  const ScreenHeader({super.key, required this.title, required this.subtitle, this.trailing});

  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.xl),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: theme.textTheme.headlineMedium),
                const SizedBox(height: 6),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 560),
                  child: Text(subtitle, style: theme.textTheme.bodyLarge),
                ),
              ],
            ),
          ),
          if (trailing != null) ...[const SizedBox(width: UriSpace.md), trailing!],
        ],
      ),
    );
  }
}

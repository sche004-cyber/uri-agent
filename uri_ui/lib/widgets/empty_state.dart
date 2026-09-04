import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

/// A deliberately calm, non-decorative empty state: what this space is
/// for, and — where relevant — the one action that fills it.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: UriSpace.xxl, horizontal: UriSpace.lg),
      decoration: BoxDecoration(
        color: UriColors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.lg),
        border: Border.all(color: UriColors.border),
      ),
      child: Column(
        children: [
          Icon(icon, size: 30, color: UriColors.inkFaint),
          const SizedBox(height: UriSpace.md),
          Text(title, style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
          const SizedBox(height: UriSpace.xs),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ),
          if (action != null) ...[
            const SizedBox(height: UriSpace.md),
            action!,
          ],
        ],
      ),
    );
  }
}

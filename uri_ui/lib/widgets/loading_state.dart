import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

/// A consistent, calm loading placeholder — used instead of a bare
/// [CircularProgressIndicator] dropped into whatever layout happens to
/// be nearby, so every screen's "still loading" moment looks the same.
class LoadingState extends StatelessWidget {
  const LoadingState({super.key, this.message});

  final String? message;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: UriSpace.xxl),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.4, color: colors.accent),
            ),
            if (message != null) ...[
              const SizedBox(height: UriSpace.md),
              Text(message!, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }
}

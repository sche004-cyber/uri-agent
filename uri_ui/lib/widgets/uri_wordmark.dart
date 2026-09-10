import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

/// The "U" mark + "URI" wordmark, in one canonical place rather than
/// duplicated (previously: app_shell.dart's private `_Wordmark` and
/// about_settings_screen.dart each defined their own near-identical
/// box). Branding assets/colors themselves are unchanged - this only
/// removes the duplication, it does not redesign the mark (a real
/// logo/asset-based rebrand is out of scope here; see
/// URI_M22_ARCHITECTURE.md section 14, M22.9).
class UriWordmark extends StatelessWidget {
  const UriWordmark({super.key, this.markSize = 30, this.showWordmark = true});

  /// Side length of the square mark. The wordmark text scales with the
  /// current theme's headlineSmall regardless of this.
  final double markSize;

  /// False shows only the square mark, no "URI" text - for a tighter
  /// space than app_shell.dart's sidebar header needs.
  final bool showWordmark;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: markSize,
          height: markSize,
          decoration: BoxDecoration(color: colors.ink, borderRadius: BorderRadius.circular(markSize * 0.3)),
          alignment: Alignment.center,
          child: Text(
            'U',
            style: TextStyle(color: colors.canvas, fontWeight: FontWeight.w700, fontSize: markSize * 0.53),
          ),
        ),
        if (showWordmark) ...[
          const SizedBox(width: 10),
          Text('URI', style: Theme.of(context).textTheme.headlineSmall),
        ],
      ],
    );
  }
}

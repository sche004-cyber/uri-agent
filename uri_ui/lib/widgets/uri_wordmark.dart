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
  const UriWordmark({
    super.key,
    this.markSize = 30,
    this.showWordmark = true,
    this.showTagline = false,
  });

  /// Side length of the square mark. The wordmark text scales with the
  /// current theme's headlineSmall regardless of this.
  final double markSize;

  /// False shows only the square mark, no "URI" text - for a tighter
  /// space than app_shell.dart's sidebar header needs.
  final bool showWordmark;

  /// M22.9 (§0.1): also shows the resolved text-only sub-brand,
  /// "— AI COMPANION", beneath "URI" — the full wordmark the User
  /// approved for this milestone. Default false so every pre-existing
  /// call site (the sidebar header, the About screen) keeps its exact
  /// prior look; only the entry points that actually want the full
  /// branded treatment (login, onboarding) opt in.
  final bool showTagline;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final mark = Container(
      width: markSize,
      height: markSize,
      decoration: BoxDecoration(color: colors.ink, borderRadius: BorderRadius.circular(markSize * 0.3)),
      alignment: Alignment.center,
      child: Text(
        'U',
        style: TextStyle(color: colors.canvas, fontWeight: FontWeight.w700, fontSize: markSize * 0.53),
      ),
    );

    if (!showWordmark) {
      return mark;
    }

    final wordmarkText = Text('URI', style: Theme.of(context).textTheme.headlineSmall);

    if (!showTagline) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [mark, const SizedBox(width: 10), wordmarkText],
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        mark,
        const SizedBox(width: 10),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            wordmarkText,
            Text(
              '— AI COMPANION',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                color: colors.inkFaint,
                fontSize: 12,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

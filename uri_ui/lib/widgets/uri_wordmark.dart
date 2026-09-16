import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

/// URI's native vector wordmark. It has no raster field, so the brand mark
/// blends directly into the obsidian shell on every desktop density.
class UriWordmark extends StatelessWidget {
  const UriWordmark({
    super.key,
    this.markSize = 30,
    this.showWordmark = true,
    this.showTagline = false,
    this.showDesktopCompanion = false,
  });

  final double markSize;
  final bool showWordmark;
  final bool showTagline;
  final bool showDesktopCompanion;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final mark = SizedBox(
      width: markSize,
      height: markSize,
      child: CustomPaint(
        painter: _EclipseMarkPainter(colors.accent, colors.canvas),
      ),
    );
    if (!showWordmark) return mark;

    final title = Text(
      'URI',
      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
        color: colors.ink,
        fontSize: markSize >= 40 ? 24 : 20,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.4,
      ),
    );
    if (!showTagline && !showDesktopCompanion) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [mark, const SizedBox(width: 10), title],
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.max,
      children: [
        mark,
        const SizedBox(width: 10),
        Expanded(
          child: FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                title,
                if (showDesktopCompanion)
                  Text(
                    'DESKTOP COMPANION',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: colors.accentInk,
                      fontWeight: FontWeight.w800,
                      fontSize: 9,
                      letterSpacing: 0.5,
                    ),
                  ),
                if (showTagline)
                  Text(
                    'AI COMPANION',
                    style: Theme.of(context).textTheme.labelSmall
                        ?.copyWith(color: colors.inkFaint),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// A single orbital line and occluding disc create one cohesive eclipse, not
/// two overlapping semicircles.
class _EclipseMarkPainter extends CustomPainter {
  const _EclipseMarkPainter(this.accent, this.background);
  final Color accent;
  final Color background;

  @override
  void paint(Canvas canvas, Size size) {
    final orbit = Rect.fromLTWH(
      size.width * .04,
      size.height * .18,
      size.width * .92,
      size.height * .64,
    );
    final glow = Paint()
      ..color = accent.withValues(alpha: .18)
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * .13
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5);
    canvas.drawOval(orbit, glow);
    final line = Paint()
      ..color = accent
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * .052
      ..strokeCap = StrokeCap.round;
    canvas.drawOval(orbit, line);
    canvas.drawCircle(
      Offset(size.width * .53, size.height * .5),
      size.width * .255,
      Paint()..color = background,
    );
    final rim = Paint()
      ..color = accent.withValues(alpha: .72)
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * .035;
    canvas.drawArc(
      Rect.fromCircle(
        center: Offset(size.width * .53, size.height * .5),
        radius: size.width * .255,
      ),
      .95,
      2.1,
      false,
      rim,
    );
  }

  @override
  bool shouldRepaint(covariant _EclipseMarkPainter oldDelegate) =>
      oldDelegate.accent != accent || oldDelegate.background != background;
}

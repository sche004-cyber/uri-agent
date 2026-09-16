/// Frozen visual contract for the approved URI desktop dashboard.
///
/// Generated from `docs/design_references/dashboard_preview.html`'s real
/// CSS at its native 1024x682 board size. `1cqw` in that stylesheet is 1%
/// of the `#board` container's own width (`container-type:inline-size`),
/// so at native size `1cqw == 10.24px` exactly - every value below is
/// that exact conversion, not an estimate.
///
/// This file is the single source of truth every dashboard widget reads
/// geometry/tokens from (`docs/plans/URI_APPROVED_UI_IMPLEMENTATION_
/// PLAN.md` sec3) - never a literal re-typed in `reference_dashboard.dart`
/// or elsewhere. Keep this in sync with
/// `docs/design_references/dashboard_manifest.json` (the canonical,
/// tooling-generated copy); regenerate both together if the reference
/// HTML ever changes - never hand-edit one without the other.
library;

import 'package:flutter/material.dart';

class DashboardManifest {
  const DashboardManifest._();

  static const double nativeWidth = 1024;
  static const double nativeHeight = 682;
  static const double aspectRatio = nativeWidth / nativeHeight;

  // Column fractions of the native board width.
  static const double leftColumnFraction = 0.14;
  static const double centerColumnFraction = 0.66;
  static const double rightColumnFraction = 0.20;

  static const double leftRailWidth = 143.4;
  static const double centerWidth = 675.8;
  static const double rightRailWidth = 204.8;

  // Tokens - copied verbatim from dashboard_preview.html's :root block.
  static const Color tokenBg = Color(0xFF020910);
  static const Color tokenLine = Color(0xFF15334A);
  static const Color tokenText = Color(0xFFEAF6FF);
  static const Color tokenMuted = Color(0xFF9BB2C4);
  static const Color tokenBlue = Color(0xFF27C9FF);
  static const Color tokenGreen = Color(0xFF25E5AA);
  static const Color tokenPink = Color(0xFFE15CF5);
  static const Color tokenGold = Color(0xFFFFC437);

  // Left rail.
  static const double logoSize = 117.8;
  static const double logoScalePercent = 108;
  static const List<String> navItems = [
    'Home', 'Chat', 'Email', 'Drive', 'Files', 'Tasks', 'Calendar',
    'Graph', 'Memory', 'Insights', 'Model', 'Tools & Skills', 'Settings',
  ];
  static const double navButtonPaddingVertical = 5.6;
  static const double navButtonPaddingHorizontal = 8.7;
  static const double navButtonFontSize = 9.5;
  static const double navGap = 1.5;
  static const double footMinHeight = 145.4;

  // Hero.
  static const double heroHeight = 84.0;
  static const double greetingFontSize = 21.5;
  static const double greetingNameFontSize = 27.6;
  static const double subtitleFontSize = 11.1;
  static const double quoteWidth = 97.3;
  static const double quoteFontSize = 8.5;

  // Tabs.
  static const double tabsHeight = 26.6;
  static const double tabButtonHeight = 24.6;
  static const double tabButtonFontSize = 8.6;
  static const double tabButtonPaddingHorizontal = 10.8;

  // Metrics row.
  static const double metricsHeight = 145.4;
  static const int metricsColumns = 5;
  static const double metricsGap = 6.7;
  static const double metricCardPaddingTop = 10.2;
  static const double metricCardPaddingHorizontal = 8.7;
  static const double metricCardPaddingBottom = 7.2;
  static const double metricValueFontSize = 23.6;
  static const double sparklineHeight = 53.2;
  static const List<String> metricCards = ['cpu', 'gpu', 'ram', 'disk', 'health'];
  static const double healthLineFontSize = 6.3;
  static const double healthLineValueFontSize = 7.4;

  // Secondary panels row.
  static const double panelsHeight = 176.1;
  static const List<double> panelColumnFractions = [1.12, 1.3, 1.12, 1.27];
  static const double panelsGap = 6.7;
  static const double panelCardPadding = 8.7;
  static const double activityHeight = 108.5;
  static const double donutRowHeight = 114.7;
  static const double donutSize = 84.0;
  static const List<String> panelCards = ['activity', 'modelUsage', 'storage', 'connections'];

  // Composer + tip.
  static const double composerHeight = 49.2;
  static const double composerBorderRadius = 12.8;
  static const double composerPaddingHorizontal = 11.3;
  static const double composerGap = 12.3;
  static const double sendButtonSize = 35.3;
  static const double composerIconSize = 18.9;
  static const double tipHeight = 21.5;
  static const double tipFontSize = 6.6;

  // Right rail.
  static const double rightRailPaddingTop = 10.2;
  static const double rightRailPaddingHorizontal = 10.2;
  static const double rightRailPaddingBottom = 6.1;
  static const double windowsRowHeight = 15.4;
  static const double profileMarginTop = 7.2;
  static const double profileMarginBottom = 10.2;
  static const double avatarSize = 28.7;
  static const double dateMarginBottom = 8.2;
  static const double sidecardMarginBottom = 5.6;
  static const double sidecardPadding = 7.7;
  static const List<String> rightRailCards = ['glance', 'currentModel', 'sandbox', 'toolsSkills'];
}

/// The single shared authority for how much the approved 1024x682
/// board is scaled up/down to fit the current window - [AppShell]
/// computes this ONCE (it is the only widget that ever sees the true,
/// full board area) and provides it down via [DashboardScale.of], so
/// the left rail ([AppShell]'s own `_Sidebar`) and the center/right
/// board (`HomeScreen`'s `_FixedDashboardBoard`) always agree on
/// exactly the same scale factor instead of each computing its own
/// independently. Two independent scaling computations is exactly what
/// let the rail and board drift apart at any window aspect ratio other
/// than the board's own native one (User-reported: "left rail and main
/// board must remain aligned" / "prefer one shared responsive
/// shell/layout authority instead of independent scaling tricks").
class DashboardScale extends InheritedWidget {
  const DashboardScale({super.key, required this.scale, required super.child});

  final double scale;

  /// Classic BoxFit.contain math against the manifest's own native
  /// board size - the one place this computation happens.
  static double scaleFor(Size available) {
    final byWidth = available.width / DashboardManifest.nativeWidth;
    final byHeight = available.height / DashboardManifest.nativeHeight;
    return byWidth < byHeight ? byWidth : byHeight;
  }

  /// Falls back to 1.0 (no scaling) outside of [AppShell]'s wide desktop
  /// layout - e.g. a widget test that renders a screen standalone, or
  /// the narrow/mobile layout, which never installs this ancestor.
  static double of(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<DashboardScale>()?.scale ?? 1.0;
  }

  @override
  bool updateShouldNotify(DashboardScale oldWidget) => scale != oldWidget.scale;
}

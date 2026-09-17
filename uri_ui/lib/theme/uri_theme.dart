import 'package:flutter/material.dart';

/// URI's own visual identity: a warm-neutral, spacious SaaS surface
/// with a single confident accent (a deep violet-blue) rather than the
/// brighter indigo/purple gradients common to template SaaS sites.
/// Inspired, by direction only, by premium SaaS product marketing —
/// no colors, assets, copy, or layout are copied from any reference.
///
/// A [ThemeExtension] rather than static constants: every value here
/// legitimately differs between light and dark, so nothing in this
/// class can be a compile-time constant looked up by name alone —
/// call sites read the active palette via [UriColors.of], which
/// resolves through [Theme.of] the same way `Theme.of(context).textTheme`
/// already does. This is what makes "respects the selected theme"
/// actually true instead of aspirational: there is no code path left
/// that can reference a hardcoded light-only color.
@immutable
class UriColors extends ThemeExtension<UriColors> {
  const UriColors({
    required this.ink,
    required this.inkSoft,
    required this.inkFaint,
    required this.canvas,
    required this.surface,
    required this.surfaceSunken,
    required this.border,
    required this.accent,
    required this.accentSoft,
    required this.accentInk,
    required this.success,
    required this.successSoft,
    required this.warning,
    required this.warningSoft,
    required this.danger,
    required this.dangerSoft,
  });

  final Color ink;
  final Color inkSoft;
  final Color inkFaint;

  final Color canvas;
  final Color surface;
  final Color surfaceSunken;
  final Color border;

  final Color accent;
  final Color accentSoft;
  final Color accentInk;

  final Color success;
  final Color successSoft;
  final Color warning;
  final Color warningSoft;
  final Color danger;
  final Color dangerSoft;

  /// Hybrid UI Frozen Blueprint §4.1/§5 — one of the 4 real themes,
  /// values transcribed from `Palettes.dc.html` (canvas/surface/elevated
  /// swatches + accent, per-theme success/warning pill tones and border).
  /// `inkSoft`/`inkFaint`/`accentSoft`/`accentInk`/`danger`/`dangerSoft`
  /// are not given by that reference (a 4-swatch demo, not a full
  /// per-theme token sheet) — these are derived here (ink/canvas blends
  /// for the ink tiers, surface/accent blends for accentSoft, an
  /// accent-lightened/darkened blend for accentInk) or reused from this
  /// app's previously-accepted dark/light danger colors, since no
  /// per-theme error tone exists in the reference either. Disclosed as a
  /// judgment call, not literal artifact data, in the Batch 3 report.
  static const graphite = UriColors(
    ink: Color(0xFFEEF0F1),
    inkSoft: Color(0xFFAAACAD),
    inkFaint: Color(0xFF727375),
    canvas: Color(0xFF0C0D0F),
    surface: Color(0xFF17181B),
    surfaceSunken: Color(0xFF1F2124),
    border: Color(0xFF2A2C30),
    accent: Color(0xFFC8A25A),
    accentSoft: Color(0xFF373126),
    accentInk: Color(0xFFDBC394),
    success: Color(0xFF5FD6A0),
    successSoft: Color(0xFF123524),
    warning: Color(0xFFE3AB4F),
    warningSoft: Color(0xFF3A2C12),
    danger: Color(0xFFFF8080),
    dangerSoft: Color(0xFF3B1E1E),
  );

  static const deepNavy = UriColors(
    ink: Color(0xFFE8EDF5),
    inkSoft: Color(0xFFA5AAB3),
    inkFaint: Color(0xFF6E737D),
    canvas: Color(0xFF0A0F1A),
    surface: Color(0xFF101828),
    surfaceSunken: Color(0xFF182234),
    border: Color(0xFF243349),
    accent: Color(0xFF5B8FC7),
    accentSoft: Color(0xFF1E2D45),
    accentInk: Color(0xFF94B6DB),
    success: Color(0xFF5CC7AB),
    successSoft: Color(0xFF0F2E28),
    warning: Color(0xFFDBA24D),
    warningSoft: Color(0xFF332711),
    danger: Color(0xFFFF8080),
    dangerSoft: Color(0xFF3B1E1E),
  );

  static const slateTeal = UriColors(
    ink: Color(0xFFE8EBED),
    inkSoft: Color(0xFFA8ABAD),
    inkFaint: Color(0xFF737678),
    canvas: Color(0xFF131619),
    surface: Color(0xFF1A1E22),
    surfaceSunken: Color(0xFF20252A),
    border: Color(0xFF2C3238),
    accent: Color(0xFF4A9C92),
    accentSoft: Color(0xFF233536),
    accentInk: Color(0xFF89BFB8),
    success: Color(0xFF5ECDB2),
    successSoft: Color(0xFF123A30),
    warning: Color(0xFFD9A552),
    warningSoft: Color(0xFF332A13),
    danger: Color(0xFFFF8080),
    dangerSoft: Color(0xFF3B1E1E),
  );

  static const lightProfessional = UriColors(
    ink: Color(0xFF1C2024),
    inkSoft: Color(0xFF5D6064),
    inkFaint: Color(0xFF949699),
    canvas: Color(0xFFF6F7F8),
    surface: Color(0xFFFFFFFF),
    surfaceSunken: Color(0xFFEEF0F2),
    border: Color(0xFFDDE1E5),
    accent: Color(0xFF3B5A78),
    accentSoft: Color(0xFFE7EBEF),
    accentInk: Color(0xFF324C66),
    success: Color(0xFF1C7A4C),
    successSoft: Color(0xFFE2F3EA),
    warning: Color(0xFF93650F),
    warningSoft: Color(0xFFFBF0DC),
    danger: Color(0xFFC23B3B),
    dangerSoft: Color(0xFFFBE9E9),
  );

  /// The active palette for [context], resolved through the current
  /// theme exactly like `Theme.of(context).textTheme` — never a bare
  /// static field, so it always tracks the selected theme correctly.
  /// Falls back to [lightProfessional] only when no [MaterialApp] has
  /// installed the extension yet (e.g. a widget test that builds a bare
  /// widget outside a themed app), never as a "usual" path.
  static UriColors of(BuildContext context) {
    return Theme.of(context).extension<UriColors>() ?? lightProfessional;
  }

  @override
  UriColors copyWith({
    Color? ink,
    Color? inkSoft,
    Color? inkFaint,
    Color? canvas,
    Color? surface,
    Color? surfaceSunken,
    Color? border,
    Color? accent,
    Color? accentSoft,
    Color? accentInk,
    Color? success,
    Color? successSoft,
    Color? warning,
    Color? warningSoft,
    Color? danger,
    Color? dangerSoft,
  }) {
    return UriColors(
      ink: ink ?? this.ink,
      inkSoft: inkSoft ?? this.inkSoft,
      inkFaint: inkFaint ?? this.inkFaint,
      canvas: canvas ?? this.canvas,
      surface: surface ?? this.surface,
      surfaceSunken: surfaceSunken ?? this.surfaceSunken,
      border: border ?? this.border,
      accent: accent ?? this.accent,
      accentSoft: accentSoft ?? this.accentSoft,
      accentInk: accentInk ?? this.accentInk,
      success: success ?? this.success,
      successSoft: successSoft ?? this.successSoft,
      warning: warning ?? this.warning,
      warningSoft: warningSoft ?? this.warningSoft,
      danger: danger ?? this.danger,
      dangerSoft: dangerSoft ?? this.dangerSoft,
    );
  }

  @override
  UriColors lerp(ThemeExtension<UriColors>? other, double t) {
    if (other is! UriColors) return this;
    return UriColors(
      ink: Color.lerp(ink, other.ink, t)!,
      inkSoft: Color.lerp(inkSoft, other.inkSoft, t)!,
      inkFaint: Color.lerp(inkFaint, other.inkFaint, t)!,
      canvas: Color.lerp(canvas, other.canvas, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceSunken: Color.lerp(surfaceSunken, other.surfaceSunken, t)!,
      border: Color.lerp(border, other.border, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      accentInk: Color.lerp(accentInk, other.accentInk, t)!,
      success: Color.lerp(success, other.success, t)!,
      successSoft: Color.lerp(successSoft, other.successSoft, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningSoft: Color.lerp(warningSoft, other.warningSoft, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      dangerSoft: Color.lerp(dangerSoft, other.dangerSoft, t)!,
    );
  }
}

/// Consistent spacing scale so cards, sections, and gaps stay visually
/// disciplined instead of ad hoc. Pure numeric design tokens — nothing
/// here varies with brightness, so (unlike [UriColors]) these stay
/// plain compile-time constants.
class UriSpace {
  UriSpace._();
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}

class UriRadius {
  UriRadius._();
  static const double sm = 10;
  static const double md = 16;
  static const double lg = 22;
}

/// Semantic typography roles for the compact dashboard.  These derive from
/// the active [TextTheme] so every surface shares the application font,
/// weight, spacing, and brightness-aware colours rather than introducing
/// local font families.
extension UriDashboardTextTheme on TextTheme {
  TextStyle get metricValue => headlineSmall!.copyWith(
    fontWeight: FontWeight.w700,
    letterSpacing: -0.2,
    height: 1.1,
  );

  TextStyle get cardHeader => titleMedium!.copyWith(
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    height: 1.25,
  );

  TextStyle get metricCaption => labelSmall!.copyWith(
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    height: 1.35,
  );

  TextStyle get keyValue => bodyMedium!.copyWith(fontSize: 11, height: 1.35);

  TextStyle get footerCaption => labelSmall!.copyWith(
    fontSize: 9,
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    height: 1.3,
  );
}

/// Layout breakpoints shared by every screen that adapts between a
/// compact phone layout and a wider tablet/desktop one (Settings'
/// master-detail, Home's dashboard grid, the app shell's sidebar vs.
/// bottom nav) — one definition so "wide" means the same width
/// everywhere rather than each screen picking its own threshold.
class UriBreakpoints {
  UriBreakpoints._();

  /// Sidebar navigation, dashboard grid, Settings master-detail all
  /// switch on here — matches [AppShell]'s pre-existing threshold.
  static const double wide = 900;

  static bool isWide(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= wide;
}

/// Hybrid UI Frozen Blueprint §4.1/§4.7 — the 4 real Appearance choices,
/// plus `system` (follows the OS light/dark signal by resolving to
/// [UriColors.graphite] or [UriColors.lightProfessional] — the same pair
/// this app's old binary dark/light default mapped to — until the user
/// makes an explicit 4-theme choice; see [ThemeStore]).
enum UriThemeChoice { system, graphite, deepNavy, slateTeal, lightProfessional }

extension UriThemeChoiceLabel on UriThemeChoice {
  String get label => switch (this) {
    UriThemeChoice.system => 'System',
    UriThemeChoice.graphite => 'Graphite',
    UriThemeChoice.deepNavy => 'Deep Navy',
    UriThemeChoice.slateTeal => 'Slate + Teal',
    UriThemeChoice.lightProfessional => 'Light Professional',
  };

  /// The circular swatch color shown for this choice in the topbar and
  /// the Appearance picker — the same accent hex named in Blueprint
  /// §4.1 for the 4 real themes; `system` has no swatch of its own.
  Color? get swatch => switch (this) {
    UriThemeChoice.system => null,
    UriThemeChoice.graphite => UriColors.graphite.accent,
    UriThemeChoice.deepNavy => UriColors.deepNavy.accent,
    UriThemeChoice.slateTeal => UriColors.slateTeal.accent,
    UriThemeChoice.lightProfessional => UriColors.lightProfessional.accent,
  };
}

/// Resolves a [UriThemeChoice] to the actual palette to render.
/// [platformBrightness] only matters for [UriThemeChoice.system].
UriColors resolveUriColors(UriThemeChoice choice, Brightness platformBrightness) {
  switch (choice) {
    case UriThemeChoice.system:
      return platformBrightness == Brightness.dark
          ? UriColors.graphite
          : UriColors.lightProfessional;
    case UriThemeChoice.graphite:
      return UriColors.graphite;
    case UriThemeChoice.deepNavy:
      return UriColors.deepNavy;
    case UriThemeChoice.slateTeal:
      return UriColors.slateTeal;
    case UriThemeChoice.lightProfessional:
      return UriColors.lightProfessional;
  }
}

ThemeData buildUriTheme(UriColors palette) {
  final brightness = ThemeData.estimateBrightnessForColor(palette.canvas);

  final base = ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: palette.accent,
      brightness: brightness,
      surface: palette.surface,
    ),
    scaffoldBackgroundColor: palette.canvas,
    fontFamily: 'Segoe UI',
  );

  final textTheme = base.textTheme.copyWith(
    displaySmall: TextStyle(
      fontSize: 34,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.8,
      color: palette.ink,
      height: 1.15,
    ),
    headlineMedium: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.4,
      color: palette.ink,
      height: 1.2,
    ),
    headlineSmall: TextStyle(
      fontSize: 19,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.2,
      color: palette.ink,
      height: 1.25,
    ),
    titleMedium: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      color: palette.ink,
      height: 1.3,
    ),
    bodyLarge: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w400,
      color: palette.inkSoft,
      height: 1.5,
    ),
    bodyMedium: TextStyle(
      fontSize: 13.5,
      fontWeight: FontWeight.w400,
      color: palette.inkSoft,
      height: 1.5,
    ),
    labelLarge: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: palette.ink,
      letterSpacing: 0.1,
    ),
    labelSmall: TextStyle(
      fontSize: 11.5,
      fontWeight: FontWeight.w600,
      color: palette.inkFaint,
      letterSpacing: 0.4,
    ),
  );

  return base.copyWith(
    extensions: [palette],
    textTheme: textTheme,
    dividerColor: palette.border,
    cardTheme: CardThemeData(
      color: palette.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(UriRadius.md),
        side: BorderSide(color: palette.border),
      ),
      margin: EdgeInsets.zero,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: palette.accent,
        foregroundColor: brightness == Brightness.dark
            ? palette.canvas
            : Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(UriRadius.sm),
        ),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: palette.ink,
        side: BorderSide(color: palette.border),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(UriRadius.sm),
        ),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: palette.inkSoft,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: palette.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: BorderSide(color: palette.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: BorderSide(color: palette.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: BorderSide(color: palette.accent, width: 1.4),
      ),
      hintStyle: TextStyle(color: palette.inkFaint),
    ),
  );
}

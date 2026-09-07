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

  static const light = UriColors(
    ink: Color(0xFF15151B),
    inkSoft: Color(0xFF52525E),
    inkFaint: Color(0xFF8C8C99),
    canvas: Color(0xFFFAF9F6),
    surface: Color(0xFFFFFFFF),
    surfaceSunken: Color(0xFFF1F0EC),
    border: Color(0xFFE7E5DF),
    accent: Color(0xFF4A3AFF),
    accentSoft: Color(0xFFEDEBFF),
    accentInk: Color(0xFF2A1FB8),
    success: Color(0xFF1C8A5A),
    successSoft: Color(0xFFE3F5EC),
    warning: Color(0xFFB6740A),
    warningSoft: Color(0xFFFBF0DD),
    danger: Color(0xFFC23B3B),
    dangerSoft: Color(0xFFFBE9E9),
  );

  static const dark = UriColors(
    ink: Color(0xFFF2F1F5),
    inkSoft: Color(0xFFB8B6C4),
    inkFaint: Color(0xFF87859A),
    canvas: Color(0xFF121116),
    surface: Color(0xFF1C1B22),
    surfaceSunken: Color(0xFF26242D),
    border: Color(0xFF34323C),
    accent: Color(0xFF8A7CFF),
    accentSoft: Color(0xFF2A2450),
    accentInk: Color(0xFFC5BCFF),
    success: Color(0xFF4FD695),
    successSoft: Color(0xFF163829),
    warning: Color(0xFFE3A93F),
    warningSoft: Color(0xFF3A2E12),
    danger: Color(0xFFFF8080),
    dangerSoft: Color(0xFF3B1E1E),
  );

  /// The active palette for [context], resolved through the current
  /// theme exactly like `Theme.of(context).textTheme` — never a bare
  /// static field, so it always tracks light/dark/system correctly.
  /// Falls back to [light] only when no [MaterialApp] has installed
  /// the extension yet (e.g. a widget test that builds a bare widget
  /// outside a themed app), never as a "usual" path.
  static UriColors of(BuildContext context) {
    return Theme.of(context).extension<UriColors>() ?? light;
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

ThemeData buildUriTheme(Brightness brightness) {
  final palette = brightness == Brightness.dark ? UriColors.dark : UriColors.light;

  final base = ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: UriColors.light.accent,
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
        foregroundColor: brightness == Brightness.dark ? palette.canvas : Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UriRadius.sm)),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: palette.ink,
        side: BorderSide(color: palette.border),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UriRadius.sm)),
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

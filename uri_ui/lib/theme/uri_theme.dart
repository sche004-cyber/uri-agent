import 'package:flutter/material.dart';

/// URI's own visual identity: a warm-neutral, spacious SaaS surface
/// with a single confident accent (a deep violet-blue) rather than the
/// brighter indigo/purple gradients common to template SaaS sites.
/// Inspired, by direction only, by premium SaaS product marketing —
/// no colors, assets, copy, or layout are copied from any reference.
class UriColors {
  UriColors._();

  static const Color ink = Color(0xFF15151B);
  static const Color inkSoft = Color(0xFF52525E);
  static const Color inkFaint = Color(0xFF8C8C99);

  static const Color canvas = Color(0xFFFAF9F6);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceSunken = Color(0xFFF1F0EC);
  static const Color border = Color(0xFFE7E5DF);

  static const Color accent = Color(0xFF4A3AFF);
  static const Color accentSoft = Color(0xFFEDEBFF);
  static const Color accentInk = Color(0xFF2A1FB8);

  static const Color success = Color(0xFF1C8A5A);
  static const Color successSoft = Color(0xFFE3F5EC);
  static const Color warning = Color(0xFFB6740A);
  static const Color warningSoft = Color(0xFFFBF0DD);
  static const Color danger = Color(0xFFC23B3B);
  static const Color dangerSoft = Color(0xFFFBE9E9);
}

/// Consistent spacing scale so cards, sections, and gaps stay visually
/// disciplined instead of ad hoc.
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

ThemeData buildUriTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: ColorScheme.fromSeed(
      seedColor: UriColors.accent,
      brightness: Brightness.light,
      surface: UriColors.surface,
    ),
    scaffoldBackgroundColor: UriColors.canvas,
    fontFamily: 'Segoe UI',
  );

  final textTheme = base.textTheme.copyWith(
    displaySmall: const TextStyle(
      fontSize: 34,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.8,
      color: UriColors.ink,
      height: 1.15,
    ),
    headlineMedium: const TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.4,
      color: UriColors.ink,
      height: 1.2,
    ),
    headlineSmall: const TextStyle(
      fontSize: 19,
      fontWeight: FontWeight.w700,
      letterSpacing: -0.2,
      color: UriColors.ink,
      height: 1.25,
    ),
    titleMedium: const TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      color: UriColors.ink,
      height: 1.3,
    ),
    bodyLarge: const TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w400,
      color: UriColors.inkSoft,
      height: 1.5,
    ),
    bodyMedium: const TextStyle(
      fontSize: 13.5,
      fontWeight: FontWeight.w400,
      color: UriColors.inkSoft,
      height: 1.5,
    ),
    labelLarge: const TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: UriColors.ink,
      letterSpacing: 0.1,
    ),
    labelSmall: const TextStyle(
      fontSize: 11.5,
      fontWeight: FontWeight.w600,
      color: UriColors.inkFaint,
      letterSpacing: 0.4,
    ),
  );

  return base.copyWith(
    textTheme: textTheme,
    dividerColor: UriColors.border,
    cardTheme: CardThemeData(
      color: UriColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(UriRadius.md),
        side: const BorderSide(color: UriColors.border),
      ),
      margin: EdgeInsets.zero,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: UriColors.accent,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UriRadius.sm)),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: UriColors.ink,
        side: const BorderSide(color: UriColors.border),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(UriRadius.sm)),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: UriColors.inkSoft,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: UriColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: const BorderSide(color: UriColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: const BorderSide(color: UriColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        borderSide: const BorderSide(color: UriColors.accent, width: 1.4),
      ),
      hintStyle: const TextStyle(color: UriColors.inkFaint),
    ),
  );
}

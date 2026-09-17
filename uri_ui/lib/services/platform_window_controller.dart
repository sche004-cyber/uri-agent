/// Compact mode's real native-window resize.
///
/// Kept isolated in this one file the same way `file_picker`/
/// `attachment_opener` are (see main.dart's own doc comment): AppState
/// and the widget tree in app.dart must stay free of any platform
/// plugin, since importing one there hangs plugin-less widget tests.
/// main.dart injects [setCompactWindowMode] down to [UriHome]; tests
/// never see it, so Compact still works there as a pure state/UI
/// switch, just without the real window actually resizing.
///
/// `window_manager` only ships a native implementation for Windows/
/// macOS/Linux (never Android/web - see its pubspec `platforms:`), and
/// the Compact toggle itself only renders in the wide desktop topbar
/// (see app_shell.dart), so [_supportsWindowControl] gates every call
/// to a no-op off Windows desktop.
library;

import 'dart:io' show Platform;
import 'dart:ui' show Rect, Size;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:window_manager/window_manager.dart';

bool get _supportsWindowControl => !kIsWeb && Platform.isWindows;

/// Companion Compact window: 440x480-720 range, midpoint of the required
/// 420-480 wide x 600-720 tall companion-window target. Logical pixels -
/// window_manager converts using the window's real DPI scale, so this
/// stays the same physical size regardless of Windows display scaling.
const Size compactWindowSize = Size(440, 680);

/// A size effectively unconstrained for `setMaximumSize`: window_manager
/// has no "unset" call (0/negative values are silently ignored by its
/// native side), so this sentinel - far larger than any real display -
/// is the only way to remove the Compact-locked maximum on Expand.
const Size _unconstrainedMax = Size(100000, 100000);

Future<void> ensurePlatformWindowManagerInitialized() async {
  if (!_supportsWindowControl) return;
  await windowManager.ensureInitialized();
}

Rect? _preCompactBounds;

/// Shrinks the real OS window to a fixed, non-resizable Compact size,
/// remembering the Workspace window's current bounds (size AND position)
/// so [exitCompactWindow] can restore them. Keeps the window's current
/// top-left corner rather than moving it, so Compact opens as a small
/// companion window right where the Workspace window already was.
Future<void> enterCompactWindow() async {
  if (!_supportsWindowControl) return;
  _preCompactBounds = await windowManager.getBounds();
  await windowManager.setMinimumSize(compactWindowSize);
  await windowManager.setMaximumSize(compactWindowSize);
  await windowManager.setSize(compactWindowSize);
  await windowManager.setResizable(false);
}

/// Restores the Workspace window's previous size/position where known;
/// falls back to simply lifting the Compact-locked size constraints
/// (leaving the window at its current, already-Compact size) if Compact
/// was somehow entered without ever capturing bounds first.
Future<void> exitCompactWindow() async {
  if (!_supportsWindowControl) return;
  await windowManager.setResizable(true);
  await windowManager.setMinimumSize(Size.zero);
  await windowManager.setMaximumSize(_unconstrainedMax);
  final bounds = _preCompactBounds;
  if (bounds != null) {
    await windowManager.setBounds(bounds);
  }
  _preCompactBounds = null;
}

/// The single hook app.dart's [UriHome] calls on every Compact/Workspace
/// transition it observes on [AppState].
Future<void> setCompactWindowMode(bool isCompact) {
  return isCompact ? enterCompactWindow() : exitCompactWindow();
}

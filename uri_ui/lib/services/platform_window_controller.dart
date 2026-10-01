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
import 'dart:ui' show Offset, Rect, Size;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/widgets.dart' show Alignment;
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

bool _wasMaximized = false;
Rect? _preCompactBounds;

/// Shrinks the real OS window to a fixed, non-resizable Compact size,
/// remembering the Workspace window's current bounds (size AND position)
/// so [exitCompactWindow] can restore them.
///
/// Handles maximized windows by unmaximizing first so Windows doesn't push the
/// window off-screen. Positions the compact window strictly within the active
/// monitor's visible work area (clamped against taskbar and display edges).
Future<void> enterCompactWindow() async {
  if (!_supportsWindowControl) return;

  _wasMaximized = await windowManager.isMaximized();
  _preCompactBounds = await windowManager.getBounds();

  // If the window is maximized, unmaximize first so Win32 WS_MAXIMIZE styles
  // do not force the window to off-screen or negative coordinates.
  if (_wasMaximized) {
    await windowManager.unmaximize();
    await Future.delayed(const Duration(milliseconds: 50));
  }

  // Calculate target position within the active monitor's visible work area.
  Offset targetPos;
  try {
    // calcWindowPosition computes coordinates using the active display's visibleSize and visiblePosition.
    final calculated = await calcWindowPosition(
      compactWindowSize,
      Alignment.topRight,
    );
    targetPos = Offset(
      (calculated.dx - 24).clamp(20.0, double.infinity),
      (calculated.dy + 24).clamp(20.0, double.infinity),
    );
  } catch (_) {
    // Fallback if display calculation fails: clamp existing bounds
    final currentLeft = _preCompactBounds?.left ?? 100.0;
    final currentTop = _preCompactBounds?.top ?? 100.0;
    targetPos = Offset(
      currentLeft < 0 ? 50.0 : currentLeft,
      currentTop < 0 ? 50.0 : currentTop,
    );
  }

  await windowManager.setMinimumSize(compactWindowSize);
  await windowManager.setMaximumSize(compactWindowSize);
  await windowManager.setBounds(
    Rect.fromLTWH(
      targetPos.dx,
      targetPos.dy,
      compactWindowSize.width,
      compactWindowSize.height,
    ),
  );
  await windowManager.setResizable(false);
  await windowManager.show();
  await windowManager.focus();
}

/// Restores the Workspace window's previous size/position where known.
/// If the window was previously maximized, restores the maximized state.
Future<void> exitCompactWindow() async {
  if (!_supportsWindowControl) return;
  await windowManager.setResizable(true);
  await windowManager.setMinimumSize(Size.zero);
  await windowManager.setMaximumSize(_unconstrainedMax);

  if (_wasMaximized) {
    await windowManager.maximize();
  } else if (_preCompactBounds != null) {
    final b = _preCompactBounds!;
    final safeLeft = b.left < 0 ? 50.0 : b.left;
    final safeTop = b.top < 0 ? 50.0 : b.top;
    final safeWidth = b.width < 400 ? 1280.0 : b.width;
    final safeHeight = b.height < 400 ? 900.0 : b.height;
    await windowManager.setBounds(
      Rect.fromLTWH(safeLeft, safeTop, safeWidth, safeHeight),
    );
  } else {
    await windowManager.setSize(const Size(1280, 900));
    await windowManager.setAlignment(Alignment.center);
  }
  _preCompactBounds = null;
  _wasMaximized = false;
  await windowManager.show();
  await windowManager.focus();
}

/// The single hook app.dart's [UriHome] calls on every Compact/Workspace
/// transition it observes on [AppState].
Future<void> setCompactWindowMode(bool isCompact) {
  return isCompact ? enterCompactWindow() : exitCompactWindow();
}

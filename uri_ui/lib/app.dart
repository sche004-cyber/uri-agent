/// The URI application widget tree.
///
/// Deliberately separate from main.dart, and deliberately free of any
/// platform-plugin import: `package:file_picker` (and anything like it)
/// hangs `flutter test` for every widget test that transitively imports
/// it, so the plugin lives only in main.dart — the real entry point —
/// and is injected down as a [FilePickerFn]. Widget tests import THIS
/// file and get the same tree with no plugin attached.
library;

import 'package:flutter/material.dart';

import 'screens/ask/ask_uri_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/bootstrap/bootstrap_screen.dart';
import 'screens/connections/connections_providers_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/onboarding/onboarding_screen.dart';
import 'screens/onboarding/brain_onboarding_screen.dart';
import 'screens/settings/settings_shell.dart';
import 'screens/tasks/tasks_screen.dart';
import 'services/app_state.dart';
import 'services/app_state_scope.dart';
import 'services/attachment_opener_service.dart';
import 'services/file_picker_service.dart';
import 'theme/uri_theme.dart';
import 'widgets/app_shell.dart';
import 'widgets/compact_overlay.dart';

/// Real native-window resize hook for a Compact/Workspace transition.
/// Defined here (not in a plugin file) so this plugin-free file can
/// still declare the parameter type it threads down to [UriHome].
typedef CompactWindowModeFn = Future<void> Function(bool isCompact);

/// Root widget. Decides between the first-run onboarding flow and the
/// main application shell based on [AppState.preferences]. Everything
/// below this point shares one [AppState] via [AppStateScope].
class UriApp extends StatefulWidget {
  const UriApp({
    super.key,
    required this.appState,
    this.filePicker,
    this.attachmentOpener,
    this.onCompactModeChanged,
  });

  final AppState appState;

  /// M16: how the user picks a file to attach. Supplied by main.dart in
  /// the real app; null in tests, where the attach control is simply
  /// not offered rather than shown inert.
  final FilePickerFn? filePicker;

  /// How a tapped attachment gets opened for the user to verify.
  /// Supplied by main.dart in the real app; null in tests, where
  /// tapping one just reports that this build can't open it.
  final AttachmentOpenerFn? attachmentOpener;

  /// Compact mode's real native-window resize hook (see
  /// services/platform_window_controller.dart). Supplied by main.dart
  /// in the real app; null in tests and on platforms without a native
  /// implementation, where Compact still switches correctly as a pure
  /// state/UI change, just without the OS window itself resizing.
  final CompactWindowModeFn? onCompactModeChanged;

  @override
  State<UriApp> createState() => _UriAppState();
}

class _UriAppState extends State<UriApp> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// M22.9 (§0.3): re-checks the current session with the backend the
  /// moment the app comes back to the foreground — a mobile app spends
  /// most of its life backgrounded, so this is the actual moment a
  /// session might have quietly expired since it was last used.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      widget.appState.revalidateSession();
    }
  }

  /// Hybrid UI Frozen Blueprint §4.7 "system" Appearance choice: the OS
  /// brightness signal can change without this app being backgrounded
  /// (e.g. a scheduled OS dark-mode switch) — this is the one place
  /// that needs to notice and re-resolve the active palette.
  @override
  void didChangePlatformBrightness() {
    if (widget.appState.themeChoice == UriThemeChoice.system) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = widget.appState;
    return AppStateScope(
      state: appState,
      child: ListenableBuilder(
        listenable: appState,
        builder: (context, _) {
          final platformBrightness =
              WidgetsBinding.instance.platformDispatcher.platformBrightness;
          final activeColors = resolveUriColors(
            appState.themeChoice,
            platformBrightness,
          );
          return MaterialApp(
            title: 'URI',
            debugShowCheckedModeBanner: false,
            // Appearance → one of the 4 real Hybrid themes, or `system`
            // (Settings → Appearance). Persisted via
            // AppState.setThemeChoice/ThemeStore. The active palette is
            // resolved above (accounting for `system`) and forced via
            // `theme` alone — MaterialApp's own light/dark switching
            // isn't used, since these are 4 distinct named palettes, not
            // a light/dark pair.
            theme: buildUriTheme(activeColors),
            themeMode: ThemeMode.light,
            home: _RootGate(
              appState: appState,
              filePicker: widget.filePicker,
              attachmentOpener: widget.attachmentOpener,
              onCompactModeChanged: widget.onCompactModeChanged,
            ),
          );
        },
      ),
    );
  }
}

class _RootGate extends StatefulWidget {
  const _RootGate({
    required this.appState,
    required this.filePicker,
    required this.attachmentOpener,
    required this.onCompactModeChanged,
  });

  final AppState appState;
  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;
  final CompactWindowModeFn? onCompactModeChanged;

  @override
  State<_RootGate> createState() => _RootGateState();
}

class _RootGateState extends State<_RootGate> {
  @override
  Widget build(BuildContext context) {
    final appState = widget.appState;
    // Bootstrap fix (multi-client connectivity): a device that has
    // never had a working backend address configured can never log in
    // against the compiled-in default (http://localhost:8000,
    // meaningless on a phone) - and Settings > "URI server" (the only
    // place to fix that) was only reachable after logging in. This
    // screen breaks that lockout by coming BEFORE the login gate
    // below, exposing the exact same address/Test Connection controls
    // unauthenticated (GET /health only - no other endpoint is
    // reachable from here). Once a working address is confirmed,
    // AppState.hasConfiguredServerAddress flips true and this screen
    // never shows again this session.
    if (!appState.isAuthenticated && !appState.hasConfiguredServerAddress) {
      return const BootstrapScreen();
    }
    // Prototype 1 (multi-user identity): login is the outermost gate,
    // ahead of onboarding - which user's state onboarding and
    // everything after it operates on is decided here, once, rather
    // than by each screen guessing.
    if (!appState.isAuthenticated) {
      return LoginScreen(onLogin: appState.login, onSignup: appState.signup);
    }
    if (!appState.preferences.completedOnboarding) {
      return OnboardingScreen(
        onComplete: (answers) => appState.updatePreferences(answers),
      );
    }
    if (!appState.brainSetupChecked) {
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => appState.refreshBrainSetupState(),
      );
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    // Optional, not a hard gate: offered once per login while no Brain is
    // configured, but "Skip for now" (brainSetupDismissed) takes the user
    // into URI normally for the rest of this session rather than being
    // re-shown on every subsequent rebuild - see AppState.dismissBrainSetup.
    if (appState.needsBrainSetup && !appState.brainSetupDismissed) {
      return BrainOnboardingScreen(onSkip: appState.dismissBrainSetup);
    }
    return UriHome(
      filePicker: widget.filePicker,
      attachmentOpener: widget.attachmentOpener,
      onCompactModeChanged: widget.onCompactModeChanged,
    );
  }
}

/// The main, post-onboarding application: 5 primary destinations
/// (Home, Chat, Tasks, Connections & Providers, Settings) behind one
/// persistent navigation shell, plus the Compact overlay (§4.4) — a
/// presentation switch over the same shell, never a separate route.
///
/// Compact-window correction (post Live UX Repair): the Live UX Repair
/// above deliberately made Compact fill the entire window rather than
/// float a small fixed-size card, on the User's direct live-testing
/// instruction. A later direct instruction reversed this: Compact must
/// again be a genuinely small, fixed-size companion window - but unlike
/// the original Frozen Blueprint §4.4 text (a floating card *inside* the
/// still full-size window, with a dimming scrim), this now resizes the
/// real OS window itself down to a small fixed size (see
/// services/platform_window_controller.dart), then restores it on
/// Expand. [CompactOverlay] itself is unchanged - it still fills
/// whatever the actual window is, which is now correct precisely
/// because the real window becomes small.
class UriHome extends StatefulWidget {
  const UriHome({
    super.key,
    this.filePicker,
    this.attachmentOpener,
    this.onCompactModeChanged,
  });

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;
  final CompactWindowModeFn? onCompactModeChanged;

  @override
  State<UriHome> createState() => _UriHomeState();
}

class _UriHomeState extends State<UriHome> {
  AppState? _appState;
  bool _lastIsCompact = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final appState = AppStateScope.of(context);
    if (!identical(_appState, appState)) {
      _appState?.removeListener(_handleCompactEdge);
      _appState = appState;
      _lastIsCompact = appState.isCompact;
      appState.addListener(_handleCompactEdge);
    }
  }

  @override
  void dispose() {
    _appState?.removeListener(_handleCompactEdge);
    super.dispose();
  }

  /// AppState.notifyListeners() fires on every state change, not just
  /// Compact toggles (a keystroke in the draft, a loaded task list, ...)
  /// - the real native-window resize must fire exactly once per actual
  /// Compact/Workspace transition, so this only calls out on the edge,
  /// never on every notification.
  void _handleCompactEdge() {
    final isCompact = _appState!.isCompact;
    if (isCompact != _lastIsCompact) {
      _lastIsCompact = isCompact;
      widget.onCompactModeChanged?.call(isCompact);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final isCompact = AppStateScope.of(context).isCompact;
        return Stack(
          children: [
            // The Workspace shell stays mounted via Offstage rather than
            // IgnorePointer, so no state is lost and switching back is
            // instant - it is simply not painted or hit-tested while
            // Compact has the (now genuinely small) window instead.
            Offstage(
              offstage: isCompact,
              child: _buildShell(),
            ),
            if (isCompact)
              CompactOverlay(
                filePicker: widget.filePicker,
                attachmentOpener: widget.attachmentOpener,
              ),
          ],
        );
      },
    );
  }

  Widget _buildShell() {
    return AppShell(
      sections: [
        const UriSection(
          label: 'Home',
          icon: Icons.auto_awesome_outlined,
          builder: _buildHome,
        ),
        UriSection(
          label: 'Chat',
          icon: Icons.chat_bubble_outline,
          builder: (context) => AskUriScreen(
            filePicker: widget.filePicker,
            attachmentOpener: widget.attachmentOpener,
          ),
        ),
        const UriSection(
          label: 'Tasks',
          icon: Icons.check_box_outlined,
          builder: _buildTasks,
        ),
        const UriSection(
          label: 'Connections & Providers',
          mobileLabel: 'Connect',
          icon: Icons.hub_outlined,
          builder: _buildConnections,
        ),
        const UriSection(
          label: 'Settings',
          icon: Icons.settings_outlined,
          builder: _buildSettings,
        ),
      ],
    );
  }

  static Widget _buildHome(BuildContext context) => const HomeScreen();
  static Widget _buildTasks(BuildContext context) => const TasksScreen();
  static Widget _buildConnections(BuildContext context) =>
      const ConnectionsProvidersScreen();
  static Widget _buildSettings(BuildContext context) => const SettingsShell();
}

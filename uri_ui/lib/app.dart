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

import 'screens/activity/activity_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/bootstrap/bootstrap_screen.dart';
import 'screens/connections/connections_screen.dart';
import 'screens/history/history_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/onboarding/onboarding_screen.dart';
import 'screens/settings/settings_shell.dart';
import 'screens/tasks/tasks_screen.dart';
import 'services/app_state.dart';
import 'services/app_state_scope.dart';
import 'services/attachment_opener_service.dart';
import 'services/file_picker_service.dart';
import 'theme/uri_theme.dart';
import 'widgets/app_shell.dart';

/// Root widget. Decides between the first-run onboarding flow and the
/// main application shell based on [AppState.preferences]. Everything
/// below this point shares one [AppState] via [AppStateScope].
class UriApp extends StatelessWidget {
  const UriApp({
    super.key,
    required this.appState,
    this.filePicker,
    this.attachmentOpener,
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

  @override
  Widget build(BuildContext context) {
    return AppStateScope(
      state: appState,
      child: ListenableBuilder(
        listenable: appState,
        builder: (context, _) {
          return MaterialApp(
            title: 'URI',
            debugShowCheckedModeBanner: false,
            theme: buildUriTheme(Brightness.light),
            darkTheme: buildUriTheme(Brightness.dark),
            // Appearance → Light/Dark/System (Settings). Persisted via
            // AppState.setThemeMode/ThemeStore; MaterialApp itself is
            // what actually applies "system" by comparing against the
            // platform brightness, so this is the one place that needs
            // to know the user's choice at all.
            themeMode: appState.themeMode,
            home: _RootGate(
              appState: appState,
              filePicker: filePicker,
              attachmentOpener: attachmentOpener,
            ),
          );
        },
      ),
    );
  }
}

class _RootGate extends StatelessWidget {
  const _RootGate({
    required this.appState,
    required this.filePicker,
    required this.attachmentOpener,
  });

  final AppState appState;
  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  Widget build(BuildContext context) {
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
    return UriHome(filePicker: filePicker, attachmentOpener: attachmentOpener);
  }
}

/// The main, post-onboarding application: Home (dashboard + the one
/// canonical Ask URI conversation), Tasks, Connections, Activity, and
/// Settings behind one persistent navigation shell. There is no
/// separate "Ask URI" destination - Home's own composer and turn
/// history ARE the conversation, so it is never duplicated anywhere
/// else in the shell (see HomeScreen).
class UriHome extends StatelessWidget {
  const UriHome({super.key, this.filePicker, this.attachmentOpener});

  final FilePickerFn? filePicker;
  final AttachmentOpenerFn? attachmentOpener;

  @override
  Widget build(BuildContext context) {
    return AppShell(
      sections: [
        UriSection(
          label: 'Home',
          icon: Icons.auto_awesome_outlined,
          builder: (context) => HomeScreen(
            filePicker: filePicker,
            attachmentOpener: attachmentOpener,
          ),
        ),
        const UriSection(
          label: 'Tasks',
          icon: Icons.task_alt_outlined,
          builder: _buildTasks,
        ),
        const UriSection(
          label: 'Connections',
          icon: Icons.hub_outlined,
          builder: _buildConnections,
        ),
        const UriSection(
          label: 'Activity',
          icon: Icons.receipt_long_outlined,
          builder: _buildActivity,
        ),
        // M19: promoted to a top-level destination (was nested inside
        // Settings) so past conversations are genuinely visible.
        const UriSection(
          label: 'History',
          icon: Icons.history_rounded,
          builder: _buildHistory,
        ),
        const UriSection(
          label: 'Settings',
          icon: Icons.settings_outlined,
          builder: _buildSettings,
        ),
      ],
    );
  }

  static Widget _buildTasks(BuildContext context) => const TasksScreen();
  static Widget _buildConnections(BuildContext context) =>
      const ConnectionsScreen();
  static Widget _buildActivity(BuildContext context) =>
      const ActivityScreen();
  static Widget _buildHistory(BuildContext context) => const HistoryScreen();
  static Widget _buildSettings(BuildContext context) => const SettingsShell();
}

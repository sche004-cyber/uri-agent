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
import 'screens/ask/ask_uri_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/bootstrap/bootstrap_screen.dart';
import 'screens/connections/connections_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/onboarding/onboarding_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/tasks/tasks_screen.dart';
import 'services/app_state.dart';
import 'services/app_state_scope.dart';
import 'services/file_picker_service.dart';
import 'theme/uri_theme.dart';
import 'widgets/app_shell.dart';

/// Root widget. Decides between the first-run onboarding flow and the
/// main application shell based on [AppState.preferences]. Everything
/// below this point shares one [AppState] via [AppStateScope].
class UriApp extends StatelessWidget {
  const UriApp({super.key, required this.appState, this.filePicker});

  final AppState appState;

  /// M16: how the user picks a file to attach. Supplied by main.dart in
  /// the real app; null in tests, where the attach control is simply
  /// not offered rather than shown inert.
  final FilePickerFn? filePicker;

  @override
  Widget build(BuildContext context) {
    return AppStateScope(
      state: appState,
      child: MaterialApp(
        title: 'URI',
        debugShowCheckedModeBanner: false,
        theme: buildUriTheme(),
        home: ListenableBuilder(
          listenable: appState,
          builder: (context, _) {
            // Bootstrap fix (multi-client connectivity): a device that
            // has never had a working backend address configured can
            // never log in against the compiled-in default
            // (http://localhost:8000, meaningless on a phone) - and
            // Settings > "URI server" (the only place to fix that) was
            // only reachable after logging in. This screen breaks that
            // lockout by coming BEFORE the login gate below, exposing
            // the exact same address/Test Connection controls
            // unauthenticated (GET /health only - no other endpoint is
            // reachable from here). Once a working address is
            // confirmed, AppState.hasConfiguredServerAddress flips true
            // and this screen never shows again this session.
            if (!appState.isAuthenticated && !appState.hasConfiguredServerAddress) {
              return const BootstrapScreen();
            }
            // Prototype 1 (multi-user identity): login is the outermost
            // gate, ahead of onboarding - which user's state onboarding
            // and everything after it operates on is decided here,
            // once, rather than by each screen guessing.
            if (!appState.isAuthenticated) {
              return LoginScreen(
                onLogin: appState.login,
                onSignup: appState.signup,
              );
            }
            if (!appState.preferences.completedOnboarding) {
              return OnboardingScreen(
                onComplete: (answers) => appState.updatePreferences(answers),
              );
            }
            return UriHome(filePicker: filePicker);
          },
        ),
      ),
    );
  }
}

/// The main, post-onboarding application: Home, Ask URI, Tasks,
/// Connections, Activity, and Settings behind one persistent
/// navigation shell.
class UriHome extends StatelessWidget {
  const UriHome({super.key, this.filePicker});

  final FilePickerFn? filePicker;

  @override
  Widget build(BuildContext context) {
    return AppShell(
      sections: [
        const UriSection(
          label: 'Home',
          icon: Icons.dashboard_outlined,
          builder: _buildHome,
        ),
        UriSection(
          label: 'Ask URI',
          icon: Icons.auto_awesome_outlined,
          builder: (context) => AskUriScreen(filePicker: filePicker),
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
      const ConnectionsScreen();
  static Widget _buildActivity(BuildContext context) =>
      const ActivityScreen();
  static Widget _buildSettings(BuildContext context) =>
      const SettingsScreen();
}

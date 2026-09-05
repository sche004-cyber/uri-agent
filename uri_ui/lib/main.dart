import 'package:flutter/material.dart';

import 'screens/activity/activity_screen.dart';
import 'screens/ask/ask_uri_screen.dart';
import 'screens/auth/login_screen.dart';
import 'screens/connections/connections_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/onboarding/onboarding_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/tasks/tasks_screen.dart';
import 'services/app_state.dart';
import 'services/app_state_scope.dart';
import 'services/device_identity.dart';
import 'services/http_uri_client.dart';
import 'theme/uri_theme.dart';
import 'widgets/app_shell.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Prototype 2 (multi-client + runtime awareness): this install's own
  // durable device_id (see device_identity.dart), generated once and
  // reused across launches, distinct from whichever user_id ends up
  // logging in on it. Resolved before the client is built so it can be
  // sent at login/signup time.
  final deviceId = await DeviceIdentityStore().loadOrCreate();

  // Talks to the real uri_core backend (uvicorn uri_core.app.server:app)
  // for `ask`; see HttpUriClient's class doc for what still falls back
  // to mock behaviour. Widget/unit tests build their own AppState with
  // MockUriClient directly and are unaffected by this.
  final appState = AppState(client: HttpUriClient(deviceId: deviceId));
  // Resolve any previously persisted onboarding/preferences/server
  // address before the first frame, so a returning user never sees
  // onboarding flash by and a phone already pointed at its PC never
  // silently falls back to localhost.
  await appState.loadPersistedPreferences();
  await appState.loadPersistedServerAddress();

  runApp(UriApp(appState: appState));
}

/// Root widget. Decides between the first-run onboarding flow and the
/// main application shell based on [AppState.preferences]. Everything
/// below this point shares one [AppState] via [AppStateScope].
class UriApp extends StatelessWidget {
  const UriApp({super.key, required this.appState});

  final AppState appState;

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
            return const UriHome();
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
  const UriHome({super.key});

  @override
  Widget build(BuildContext context) {
    return AppShell(
      sections: const [
        UriSection(label: 'Home', icon: Icons.dashboard_outlined, builder: _buildHome),
        UriSection(label: 'Ask URI', icon: Icons.auto_awesome_outlined, builder: _buildAsk),
        UriSection(label: 'Tasks', icon: Icons.task_alt_outlined, builder: _buildTasks),
        UriSection(label: 'Connections', icon: Icons.hub_outlined, builder: _buildConnections),
        UriSection(label: 'Activity', icon: Icons.receipt_long_outlined, builder: _buildActivity),
        UriSection(label: 'Settings', icon: Icons.settings_outlined, builder: _buildSettings),
      ],
    );
  }

  static Widget _buildHome(BuildContext context) => const HomeScreen();
  static Widget _buildAsk(BuildContext context) => const AskUriScreen();
  static Widget _buildTasks(BuildContext context) => const TasksScreen();
  static Widget _buildConnections(BuildContext context) => const ConnectionsScreen();
  static Widget _buildActivity(BuildContext context) => const ActivityScreen();
  static Widget _buildSettings(BuildContext context) => const SettingsScreen();
}

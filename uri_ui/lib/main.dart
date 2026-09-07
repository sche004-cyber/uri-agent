/// Real application entry point.
///
/// This file is deliberately thin, and is the ONLY place that touches a
/// platform plugin (`package:file_picker`, via platform_file_picker.dart).
/// The widget tree itself lives in app.dart so that widget tests can
/// import it without pulling the plugin in — which hangs `flutter test`.
library;

import 'package:flutter/material.dart';

import 'app.dart';
import 'services/app_state.dart';
import 'services/device_identity.dart';
import 'services/http_uri_client.dart';
import 'services/platform_file_picker.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Prototype 2 (multi-client + runtime awareness): this install's own
  // durable device_id (see device_identity.dart), generated once and
  // reused across launches, distinct from whichever user_id ends up
  // logging in on it. Resolved before the client is built so it can be
  // sent at login/signup time.
  final deviceId = await DeviceIdentityStore().loadOrCreate();

  // Talks to the real uri_core backend (uvicorn uri_core.app.server:app).
  // As of M16 nothing in HttpUriClient falls back to mock data. Widget/
  // unit tests build their own AppState with MockUriClient directly and
  // are unaffected by this.
  final appState = AppState(client: HttpUriClient(deviceId: deviceId));
  // Resolve any previously persisted onboarding/preferences/server
  // address before the first frame, so a returning user never sees
  // onboarding flash by and a phone already pointed at its PC never
  // silently falls back to localhost.
  await appState.loadPersistedPreferences();
  await appState.loadPersistedServerAddress();

  // M16: the real platform picker is injected here, at the entry point,
  // and nowhere else.
  runApp(UriApp(appState: appState, filePicker: pickPlatformFile));
}

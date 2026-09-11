import 'package:shared_preferences/shared_preferences.dart';

/// M22.9 (§0.3): persists the current login's bearer token/username
/// on-device, so a still-valid session survives the app being closed
/// and reopened instead of forcing a fresh login every time — the same
/// per-device, on-device-only discipline [ServerAddressStore]/
/// [PreferencesStore] already use. Never itself decides the token is
/// still valid; see [UriClient.validateSession] for that.
class SessionStore {
  static const _tokenKey = 'uri.session.token';
  static const _usernameKey = 'uri.session.username';

  Future<PersistedSession?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    final username = prefs.getString(_usernameKey);
    if (token == null || token.isEmpty || username == null || username.isEmpty) {
      return null;
    }
    return PersistedSession(token: token, username: username);
  }

  Future<void> save({required String token, required String username}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_usernameKey, username);
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_usernameKey);
  }
}

class PersistedSession {
  const PersistedSession({required this.token, required this.username});

  final String token;
  final String username;
}

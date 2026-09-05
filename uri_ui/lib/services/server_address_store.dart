import 'package:shared_preferences/shared_preferences.dart';

/// Prototype 2 (multi-client + runtime awareness): persists the
/// backend address this device should talk to, so a phone can be
/// pointed at its PC's LAN address ("Use a configurable backend
/// address; do not assume localhost on the phone") without retyping it
/// every launch. Same per-device, non-sensitive, on-device-only
/// discipline as PreferencesStore - this is UI-side client
/// configuration, never something the backend is authoritative over.
class ServerAddressStore {
  static const _key = 'uri.serverBaseUrl';

  Future<String?> load() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_key);
  }

  Future<void> save(String baseUrl) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, baseUrl);
  }
}

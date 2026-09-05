import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

/// Prototype 2 (multi-client + runtime awareness): a durable id for
/// THIS Flutter install only - a phone and a PC each generate and
/// keep their own, exactly like uri_core/core/identity.py's
/// DeviceIdentityStore does for the backend's own install, but this
/// one lives entirely client-side and is never derived from (or
/// confused with) the logged-in user's user_id. Sent only at login/
/// signup time (see HttpUriClient), never on every request - the
/// server binds it to that login's token (see auth_session.py) and
/// never treats it as a credential or as user-authoritative data.
///
/// Generated once, cached on-device via shared_preferences (a
/// per-device UI convenience, not a backend - see PreferencesStore's
/// identical discipline) - reinstalling the app or clearing app data
/// always produces a fresh device_id, matching DeviceIdentityStore's
/// own "never portable" contract.
class DeviceIdentityStore {
  static const _key = 'uri.clientDeviceId';

  Future<String> loadOrCreate() async {
    final prefs = await SharedPreferences.getInstance();

    final existing = prefs.getString(_key);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }

    final generated = _generateId();
    await prefs.setString(_key, generated);
    return generated;
  }

  /// A UUIDv4-shaped random id, hand-rolled from dart:math's
  /// cryptographically secure Random rather than pulling in a `uuid`
  /// package dependency for one id generated once per install - this
  /// id is informational metadata (see class doc), never validated
  /// against a strict UUID shape server-side the way user_id is (see
  /// portable_paths.py), so an RFC-perfect implementation isn't
  /// required, only a practically-unique, recognizable one.
  String _generateId() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));

    // Per RFC 4122 §4.4: set version (4) and variant (10) bits.
    bytes[6] = (bytes[6] & 0x0F) | 0x40;
    bytes[8] = (bytes[8] & 0x3F) | 0x80;

    String hex(int start, int end) =>
        bytes.sublist(start, end).map((b) => b.toRadixString(16).padLeft(2, '0')).join();

    return '${hex(0, 4)}-${hex(4, 6)}-${hex(6, 8)}-${hex(8, 10)}-${hex(10, 16)}';
  }
}

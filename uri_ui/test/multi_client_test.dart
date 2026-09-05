// Prototype 2 (multi-client + runtime awareness): unit-tests the
// client-side pieces added on top of HttpUriClient/MockUriClient - a
// configurable, mutable backend address, an explicit connection check,
// device_id being sent at login/signup, and the device_id generator/
// persistence itself. No real network, no real backend.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uri_ui/services/device_identity.dart';
import 'package:uri_ui/services/http_uri_client.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

http.Response _json(Map<String, dynamic> body, {int statusCode = 200}) {
  return http.Response(jsonEncode(body), statusCode);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('DeviceIdentityStore', () {
    test('generates a UUID-shaped id on first use', () async {
      final id = await DeviceIdentityStore().loadOrCreate();

      final uuidPattern = RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
      );
      expect(uuidPattern.hasMatch(id), isTrue, reason: 'got: $id');
    });

    test('returns the same id on a second call (persisted)', () async {
      final store = DeviceIdentityStore();

      final first = await store.loadOrCreate();
      final second = await store.loadOrCreate();

      expect(second, first);
    });

    test('a second, independent store instance sees the same persisted id', () async {
      // Simulates the app relaunching - a fresh DeviceIdentityStore
      // object reading from the same underlying shared_preferences
      // backing store must recover the same device_id, not generate a
      // new one (device_id must be durable across launches).
      final first = await DeviceIdentityStore().loadOrCreate();
      final second = await DeviceIdentityStore().loadOrCreate();

      expect(second, first);
    });
  });

  group('HttpUriClient — configurable backend address', () {
    test('setBaseUrl changes where subsequent requests go', () async {
      final requestedUris = <Uri>[];
      final client = HttpUriClient(
        baseUrl: 'http://localhost:8000',
        httpClient: MockClient((request) async {
          requestedUris.add(request.url);
          return _json({'status': 'ok'});
        }),
      );

      await client.checkConnection();
      expect(requestedUris.single.toString(), 'http://localhost:8000/health');

      client.setBaseUrl('http://192.168.1.23:8000');
      expect(client.baseUrl, 'http://192.168.1.23:8000');

      await client.checkConnection();
      expect(requestedUris.last.toString(), 'http://192.168.1.23:8000/health');
    });

    test('checkConnection returns true for a reachable backend', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async => _json({'status': 'ok'})),
      );

      expect(await client.checkConnection(), isTrue);
    });

    test('checkConnection returns false rather than throwing on a network error', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async => throw Exception('unreachable')),
      );

      expect(await client.checkConnection(), isFalse);
    });

    test('checkConnection returns false for a non-200 response', () async {
      final client = HttpUriClient(
        httpClient: MockClient((request) async => http.Response('error', 500)),
      );

      expect(await client.checkConnection(), isFalse);
    });

    test('a disconnect followed by a reconnect recovers cleanly on the same client', () async {
      var shouldFail = true;
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          if (shouldFail) throw Exception('network down');
          return _json({'status': 'ok'});
        }),
      );

      expect(await client.checkConnection(), isFalse);

      shouldFail = false;
      expect(await client.checkConnection(), isTrue);
    });
  });

  group('HttpUriClient — device_id at login/signup', () {
    test('signup sends the configured device_id in the request body', () async {
      Map<String, dynamic>? sentBody;
      final client = HttpUriClient(
        deviceId: 'phone-device-123',
        httpClient: MockClient((request) async {
          sentBody = jsonDecode(request.body) as Map<String, dynamic>;
          return _json({'user_id': 'u1', 'username': 'alice', 'token': 't1'});
        }),
      );

      await client.signup('alice', 'password123');

      expect(sentBody!['device_id'], 'phone-device-123');
      expect(sentBody!['username'], 'alice');
    });

    test('login omits device_id entirely when none was configured', () async {
      Map<String, dynamic>? sentBody;
      final client = HttpUriClient(
        httpClient: MockClient((request) async {
          sentBody = jsonDecode(request.body) as Map<String, dynamic>;
          return _json({'user_id': 'u1', 'username': 'alice', 'token': 't1'});
        }),
      );

      await client.login('alice', 'password123');

      expect(sentBody!.containsKey('device_id'), isFalse);
    });
  });

  group('MockUriClient — connection config stand-ins', () {
    test('is always reachable and accepts setBaseUrl without error', () async {
      final client = MockUriClient();

      expect(await client.checkConnection(), isTrue);
      client.setBaseUrl('anything');
      expect(client.baseUrl, 'anything');
    });
  });
}

// M22.5: Model provider catalogue and key management UI tests.
// Tests that:
// 1. ProvidersScreen loads and displays the provider catalogue.
// 2. API key input field is masked (obscureText: true).
// 3. Submitting an API key updates configured status to include last-four.
// 4. Raw key is never displayed anywhere in the UI.
// 5. Endpoint overrides dialog functions properly.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/screens/settings/providers_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

class _FailingKeySubmitMockClient extends MockUriClient {
  @override
  Future<ProviderKeyResult?> submitProviderKey(
    String providerId,
    String apiKey,
  ) async {
    return null;
  }
}

Future<AppState> _pumpProvidersScreen(
  WidgetTester tester, {
  UriClient? client,
}) async {
  tester.view.physicalSize = const Size(1280, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final appState = AppState(client ?? MockUriClient());
  await tester.pumpWidget(
    AppStateScope(
      state: appState,
      child: const MaterialApp(
        home: Scaffold(body: SingleChildScrollView(child: ProvidersScreen())),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return appState;
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    300,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('renders catalogue providers with display names and adapters', (
    tester,
  ) async {
    await _pumpProvidersScreen(tester);

    expect(find.text('Connect a provider'), findsOneWidget);
    await _scrollTo(tester, find.text('OpenAI'));
    expect(find.text('OpenAI'), findsOneWidget);
    await _scrollTo(tester, find.text('Groq'));
    expect(find.text('Groq'), findsOneWidget);
    await _scrollTo(tester, find.text('Ollama (Local)'));
    expect(find.text('Ollama (Local)'), findsOneWidget);
    await _scrollTo(tester, find.text('Anthropic'));
    expect(find.text('Anthropic'), findsOneWidget);
  });

  testWidgets(
    'shows the three connection methods and verified-only routing entry point',
    (tester) async {
      await _pumpProvidersScreen(tester);

      expect(find.text('Subscription'), findsOneWidget);
      expect(find.text('API Key'), findsOneWidget);
      expect(find.text('Local Models'), findsOneWidget);
      expect(find.textContaining('Not currently available'), findsOneWidget);
      final fallbackRouting = find.text('Fallback Routing');
      expect(fallbackRouting, findsOneWidget);
      final editRouting = find.text('Edit Routing');
      expect(editRouting, findsOneWidget);

      await tester.tap(editRouting);
      await tester.pumpAndSettle();
      expect(find.text('Edit fallback routing'), findsOneWidget);
      expect(find.text('Primary Brain'), findsOneWidget);
      expect(find.text('Fallback 1'), findsOneWidget);
      expect(find.text('Fallback 2'), findsOneWidget);
    },
  );

  testWidgets('key entry input is masked (obscureText: true)', (tester) async {
    await _pumpProvidersScreen(tester);

    final addKeyBtn = find.text('Add key').first;
    await _scrollTo(tester, addKeyBtn);
    expect(addKeyBtn, findsOneWidget);
    await tester.tap(addKeyBtn);
    await tester.pumpAndSettle();

    // The key input must exist and have obscureText = true
    final textFieldFinder = find.byType(TextField);
    expect(textFieldFinder, findsOneWidget);

    final textField = tester.widget<TextField>(textFieldFinder);
    expect(
      textField.obscureText,
      isTrue,
      reason: 'API key input must always be masked.',
    );
  });

  testWidgets(
    'submitting a key updates configured status with last-4 and never redisplays the raw key',
    (tester) async {
      await _pumpProvidersScreen(tester);

      // Tap "Add Key" for OpenAI
      final addKeyBtn = find.text('Add key').first;
      await _scrollTo(tester, addKeyBtn);
      await tester.tap(addKeyBtn);
      await tester.pumpAndSettle();

      const rawKey = 'sk-test-super-secret-key-9876';
      await tester.enterText(find.byType(TextField), rawKey);
      await tester.pumpAndSettle();

      // Tap "Save Encrypted Key"
      await tester.tap(find.text('Save Encrypted Key'));
      await tester.pumpAndSettle();

      // Dialog should be dismissed
      expect(find.byType(AlertDialog), findsNothing);

      // Configuration is shown in the API-key card after its list refresh.
      expect(find.textContaining('9876'), findsAtLeastNWidgets(1));

      // The raw key must NEVER appear anywhere in the widget tree
      expect(
        find.text(rawKey),
        findsNothing,
        reason: 'Raw API key must never be displayed in the UI.',
      );
    },
  );

  testWidgets('shows explicit error message when key submission fails', (
    tester,
  ) async {
    await _pumpProvidersScreen(tester, client: _FailingKeySubmitMockClient());

    final addKeyBtn = find.text('Add key').first;
    await _scrollTo(tester, addKeyBtn);
    await tester.tap(addKeyBtn);
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'sk-fails');
    await tester.pumpAndSettle();

    await tester.tap(find.text('Save Encrypted Key'));
    await tester.pumpAndSettle();

    // Dialog remains open and displays error
    expect(find.textContaining('Credential storage failed'), findsOneWidget);
  });

  testWidgets('allows saving endpoint config overrides', (tester) async {
    await _pumpProvidersScreen(tester);

    final endpointConfig = find.text('Endpoint').first;
    await _scrollTo(tester, endpointConfig);
    await tester.tap(endpointConfig);
    await tester.pumpAndSettle();

    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text('Save Overrides'), findsOneWidget);

    await tester.tap(find.text('Save Overrides'));
    await tester.pumpAndSettle();

    expect(find.byType(AlertDialog), findsNothing);
  });
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/screens/ask/ask_uri_screen.dart';
import 'package:uri_ui/screens/onboarding/brain_onboarding_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';
import 'package:uri_ui/widgets/app_shell.dart';

class _ProviderSpy extends MockUriClient {
  String? savedProvider;
  String? savedKey;
  String? activeProvider;

  @override
  Future<ProviderKeyResult?> submitProviderKey(
    String providerId,
    String apiKey,
  ) async {
    savedProvider = providerId;
    savedKey = apiKey;
    return super.submitProviderKey(providerId, apiKey);
  }

  @override
  Future<bool> setActiveBrain(String providerId, {String? model}) async {
    activeProvider = providerId;
    return super.setActiveBrain(providerId, model: model);
  }
}

Widget _scoped(AppState state, Widget child) => MaterialApp(
  home: Scaffold(
    body: AppStateScope(state: state, child: child),
  ),
);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('cloud onboarding saves a key and activates that provider', (
    tester,
  ) async {
    final client = _ProviderSpy();
    await tester.pumpWidget(
      _scoped(AppState(client), const BrainOnboardingScreen()),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.text('Cloud Provider (API Key)'));
    await tester.pump(const Duration(seconds: 1));
    await tester.enterText(find.byType(TextField), 'sk-m25-test-key');
    await tester.ensureVisible(find.text('Save Key & Set as Active Brain'));
    await tester.tap(find.text('Save Key & Set as Active Brain'));
    await tester.pump(const Duration(seconds: 1));

    expect(client.savedProvider, 'openai');
    expect(client.savedKey, 'sk-m25-test-key');
    expect(client.activeProvider, 'openai');
  });

  testWidgets('brain status pill shows active reachable brain', (tester) async {
    final state = AppState(MockUriClient());
    state.activeBrain = const ActiveBrainInfo(
      providerId: 'ollama',
      model: 'qwen3:14b',
    );
    state.activeBrainProvider = const ProviderEntry(
      providerId: 'ollama',
      displayName: 'Ollama (Local)',
      adapter: 'ollama',
      baseUrl: 'http://localhost:11434',
      configured: true,
      available: true,
    );
    await tester.pumpWidget(
      _scoped(
        state,
        AppShell(
          sections: [
            UriSection(
              label: 'Home',
              icon: Icons.home,
              builder: (_) => const SizedBox(),
            ),
            UriSection(
              label: 'Settings',
              icon: Icons.settings,
              builder: (_) => const SizedBox(),
            ),
          ],
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('Brain: ollama (qwen3:14b)'), findsOneWidget);
  });

  testWidgets(
    'Enter sends while Shift+Enter leaves a newline in the composer',
    (tester) async {
      final state = AppState(MockUriClient());
      await tester.pumpWidget(_scoped(state, const AskUriScreen()));
      final input = find.byType(TextField);
      await tester.tap(input);
      await tester.enterText(input, 'send this');
      await tester.sendKeyDownEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(state.conversation, hasLength(1));

      await tester.enterText(input, 'keep\nediting');
      await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
      await tester.sendKeyDownEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.enter);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
      await tester.pump();
      expect(state.conversation, hasLength(1));
      expect(tester.widget<TextField>(input).controller!.text, contains('\n'));
    },
  );
}

// Coverage for the Post-Launch Brain Setup & Onboarding Repair:
//   - Brain setup is skippable and never fabricates a provider/model
//   - skipping does not get re-shown on every subsequent app rebuild
//   - the cloud-provider path verifies a real model before activating,
//     instead of calling setActiveBrain with no model at all (the root
//     cause of the reported "cloud-provider path unusable" defect)
//   - the preference-tour onboarding is skippable too

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';
import 'package:uri_ui/screens/onboarding/brain_onboarding_screen.dart';
import 'package:uri_ui/screens/onboarding/onboarding_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';
import 'package:uri_ui/theme/uri_theme.dart';

/// No provider configured and no Active Brain - the state a fresh
/// account is really in before anyone sets one up, unlike the base
/// [MockUriClient] which defaults Ollama to already configured/active.
class _NoBrainClient extends MockUriClient {
  bool keySubmitted = false;
  bool verifyCalled = false;
  String? activatedProvider;
  String? activatedModel;

  @override
  Future<List<ProviderEntry>> listProviders() async {
    final base = await super.listProviders();
    return base
        .map(
          (p) => ProviderEntry(
            providerId: p.providerId,
            displayName: p.displayName,
            adapter: p.adapter,
            baseUrl: p.baseUrl,
            configured: keySubmitted && p.providerId == 'openai',
            available: p.providerId == 'openai',
            models: p.models,
            activeBrain: false,
          ),
        )
        .toList();
  }

  // Matches the real backend exactly (see server.py's
  // GET /providers/active-brain): it never returns null, even for an
  // account that has configured nothing - an unconfigured account still
  // gets the deployment-wide default provider/model back, with
  // isConfigured: false as the only real signal.
  @override
  Future<ActiveBrainInfo?> getActiveBrain() async => const ActiveBrainInfo(
    providerId: 'ollama',
    model: 'qwen3:14b',
    displayName: 'Qwen3 14B',
    isConfigured: false,
  );

  @override
  Future<ProviderKeyResult?> submitProviderKey(
    String providerId,
    String apiKey,
  ) async {
    keySubmitted = true;
    return ProviderKeyResult(
      providerId: providerId,
      configured: true,
      lastFour: apiKey.substring(apiKey.length - 4),
    );
  }

  @override
  Future<ProviderVerificationResult?> verifyProvider(String providerId) async {
    verifyCalled = true;
    return ProviderVerificationResult(
      providerId: providerId,
      verified: true,
      models: const ['gpt-4o'],
    );
  }

  @override
  Future<bool> setActiveBrain(String providerId, {String? model}) async {
    activatedProvider = providerId;
    activatedModel = model;
    return model != null;
  }
}

Widget _scoped(AppState state, Widget child) => MaterialApp(
  home: Scaffold(body: AppStateScope(state: state, child: child)),
);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('BrainOnboardingScreen "Skip for now" invokes onSkip without contacting any provider', (
    tester,
  ) async {
    var skipped = false;
    await tester.pumpWidget(
      _scoped(
        AppState(_NoBrainClient()),
        BrainOnboardingScreen(onSkip: () => skipped = true),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.text('Skip for now'));
    await tester.pump();

    expect(skipped, isTrue);
  });

  testWidgets('cloud onboarding verifies and selects a real model before activating (not null)', (
    tester,
  ) async {
    final client = _NoBrainClient();
    await tester.pumpWidget(
      _scoped(AppState(client), BrainOnboardingScreen(onSkip: () {})),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.text('Cloud Provider (API Key)'));
    await tester.pump(const Duration(seconds: 1));
    await tester.enterText(find.byType(TextField), 'sk-repair-test-key');
    await tester.ensureVisible(find.text('Save Key & Set as Active Brain'));
    await tester.tap(find.text('Save Key & Set as Active Brain'));
    await tester.pump(const Duration(seconds: 1));

    expect(client.verifyCalled, isTrue);
    expect(client.activatedProvider, 'openai');
    // The defect this milestone fixed: the old flow always passed a null
    // model, which the real backend unconditionally rejects.
    expect(client.activatedModel, 'gpt-4o');
    expect(find.textContaining('verified'), findsOneWidget);
  });

  testWidgets('OnboardingScreen "Skip for now" completes onboarding immediately', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    UserPreferences? completed;
    await tester.pumpWidget(
      MaterialApp(
        home: OnboardingScreen(onComplete: (prefs) => completed = prefs),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('Skip for now'));
    await tester.pump();

    expect(completed, isNotNull);
    expect(completed!.completedOnboarding, isTrue);
  });

  testWidgets('skipping Brain setup lands on Home and does not reappear on later rebuilds', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final appState = AppState(_NoBrainClient());
    await appState.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    await tester.pumpWidget(UriApp(appState: appState));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    expect(find.byType(BrainOnboardingScreen), findsOneWidget);

    await tester.tap(find.text('Skip for now'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();

    expect(find.byType(BrainOnboardingScreen), findsNothing);
    expect(appState.brainSetupDismissed, isTrue);

    // Home must show the account's real, unconfigured state - never the
    // deployment-wide default provider/model GET /providers/active-brain
    // returns for every account regardless of configuration (see
    // _NoBrainClient.getActiveBrain and home_screen.dart's isConfigured
    // check, the defect this milestone's live verification found).
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('No Active Brain'), findsOneWidget);
    expect(find.text('Qwen3 14B'), findsNothing);

    // Drive an unrelated notifyListeners() the way live use would (a
    // theme change touches the same top-level ListenableBuilder that
    // rebuilds _RootGate) - the previous behaviour re-evaluated
    // needsBrainSetup on every such rebuild and bounced straight back
    // to BrainOnboardingScreen even after the user had explicitly
    // skipped it, mid-session, with no way out short of configuring a
    // Brain.
    await appState.setThemeChoice(UriThemeChoice.lightProfessional);
    await tester.pumpAndSettle();

    expect(find.byType(BrainOnboardingScreen), findsNothing);
  });

  test(
    'logout clears activeBrain/activeBrainProvider/providerInventory so a '
    'different account signed into next never inherits them (live-verified '
    'cross-account leak, Post-Launch Brain Setup Repair)',
    () async {
      SharedPreferences.setMockInitialValues({});
      final appState = AppState(MockUriClient());

      await appState.loadActiveBrain();
      expect(appState.activeBrain, isNotNull);
      expect(appState.activeBrainProvider, isNotNull);
      await appState.loadProviderInventory();
      expect(appState.providerInventory, isNotEmpty);

      await appState.logout();

      expect(appState.activeBrain, isNull);
      expect(appState.activeBrainProvider, isNull);
      expect(appState.providerInventory, isEmpty);
      expect(appState.brainSetupChecked, isFalse);
      expect(appState.needsBrainSetup, isFalse);
    },
  );
}

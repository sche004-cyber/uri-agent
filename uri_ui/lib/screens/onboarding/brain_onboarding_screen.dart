import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/uri_wordmark.dart';

/// First-run provider setup; separate from the preference-tour onboarding.
class BrainOnboardingScreen extends StatefulWidget {
  const BrainOnboardingScreen({super.key});
  @override
  State<BrainOnboardingScreen> createState() => _BrainOnboardingScreenState();
}

class _BrainOnboardingScreenState extends State<BrainOnboardingScreen> {
  List<ProviderEntry> _providers = const [];
  final _keyController = TextEditingController();
  bool _testing = false;
  bool _savingKey = false;
  _BrainSetupChoice? _choice;
  String? _cloudProviderId;
  String? _message;

  List<ProviderEntry> get _cloudProviders => _providers
      .where((provider) => provider.adapter != 'ollama')
      .toList(growable: false);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _load();
    });
  }

  @override
  void dispose() {
    _keyController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final providers = await AppStateScope.of(context).listProviders();
    if (mounted) setState(() => _providers = providers);
  }

  Future<void> _testLocal() async {
    setState(() {
      _testing = true;
      _message = null;
    });
    await _load();
    if (mounted) {
      setState(() {
        _testing = false;
        _message =
            _providers
                .where((p) => p.adapter == 'ollama')
                .any((p) => p.available)
            ? 'Ollama is reachable. Choose it as your Active Brain.'
            : 'Ollama was not reachable. Start Ollama or connect an API-key provider.';
      });
    }
  }

  Future<void> _chooseLocal() async {
    final local = _providers.where((p) => p.adapter == 'ollama').firstOrNull;
    if (local == null) {
      return;
    }
    final model = local.models.firstOrNull?.modelId;
    final ok = await AppStateScope.of(context)
        .setActiveBrain(local.providerId, model: model);
    if (mounted && !ok) {
      setState(
        () => _message =
            'URI could not activate Ollama. Test the connection and try again.',
      );
    }
  }

  Future<void> _saveCloudKey() async {
    final providerId = _cloudProviderId;
    final key = _keyController.text.trim();
    if (providerId == null || key.isEmpty) {
      setState(() => _message = 'Choose a provider and enter its API key.');
      return;
    }
    setState(() {
      _savingKey = true;
      _message = null;
    });
    final state = AppStateScope.of(context);
    final saved = await state.submitProviderKey(providerId, key);
    final activated = saved != null && await state.setActiveBrain(providerId);
    if (!mounted) return;
    setState(() {
      _savingKey = false;
      _message = activated
          ? 'Your API key was saved and this provider is now your Active Brain.'
          : 'URI could not save and activate this provider. Check the key and try again.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Scaffold(
      backgroundColor: colors.canvas,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(vertical: UriSpace.lg),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Padding(
                padding: const EdgeInsets.all(UriSpace.xl),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const UriWordmark(markSize: 40, showTagline: true),
                    const SizedBox(height: UriSpace.lg),
                    Text(
                      'Give URI a Brain',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: UriSpace.sm),
                    const Text(
                      'Connect local Ollama or add an encrypted API key before your first chat. URI uses your Active Brain for reasoning and response authoring.',
                    ),
                    const SizedBox(height: UriSpace.lg),
                    _ChoiceCard(
                      title: 'Local Model (Ollama)',
                      subtitle: 'Use a model running on this computer.',
                      icon: Icons.lan_outlined,
                      selected: _choice == _BrainSetupChoice.local,
                      onTap: () => setState(() {
                        _choice = _BrainSetupChoice.local;
                        _message = null;
                      }),
                    ),
                    const SizedBox(height: UriSpace.sm),
                    _ChoiceCard(
                      title: 'Cloud Provider (API Key)',
                      subtitle:
                          'Use an encrypted key from a supported provider.',
                      icon: Icons.cloud_outlined,
                      selected: _choice == _BrainSetupChoice.cloud,
                      onTap: () => setState(() {
                        _choice = _BrainSetupChoice.cloud;
                        _cloudProviderId ??=
                            _cloudProviders.firstOrNull?.providerId;
                        _message = null;
                      }),
                    ),
                    if (_choice == _BrainSetupChoice.local) ...[
                      const SizedBox(height: UriSpace.md),
                      FilledButton.icon(
                        onPressed: _testing ? null : _testLocal,
                        icon: const Icon(Icons.lan_outlined),
                        label: Text(
                          _testing
                              ? 'Testing Ollama…'
                              : 'Test local Ollama connection',
                        ),
                      ),
                      const SizedBox(height: UriSpace.sm),
                      OutlinedButton.icon(
                        onPressed: _chooseLocal,
                        icon: const Icon(Icons.psychology_outlined),
                        label: const Text('Use Ollama as Active Brain'),
                      ),
                    ],
                    const SizedBox(height: UriSpace.md),
                    Text(
                      'Prefer OpenAI, Anthropic, Groq, Google, or OpenRouter?',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    Text(
                      'Open Model Providers after setup to save an encrypted API key, select its model, then make it your Active Brain.',
                      style: TextStyle(color: colors.inkFaint),
                    ),
                    if (_choice == _BrainSetupChoice.cloud) ...[
                      const SizedBox(height: UriSpace.md),
                      DropdownButtonFormField<String>(
                        initialValue: _cloudProviderId,
                        decoration: const InputDecoration(
                          labelText: 'Cloud provider',
                        ),
                        items: [
                          for (final provider in _cloudProviders)
                            DropdownMenuItem(
                              value: provider.providerId,
                              child: Text(provider.displayName),
                            ),
                        ],
                        onChanged: (value) =>
                            setState(() => _cloudProviderId = value),
                      ),
                      const SizedBox(height: UriSpace.sm),
                      TextField(
                        controller: _keyController,
                        obscureText: true,
                        enableSuggestions: false,
                        autocorrect: false,
                        decoration: const InputDecoration(labelText: 'API key'),
                      ),
                      const SizedBox(height: UriSpace.sm),
                      FilledButton.icon(
                        onPressed: _savingKey ? null : _saveCloudKey,
                        icon: const Icon(Icons.key_outlined),
                        label: Text(
                          _savingKey
                              ? 'Saving encrypted key...'
                              : 'Save Key & Set as Active Brain',
                        ),
                      ),
                    ],
                    if (_message != null)
                      Padding(
                        padding: const EdgeInsets.only(top: UriSpace.md),
                        child: Text(_message!),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

enum _BrainSetupChoice { local, cloud }

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Material(
      color: selected ? colors.accentSoft : colors.surface,
      borderRadius: BorderRadius.circular(UriRadius.sm),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: Container(
          padding: const EdgeInsets.all(UriSpace.md),
          decoration: BoxDecoration(
            border: Border.all(color: selected ? colors.accent : colors.border),
            borderRadius: BorderRadius.circular(UriRadius.sm),
          ),
          child: Row(
            children: [
              Icon(icon, color: selected ? colors.accent : colors.inkFaint),
              const SizedBox(width: UriSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleSmall),
                    Text(subtitle, style: TextStyle(color: colors.inkFaint)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

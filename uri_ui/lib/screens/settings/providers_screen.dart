import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show ProviderEntry, UsageLimitStatus;
import '../../theme/uri_theme.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_pill.dart';

/// M22.5: Model provider catalogue and API key management screen.
///
/// Allows users to view supported LLM providers, configure encrypted-at-rest
/// API keys (write-only, never redisplayed), and set base_url or model overrides.
class ProvidersScreen extends StatefulWidget {
  const ProvidersScreen({super.key});

  @override
  State<ProvidersScreen> createState() => _ProvidersScreenState();
}

class _ProvidersScreenState extends State<ProvidersScreen> {
  List<ProviderEntry> _providers = const [];
  bool _loading = true;
  String? _errorMessage;
  String? _successMessage;
  UsageLimitStatus? _usageLimits;
  AppState? _state;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _state = AppStateScope.of(context);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _loadProviders();
      if (mounted) _loadUsageLimits();
    });
  }

  Future<void> _loadUsageLimits() async {
    final state = _state ?? AppStateScope.of(context);
    final limits = await state.getUsageLimitStatus();
    if (mounted) setState(() => _usageLimits = limits);
  }

  Future<void> _loadProviders() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    final state = _state ?? AppStateScope.of(context);
    try {
      final list = await state.listProviders();
      if (!mounted) return;
      setState(() {
        _providers = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _errorMessage = 'Could not load provider catalogue: $e';
      });
    }
  }

  Future<void> _showKeyDialog(ProviderEntry provider) async {
    final state = _state ?? AppStateScope.of(context);
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => _KeyDialog(
        provider: provider,
        state: state,
        onSuccess: (message) {
          if (!mounted) return;
          setState(() {
            _successMessage = message;
          });
          _loadProviders();
        },
      ),
    );
  }

  Future<void> _showConfigDialog(ProviderEntry provider) async {
    final state = _state ?? AppStateScope.of(context);
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => _ConfigDialog(
        provider: provider,
        state: state,
        onSuccess: (message) {
          if (!mounted) return;
          setState(() {
            _successMessage = message;
          });
          _loadProviders();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final basic = (_state?.accountInfo?.experienceTier ?? 'BASIC') == 'BASIC';

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: ScreenHeader(
              title: 'Model Providers',
              subtitle: basic
                  ? 'Connect a provider and safely save its access key.'
                  : 'Configure supported LLM providers, encrypted API keys, and endpoint overrides. Submitted keys are encrypted at rest with Fernet and never redisplayed.',
            ),
          ),
          if (_usageLimits?.ceilingReached == true || _usageLimits?.warning == true)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: UriSpace.lg, vertical: UriSpace.sm),
                child: Material(
                  color: _usageLimits!.ceilingReached ? colors.dangerSoft : colors.warningSoft,
                  borderRadius: BorderRadius.circular(UriRadius.md),
                  child: Padding(
                    padding: const EdgeInsets.all(UriSpace.md),
                    child: Text(_usageLimits!.ceilingReached
                        ? 'Your monthly usage limit has been reached. Add or change a limit in Usage settings to continue.'
                        : 'You are close to your monthly usage limit.'),
                  ),
                ),
              ),
            ),
          if (_errorMessage != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: UriSpace.lg,
                  vertical: UriSpace.sm,
                ),
                child: Material(
                  color: colors.dangerSoft,
                  borderRadius: BorderRadius.circular(UriRadius.md),
                  child: Padding(
                    padding: const EdgeInsets.all(UriSpace.md),
                    child: Row(
                      children: [
                        Icon(Icons.error_outline, color: colors.danger),
                        const SizedBox(width: UriSpace.sm),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: TextStyle(color: colors.danger),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          if (_successMessage != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: UriSpace.lg,
                  vertical: UriSpace.sm,
                ),
                child: Material(
                  color: colors.successSoft,
                  borderRadius: BorderRadius.circular(UriRadius.md),
                  child: Padding(
                    padding: const EdgeInsets.all(UriSpace.md),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: colors.success),
                        const SizedBox(width: UriSpace.sm),
                        Expanded(
                          child: Text(
                            _successMessage!,
                            style: TextStyle(color: colors.success),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 16),
                          onPressed: () => setState(() => _successMessage = null),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          if (_loading)
            const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_providers.isEmpty)
            SliverFillRemaining(
              child: Center(
                child: Text(
                  'No providers found in catalogue.',
                  style: TextStyle(color: colors.inkFaint),
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.all(UriSpace.lg),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final provider = _providers[index];
                    return _ProviderCard(
                      provider: provider,
                      onConfigureKey: () => _showKeyDialog(provider),
                      onEditConfig: () => _showConfigDialog(provider),
                    );
                  },
                  childCount: _providers.length,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({
    required this.provider,
    required this.onConfigureKey,
    required this.onEditConfig,
  });

  final ProviderEntry provider;
  final VoidCallback onConfigureKey;
  final VoidCallback onEditConfig;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    final statusPill = provider.configured
        ? StatusPill(
            label: provider.lastFour != null
                ? 'Configured (···${provider.lastFour})'
                : 'Configured',
            foreground: colors.success,
            background: colors.successSoft,
          )
        : StatusPill(
            label: 'Not Configured',
            foreground: colors.inkFaint,
            background: colors.surfaceSunken,
          );

    final availabilityPill = provider.available
        ? StatusPill(
            label: 'Available',
            foreground: colors.accentInk,
            background: colors.accentSoft,
          )
        : StatusPill(
            label: 'Unreachable',
            foreground: colors.warning,
            background: colors.warningSoft,
          );

    return Card(
      margin: const EdgeInsets.only(bottom: UriSpace.md),
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    provider.displayName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                statusPill,
                const SizedBox(width: UriSpace.sm),
                availabilityPill,
              ],
            ),
            const SizedBox(height: UriSpace.xs),
            Text(
              'Adapter: ${provider.adapter}  •  Endpoint: ${provider.baseUrl}',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: colors.inkFaint),
            ),
            const SizedBox(height: UriSpace.md),
            // Wrap, not Row: at narrower card widths (e.g. the BASIC-tier
            // layout, or a constrained settings content width) two
            // full-width icon buttons side by side can overflow a plain
            // Row - wrapping to a second line keeps both fully visible
            // instead of silently clipping content off-screen.
            Wrap(
              alignment: WrapAlignment.end,
              spacing: UriSpace.sm,
              runSpacing: UriSpace.xs,
              children: [
                OutlinedButton.icon(
                  icon: const Icon(Icons.settings_outlined, size: 18),
                  label: const Text('Endpoint Config'),
                  onPressed: onEditConfig,
                ),
                FilledButton.icon(
                  icon: const Icon(Icons.key_outlined, size: 18),
                  label: Text(
                    provider.configured ? 'Update Key' : 'Add Key',
                  ),
                  onPressed: onConfigureKey,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _KeyDialog extends StatefulWidget {
  const _KeyDialog({
    required this.provider,
    required this.state,
    required this.onSuccess,
  });

  final ProviderEntry provider;
  final AppState state;
  final ValueChanged<String> onSuccess;

  @override
  State<_KeyDialog> createState() => _KeyDialogState();
}

class _KeyDialogState extends State<_KeyDialog> {
  final _keyController = TextEditingController();
  bool _submitting = false;
  String? _dialogError;

  @override
  void dispose() {
    _keyController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    final rawKey = _keyController.text.trim();
    if (rawKey.isEmpty) {
      setState(() {
        _dialogError = 'API key cannot be empty.';
      });
      return;
    }

    setState(() {
      _submitting = true;
      _dialogError = null;
    });

    final result = await widget.state.submitProviderKey(
      widget.provider.providerId,
      rawKey,
    );

    // Instantly zero and clear controller to avoid retaining key in memory
    _keyController.clear();

    if (!mounted) return;

    if (result != null) {
      widget.onSuccess(
        'Key saved for ${widget.provider.displayName} (ending in ${result.lastFour}).',
      );
      Navigator.of(context).pop();
    } else {
      setState(() {
        _submitting = false;
        _dialogError =
            'Failed to save key. Verify backend authentication and try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    return AlertDialog(
      title: Text('Configure Key for ${widget.provider.displayName}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Provide an API key for ${widget.provider.displayName}. Keys are encrypted with PBKDF2 + Fernet at rest and are write-only.',
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: colors.inkFaint),
            ),
            const SizedBox(height: UriSpace.md),
            TextField(
              controller: _keyController,
              obscureText: true,
              autofocus: true,
              decoration: InputDecoration(
                labelText: 'API Key',
                hintText: 'Paste secret key',
                prefixIcon: const Icon(Icons.key_outlined),
                border: const OutlineInputBorder(),
                errorText: _dialogError,
              ),
            ),
            if (_submitting) ...[
              const SizedBox(height: UriSpace.md),
              const Center(child: CircularProgressIndicator()),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _submitting
              ? null
              : () {
                  _keyController.clear();
                  Navigator.of(context).pop();
                },
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _submitting ? null : _handleSubmit,
          child: const Text('Save Encrypted Key'),
        ),
      ],
    );
  }
}

class _ConfigDialog extends StatefulWidget {
  const _ConfigDialog({
    required this.provider,
    required this.state,
    required this.onSuccess,
  });

  final ProviderEntry provider;
  final AppState state;
  final ValueChanged<String> onSuccess;

  @override
  State<_ConfigDialog> createState() => _ConfigDialogState();
}

class _ConfigDialogState extends State<_ConfigDialog> {
  late final TextEditingController _urlController;
  late final TextEditingController _modelController;
  bool _saving = false;
  String? _dialogError;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: widget.provider.baseUrl);
    _modelController = TextEditingController();
  }

  @override
  void dispose() {
    _urlController.dispose();
    _modelController.dispose();
    super.dispose();
  }

  Future<void> _handleSave() async {
    setState(() {
      _saving = true;
      _dialogError = null;
    });

    final ok = await widget.state.updateProviderConfig(
      widget.provider.providerId,
      baseUrl: _urlController.text.trim().isNotEmpty
          ? _urlController.text.trim()
          : null,
      model: _modelController.text.trim().isNotEmpty
          ? _modelController.text.trim()
          : null,
    );

    if (!mounted) return;

    if (ok) {
      widget.onSuccess(
        'Updated configuration for ${widget.provider.displayName}.',
      );
      Navigator.of(context).pop();
    } else {
      setState(() {
        _saving = false;
        _dialogError = 'Failed to update provider configuration.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Settings for ${widget.provider.displayName}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                labelText: 'Base URL Override',
                hintText: 'https://...',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: UriSpace.md),
            TextField(
              controller: _modelController,
              decoration: const InputDecoration(
                labelText: 'Model Override (optional)',
                hintText: 'e.g. gpt-4o, llama-3.3-70b',
                border: OutlineInputBorder(),
              ),
            ),
            if (_dialogError != null) ...[
              const SizedBox(height: UriSpace.sm),
              Text(
                _dialogError!,
                style: const TextStyle(color: Colors.red),
              ),
            ],
            if (_saving) ...[
              const SizedBox(height: UriSpace.md),
              const Center(child: CircularProgressIndicator()),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _saving ? null : _handleSave,
          child: const Text('Save Overrides'),
        ),
      ],
    );
  }
}

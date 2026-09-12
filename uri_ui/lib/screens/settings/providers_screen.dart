import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show ProviderEntry, UsageLimitStatus;
import '../../theme/uri_theme.dart';
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
  String _section = 'Accounts / API Keys';

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
    final visible = switch (_section) {
      'Local Models' =>
        _providers.where((provider) => provider.adapter == 'ollama').toList(),
      'Custom Endpoints' =>
        _providers.where((provider) => provider.adapter != 'ollama').toList(),
      _ => _providers,
    };
    return Material(
      color: Colors.transparent,
      child: ListView(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        children: [
          Text(
            'Model Providers',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: UriSpace.xs),
          Text(
            basic ? 'Connect a provider and safely save its access key.' : 'Encrypted keys, local models, endpoints, and URI\'s primary Brain.',
            style: Theme.of(context).textTheme.bodyMedium
                ?.copyWith(color: colors.inkFaint),
          ),
          const SizedBox(height: UriSpace.md),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(UriSpace.md),
              child: Row(
                children: [
                  Icon(Icons.psychology_outlined, color: colors.accentInk),
                  const SizedBox(width: UriSpace.sm),
                  Expanded(
                    child: Text(
                      _providers
                              .where((provider) => provider.activeBrain)
                              .map(
                                (provider) =>
                                    '${provider.displayName} · ${provider.activeModel ?? ''}',
                              )
                              .firstOrNull ??
                          'No Active Brain selected',
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: UriSpace.md),
          Wrap(
            spacing: UriSpace.sm,
            runSpacing: UriSpace.xs,
            children: [
              for (final section in const [
                'Accounts / API Keys',
                'Local Models',
                'Custom Endpoints',
              ])
                ChoiceChip(
                  label: Text(section),
                  selected: _section == section,
                  onSelected: (_) => setState(() => _section = section),
                ),
            ],
          ),
          if (_usageLimits?.ceilingReached == true ||
              _usageLimits?.warning == true)
            Padding(
              padding: const EdgeInsets.only(top: UriSpace.md),
              child: Text(
                _usageLimits!.ceilingReached
                    ? 'Your monthly usage limit has been reached.'
                    : 'You are close to your monthly usage limit.',
                style: TextStyle(
                  color: _usageLimits!.ceilingReached
                      ? colors.danger
                      : colors.warning,
                ),
              ),
            ),
          if (_errorMessage != null)
            Padding(
              padding: const EdgeInsets.only(top: UriSpace.md),
              child: Text(
                _errorMessage!,
                style: TextStyle(color: colors.danger),
              ),
            ),
          if (_successMessage != null)
            Padding(
              padding: const EdgeInsets.only(top: UriSpace.md),
              child: Text(
                _successMessage!,
                style: TextStyle(color: colors.success),
              ),
            ),
          const SizedBox(height: UriSpace.md),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(UriSpace.xl),
                child: CircularProgressIndicator(),
              ),
            )
          else if (visible.isEmpty)
            Text(
              'No providers in this section.',
              style: TextStyle(color: colors.inkFaint),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: visible.length,
              itemBuilder: (context, index) {
                final provider = visible[index];
                return _ProviderCard(
                  provider: provider,
                  onConfigureKey: () => _showKeyDialog(provider),
                  onEditConfig: () => _showConfigDialog(provider),
                  onSetActiveBrain: (model) =>
                      _confirmActiveBrain(provider, model),
                );
              },
            ),
        ],
      ),
    );
  }

  Future<void> _confirmActiveBrain(
    ProviderEntry provider,
    String? model,
  ) async {
    final selected = provider.models
        .where((item) => item.modelId == model)
        .firstOrNull;
    final modelName = selected?.displayName ?? model ?? 'default model';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Change Active Brain?'),
        content: Text(
          'This will change the primary model URI uses for reasoning and planning to ${provider.displayName} ($modelName).',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    if (!mounted) return;
    final state = _state ?? AppStateScope.of(context);
    final success = await state.setActiveBrain(
      provider.providerId,
      model: model,
    );
    if (!mounted) return;
    if (success) {
      setState(
        () => _successMessage =
            '${provider.displayName} is now URI\'s Active Brain.',
      );
      await _loadProviders();
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Active Brain updated.')));
    } else {
      setState(() => _errorMessage = 'URI could not change the Active Brain.');
    }
  }
}

class _ProviderCard extends StatefulWidget {
  const _ProviderCard({
    required this.provider,
    required this.onConfigureKey,
    required this.onEditConfig,
    required this.onSetActiveBrain,
  });

  final ProviderEntry provider;
  final VoidCallback onConfigureKey;
  final VoidCallback onEditConfig;
  final ValueChanged<String?> onSetActiveBrain;

  @override
  State<_ProviderCard> createState() => _ProviderCardState();
}

class _ProviderCardState extends State<_ProviderCard> {
  String? _selectedModel;

  @override
  void initState() {
    super.initState();
    _selectedModel =
        widget.provider.activeModel ??
        widget.provider.models.firstOrNull?.modelId;
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    final provider = widget.provider;
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
            Wrap(
              spacing: UriSpace.sm,
              runSpacing: UriSpace.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  provider.displayName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                statusPill,
                availabilityPill,
                if (provider.activeBrain) ...[
                  StatusPill(
                    label: 'Active Brain',
                    foreground: colors.accentInk,
                    background: colors.accentSoft,
                  ),
                ],
              ],
            ),
            const SizedBox(height: UriSpace.xs),
            Text(
              'Adapter: ${provider.adapter}  •  Endpoint: ${provider.baseUrl}',
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: colors.inkFaint),
            ),
            const SizedBox(height: UriSpace.md),
            if (provider.models.isNotEmpty) ...[
              DropdownButtonFormField<String>(
                initialValue: _selectedModel,
                decoration: const InputDecoration(
                  labelText: 'Model',
                  border: OutlineInputBorder(),
                ),
                items: [
                  for (final model in provider.models)
                    DropdownMenuItem(
                      value: model.modelId,
                      child: Text(model.displayName),
                    ),
                ],
                onChanged: provider.activeBrain
                    ? null
                    : (value) => setState(() => _selectedModel = value),
              ),
              const SizedBox(height: UriSpace.md),
            ],
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
                  onPressed: widget.onEditConfig,
                ),
                FilledButton.icon(
                  icon: const Icon(Icons.key_outlined, size: 18),
                  label: Text(provider.configured ? 'Update Key' : 'Add Key'),
                  onPressed: widget.onConfigureKey,
                ),
                OutlinedButton.icon(
                  icon: const Icon(Icons.psychology_outlined, size: 18),
                  label: const Text('Set as Active Brain'),
                  onPressed: provider.activeBrain
                      ? null
                      : () => widget.onSetActiveBrain(_selectedModel),
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
              style: Theme.of(context).textTheme.bodySmall
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
              Text(_dialogError!, style: const TextStyle(color: Colors.red)),
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

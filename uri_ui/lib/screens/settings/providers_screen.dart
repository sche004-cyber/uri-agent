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

  // Live UX Repair: the "Connect Provider" method cards' "Continue"
  // buttons previously did nothing at all (`onPressed: () {}`) - a
  // reproduced, confirmed defect. Continue now takes the User to the
  // real next step: the matching provider group already rendered below,
  // scrolled into view via the enclosing page's Scrollable.
  final _apiKeyGroupKey = GlobalKey();
  final _localGroupKey = GlobalKey();

  Future<void> _scrollToGroup(GlobalKey key) async {
    final target = key.currentContext;
    if (target == null) return;
    await Scrollable.ensureVisible(
      target,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      alignment: 0.05,
    );
  }

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
    final apiProviders = _providers
        .where(
          (provider) =>
              provider.adapter != 'ollama' &&
              provider.providerId != 'lm_studio',
        )
        .toList(growable: false);
    final localProviders = _providers
        .where(
          (provider) =>
              provider.adapter == 'ollama' ||
              provider.providerId == 'lm_studio',
        )
        .toList(growable: false);
    return Material(
      color: Colors.transparent,
      child: ListView(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        children: [
          Text(
            'Connect a provider',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: UriSpace.xs),
          Text(
            'Choose how URI reaches a Brain. Models become selectable only after URI verifies that they can serve requests.',
            style: Theme.of(context).textTheme.bodyMedium
                ?.copyWith(color: colors.inkFaint),
          ),
          const SizedBox(height: UriSpace.md),
          _ConnectProviderOverview(
            providers: _providers,
            routing: _state?.fallbackRouting,
            onEditRouting: _showFallbackRoutingDialog,
            onContinueApiKey: () => _scrollToGroup(_apiKeyGroupKey),
            onContinueLocal: () => _scrollToGroup(_localGroupKey),
          ),
          /* Legacy provider-card/tabs layout retained only as a source
             reference during this repair; it is intentionally not rendered.
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
          */
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
          else
            Wrap(
              spacing: UriSpace.md,
              runSpacing: UriSpace.md,
              children: [
                KeyedSubtree(
                  key: _apiKeyGroupKey,
                  child: _ProviderConnectionGroup(
                    title: 'API Key Providers',
                    tag: 'OpenAI, Anthropic, Gemini, Groq, OpenRouter',
                    providers: apiProviders,
                    onConfigureKey: _showKeyDialog,
                    onEditConfig: _showConfigDialog,
                    onSetActiveBrain: _confirmActiveBrain,
                  ),
                ),
                KeyedSubtree(
                  key: _localGroupKey,
                  child: _ProviderConnectionGroup(
                    title: 'Local Model Providers',
                    tag: 'Ollama, LM Studio',
                    providers: localProviders,
                    onConfigureKey: _showKeyDialog,
                    onEditConfig: _showConfigDialog,
                    onSetActiveBrain: _confirmActiveBrain,
                  ),
                ),
              ],
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

  Future<void> _showFallbackRoutingDialog() async {
    final state = _state ?? AppStateScope.of(context);
    await showDialog<void>(
      context: context,
      builder: (_) => _FallbackRoutingDialog(
        providers: _providers,
        initialConfig: state.fallbackRouting ?? const <String, dynamic>{},
        onSave: (config) async {
          final saved = await state.updateFallbackRouting(config);
          if (mounted && saved) {
            setState(() => _successMessage = 'Fallback routing updated.');
          }
          return saved;
        },
      ),
    );
  }
}

class _ConnectProviderOverview extends StatelessWidget {
  const _ConnectProviderOverview({
    required this.providers,
    required this.routing,
    required this.onEditRouting,
    required this.onContinueApiKey,
    required this.onContinueLocal,
  });

  final List<ProviderEntry> providers;
  final Map<String, dynamic>? routing;
  final VoidCallback onEditRouting;
  final VoidCallback onContinueApiKey;
  final VoidCallback onContinueLocal;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Connect Provider',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const SizedBox(height: UriSpace.xs),
      Text(
        'Authentication method comes first; URI only shows provider-specific options.',
        style: Theme.of(context).textTheme.bodyMedium,
      ),
      const SizedBox(height: UriSpace.md),
      Wrap(
        spacing: UriSpace.md,
        runSpacing: UriSpace.md,
        children: [
          const _ConnectionMethodCard(
            title: 'Subscription',
            tag: 'OAuth account',
            detail:
                'OpenAI, Claude, Gemini\nNot currently available — no officially supported direct connection exists yet.',
            enabled: false,
          ),
          _ConnectionMethodCard(
            title: 'API Key',
            tag: 'Encrypted credential',
            detail:
                'Groq, OpenAI API, Anthropic API, Gemini API, OpenRouter',
            enabled: true,
            onContinue: onContinueApiKey,
          ),
          _ConnectionMethodCard(
            title: 'Local Models',
            tag: 'Local endpoint',
            detail: 'Ollama, LM Studio',
            enabled: true,
            onContinue: onContinueLocal,
          ),
        ],
      ),
      const SizedBox(height: UriSpace.md),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'How connection works',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: UriSpace.xs),
              const Text(
                '1. Choose provider type\n2. Add key / configure endpoint\n3. URI verifies model reachability\n4. Select Active Brain or use URI Auto',
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: UriSpace.md),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Fallback Routing',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: UriSpace.xs),
              const Text(
                'Fallbacks populate only from models URI has actually discovered and verified.',
              ),
              const SizedBox(height: UriSpace.sm),
              Text(_routingSummary('Primary Brain', routing?['primary'])),
              Text(_routingSummary('Fallback 1', routing?['fallback_1'])),
              Text(_routingSummary('Fallback 2', routing?['fallback_2'])),
              Align(
                alignment: Alignment.centerRight,
                child: OutlinedButton(
                  onPressed: onEditRouting,
                  child: const Text('Edit Routing'),
                ),
              ),
              Text(
                'Models are discovered dynamically from connected providers. A model is selectable only when URI can verify it is usable.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    ],
  );

  String _routingSummary(String label, dynamic value) {
    if (value == 'auto') return '$label: URI Auto';
    if (value is Map) {
      return '$label: ${value['provider_id']} • ${value['model']}';
    }
    return '$label: None';
  }
}

class _ProviderConnectionGroup extends StatelessWidget {
  const _ProviderConnectionGroup({
    required this.title,
    required this.tag,
    required this.providers,
    required this.onConfigureKey,
    required this.onEditConfig,
    required this.onSetActiveBrain,
  });

  final String title;
  final String tag;
  final List<ProviderEntry> providers;
  final ValueChanged<ProviderEntry> onConfigureKey;
  final ValueChanged<ProviderEntry> onEditConfig;
  final void Function(ProviderEntry, String?) onSetActiveBrain;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 310,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: UriSpace.xs),
            Text(tag, style: Theme.of(context).textTheme.bodySmall),
            const Divider(height: UriSpace.lg),
            for (final provider in providers) ...[
              Text(
                provider.displayName,
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: UriSpace.xs),
              Text(
                provider.configured
                    ? 'Configured: credential or endpoint saved${provider.lastFour == null ? '' : ' (••••${provider.lastFour})'}'
                    : 'Not configured',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                provider.available
                    ? 'Reachable: endpoint ping succeeded'
                    : 'Reachable: not confirmed',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                provider.models.any((model) => model.verified)
                    ? 'Models discovered; verified models are selectable below.'
                    : 'Connect provider to discover models.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              if (provider.models.any((model) => model.verified))
                Wrap(
                  spacing: UriSpace.xs,
                  runSpacing: UriSpace.xs,
                  children: [
                    for (final model in provider.models.where(
                      (model) => model.verified,
                    ))
                      ActionChip(
                        label: Text(model.displayName),
                        avatar:
                            provider.activeBrain &&
                                provider.activeModel == model.modelId
                            ? const Icon(Icons.psychology, size: 16)
                            : const Icon(Icons.verified_outlined, size: 16),
                        onPressed:
                            provider.activeBrain &&
                                provider.activeModel == model.modelId
                            ? null
                            : () => onSetActiveBrain(provider, model.modelId),
                      ),
                  ],
                ),
              const SizedBox(height: UriSpace.xs),
              Wrap(
                spacing: UriSpace.xs,
                children: [
                  OutlinedButton(
                    onPressed: () => onEditConfig(provider),
                    child: const Text('Endpoint'),
                  ),
                  if (provider.adapter != 'ollama')
                    FilledButton(
                      onPressed: () => onConfigureKey(provider),
                      child: Text(
                        provider.configured ? 'Update key' : 'Add key',
                      ),
                    ),
                ],
              ),
              const Divider(height: UriSpace.lg),
            ],
          ],
        ),
      ),
    ),
  );
}

class _FallbackRoutingDialog extends StatefulWidget {
  const _FallbackRoutingDialog({
    required this.providers,
    required this.initialConfig,
    required this.onSave,
  });

  final List<ProviderEntry> providers;
  final Map<String, dynamic> initialConfig;
  final Future<bool> Function(Map<String, dynamic>) onSave;

  @override
  State<_FallbackRoutingDialog> createState() => _FallbackRoutingDialogState();
}

class _FallbackRoutingDialogState extends State<_FallbackRoutingDialog> {
  static const _auto = 'auto';
  String? _primary;
  String? _fallback1;
  String? _fallback2;
  bool _saving = false;
  String? _error;

  List<_VerifiedModel> get _verified => [
    for (final provider in widget.providers)
      for (final model in provider.models.where((model) => model.verified))
        _VerifiedModel(
          provider.providerId,
          model.modelId,
          '${provider.displayName} • ${model.displayName}',
        ),
  ];

  String? _selectionFor(dynamic value) => value is Map
      ? '${value['provider_id']}::${value['model']}'
      : value == _auto
      ? _auto
      : null;

  @override
  void initState() {
    super.initState();
    _primary = _selectionFor(widget.initialConfig['primary']);
    _fallback1 = _selectionFor(widget.initialConfig['fallback_1']) ?? _auto;
    _fallback2 = _selectionFor(widget.initialConfig['fallback_2']);
  }

  Map<String, dynamic>? _asConfig(String? selection) {
    if (selection == null || selection == _auto) return null;
    final parts = selection.split('::');
    return parts.length == 2
        ? {'provider_id': parts[0], 'model': parts[1]}
        : null;
  }

  Future<void> _save() async {
    if (_primary == null) {
      setState(() => _error = 'Choose a verified Primary Brain.');
      return;
    }
    final selected = [
      _primary,
      _fallback1,
      _fallback2,
    ].whereType<String>().where((value) => value != _auto).toList();
    if (selected.toSet().length != selected.length) {
      setState(
        () => _error = 'Choose different models for each fallback. URI Auto may repeat its own safe route.',
      );
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    final config = <String, dynamic>{
      'primary': _asConfig(_primary),
      'fallback_1': _fallback1 == _auto ? _auto : _asConfig(_fallback1),
      'fallback_2': _asConfig(_fallback2),
    };
    final saved = await widget.onSave(config);
    if (!mounted) return;
    if (saved) {
      Navigator.of(context).pop();
    } else {
      setState(() {
        _saving = false;
        _error = 'URI could not save routing.';
      });
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Edit fallback routing'),
    content: SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _selector(
            'Primary Brain',
            _primary,
            _verified,
            (value) => setState(() => _primary = value),
            allowNone: false,
          ),
          const SizedBox(height: UriSpace.md),
          _selector(
            'Fallback 1',
            _fallback1,
            _verified,
            (value) => setState(() => _fallback1 = value),
            allowAuto: true,
          ),
          const SizedBox(height: UriSpace.md),
          _selector(
            'Fallback 2',
            _fallback2,
            _verified,
            (value) => setState(() => _fallback2 = value),
            allowNone: true,
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: UriSpace.sm),
              child: Text(
                _error!,
                style: TextStyle(color: UriColors.of(context).danger),
              ),
            ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: _saving ? null : () => Navigator.of(context).pop(),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: _saving ? null : _save,
        child: const Text('Save routing'),
      ),
    ],
  );

  Widget _selector(
    String label,
    String? value,
    List<_VerifiedModel> models,
    ValueChanged<String?> onChanged, {
    bool allowAuto = false,
    bool allowNone = false,
  }) => DropdownButtonFormField<String>(
    value:
        models.any((model) => model.value == value) ||
            (allowAuto && value == _auto)
        ? value
        : null,
    decoration: InputDecoration(
      labelText: label,
      border: const OutlineInputBorder(),
    ),
    items: [
      if (allowAuto)
        const DropdownMenuItem(value: _auto, child: Text('URI Auto')),
      if (allowNone) const DropdownMenuItem(value: null, child: Text('None')),
      for (final model in models)
        DropdownMenuItem(value: model.value, child: Text(model.label)),
    ],
    onChanged: onChanged,
  );
}

class _VerifiedModel {
  const _VerifiedModel(this.providerId, this.modelId, this.label);
  final String providerId;
  final String modelId;
  final String label;
  String get value => '$providerId::$modelId';
}

class _ConnectionMethodCard extends StatelessWidget {
  const _ConnectionMethodCard({
    required this.title,
    required this.tag,
    required this.detail,
    this.enabled = true,
    this.onContinue,
  });
  final String title;
  final String tag;
  final String detail;
  final bool enabled;

  /// Live UX Repair: previously always `() {}` regardless of [enabled] -
  /// an enabled button that visibly did nothing when pressed. Null here
  /// means "disabled and explained" (the [detail] text already covers
  /// why); a real, non-null callback is the "real next step" a working
  /// enabled control must lead to.
  final VoidCallback? onContinue;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 290,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Chip(label: Text(tag)),
            const SizedBox(height: UriSpace.sm),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: UriSpace.xs),
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Text(detail),
            ),
            const SizedBox(height: UriSpace.md),
            FilledButton(
              onPressed: enabled ? onContinue : null,
              child: const Text('Continue'),
            ),
          ],
        ),
      ),
    ),
  );
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

  /// The real, selectable model ids for this provider - for Ollama,
  /// this is the actually-installed list reported live by the backend
  /// (never the static catalogue, which can list a model that was
  /// never pulled, or omit one that was - see OllamaProvider.
  /// list_installed_models()); for a cloud adapter (no local
  /// introspection possible) this stays the catalogue's own model ids.
  List<String> _modelIds(ProviderEntry provider) =>
      provider.adapter == 'ollama' && provider.installedModelIds.isNotEmpty
      ? provider.installedModelIds
      : provider.models.map((m) => m.modelId).toList();

  String _displayFor(ProviderEntry provider, String modelId) =>
      provider.models
          .where((m) => m.modelId == modelId)
          .map((m) => m.displayName)
          .firstOrNull ??
      modelId;

  @override
  void initState() {
    super.initState();
    final ids = _modelIds(widget.provider);
    final active = widget.provider.activeModel;
    _selectedModel = (active != null && ids.contains(active))
        ? active
        : ids.firstOrNull;
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    final provider = widget.provider;
    final modelIds = _modelIds(provider);
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
            if (modelIds.isNotEmpty) ...[
              DropdownButtonFormField<String>(
                initialValue: modelIds.contains(_selectedModel)
                    ? _selectedModel
                    : modelIds.first,
                decoration: const InputDecoration(
                  labelText: 'Model',
                  border: OutlineInputBorder(),
                ),
                items: [
                  for (final modelId in modelIds)
                    DropdownMenuItem(
                      value: modelId,
                      child: Text(_displayFor(provider, modelId)),
                    ),
                ],
                // Always changeable, even when this provider IS the
                // active brain - "activeBrain" locks in a provider+model
                // PAIR, not the whole provider. Locking the dropdown
                // whenever the provider happened to already be active
                // made it impossible to ever switch to a different
                // installed model on that same provider (e.g. a second
                // locally-installed Ollama model) - see
                // onSetActiveBrain's enablement below, which is the
                // actual gate on whether a change would do anything.
                onChanged: (value) => setState(() => _selectedModel = value),
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
                  // Disabled only when the selection would be a no-op
                  // (this exact provider+model pair is already active) -
                  // never merely because the provider itself happens to
                  // already be the active brain, which previously made
                  // switching models on an already-active local provider
                  // impossible.
                  onPressed:
                      (provider.activeBrain &&
                          _selectedModel == provider.activeModel)
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

    if (result?.configured == true) {
      final verification = await widget.state.verifyProvider(
        widget.provider.providerId,
      );
      if (!mounted) return;
      if (verification?.verified != true) {
        setState(() {
          _submitting = false;
          _dialogError =
              'Key stored, but model verification failed: '
              '${verification?.error ?? 'URI could not reach a usable model.'}';
        });
        return;
      }
      widget.onSuccess(
        'Key stored, models discovered, and ${verification!.models.length} model(s) verified for ${widget.provider.displayName}.',
      );
      Navigator.of(context).pop();
    } else {
      setState(() {
        _submitting = false;
        _dialogError =
            'Credential storage failed: '
            '${result?.error ?? 'Could not reach the URI backend.'}';
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

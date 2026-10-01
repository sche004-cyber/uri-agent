import 'package:flutter/material.dart';

import '../../models/edge_intelligence.dart';
import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/status_pill.dart';

/// M33.2 / M31: Edge Brain Lab & Developer Runtime Evidence.
///
/// Truthfully exposes the real Edge qualification state:
/// - Needle 3 = RESIDENT for fast reflex routing and structured extraction
/// - SmolLM2-135M and Qwen2.5-0.5B = BYPASSED / REDUNDANT
/// - STT / OCR / VLM = UNAVAILABLE / UNQUALIFIED
/// - Live interactive routing probe
/// - High-level redacted operational traces (zero private chain-of-thought)
class EdgeLabScreen extends StatefulWidget {
  const EdgeLabScreen({super.key});

  @override
  State<EdgeLabScreen> createState() => _EdgeLabScreenState();
}

class _EdgeLabScreenState extends State<EdgeLabScreen> {
  final TextEditingController _probeController = TextEditingController(
    text: 'hello',
  );
  EdgeProbeResult? _lastProbeResult;
  bool _isProbing = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        AppStateScope.of(context).loadEdgeIntelligence();
      }
    });
  }

  @override
  void dispose() {
    _probeController.dispose();
    super.dispose();
  }

  Future<void> _runProbe(AppState state) async {
    final query = _probeController.text.trim();
    if (query.isEmpty) return;
    setState(() => _isProbing = true);
    final result = await state.probeEdge(query);
    if (mounted) {
      setState(() {
        _lastProbeResult = result;
        _isProbing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final theme = Theme.of(context);
        final colors = UriColors.of(context);

        if (state.isLoadingEdge && state.edgeLabOverview == null) {
          return const Center(child: CircularProgressIndicator());
        }

        final overview = state.edgeLabOverview;
        final settings = state.edgeSettings;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ---- Header & Lifecycle Status ----
              _buildLifecycleHeader(context, overview, settings, state),
              const SizedBox(height: UriSpace.lg),

              // ---- Interactive Reflex Probe ----
              _buildProbeSection(context, state),
              const SizedBox(height: UriSpace.lg),

              _buildExperimentalCandidates(context, state),
              const SizedBox(height: UriSpace.lg),

              // ---- Candidate Qualification Matrix ----
              Text(
                'Candidate Qualification Matrix (M33.2)',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: UriSpace.xs),
              Text(
                'Truthful backend qualification status. Stronger active Main Brain always bypasses weaker edge workers.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.inkFaint,
                ),
              ),
              const SizedBox(height: UriSpace.sm),
              if (overview != null)
                ...overview.candidates.map(
                  (c) => _buildCandidateCard(context, c),
                ),
              const SizedBox(height: UriSpace.lg),

              // ---- Developer Log / Runtime Evidence ----
              Text(
                'Developer Evidence & Routing Trace',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: UriSpace.xs),
              Text(
                'Redacted operational log from GET /intelligence/trace. Never exposes private chain-of-thought.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.inkFaint,
                ),
              ),
              const SizedBox(height: UriSpace.sm),
              _buildTraceList(context, state.edgeTrace),
            ],
          ),
        );
      },
    );
  }

  Widget _buildExperimentalCandidates(BuildContext context, AppState state) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Experimental Candidates',
                  style: theme.textTheme.titleMedium,
                ),
              ),
              FilledButton.icon(
                onPressed: state.isDiscoveringCandidates
                    ? null
                    : state.discoverExperimentalCandidates,
                icon: const Icon(Icons.search),
                label: const Text('Discover local'),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Text(
            'Benchmark-only discovery and qualification. Adding a test model never installs system software, changes PATH/registry, or promotes it into production routing.',
            style: theme.textTheme.bodySmall?.copyWith(color: colors.inkFaint),
          ),
          if (state.experimentalCandidates.isEmpty) ...[
            const SizedBox(height: UriSpace.sm),
            const Text('No candidates discovered yet.'),
          ],
          for (final candidate in state.experimentalCandidates) ...[
            const Divider(height: UriSpace.lg),
            Text(candidate.modelId, style: theme.textTheme.titleSmall),
            Text(
              'Runtime: ${candidate.runtime} Â· Quantization: ${candidate.quantization ?? 'unknown'} Â· Loaded: ${candidate.loadedState}',
              style: theme.textTheme.bodySmall,
            ),
            Text(
              'File size: ${candidate.fileSizeBytes ?? 'unknown'} Â· RAM: ${candidate.ramMib ?? 'unknown'} MiB Â· VRAM: ${candidate.vramMib ?? 'unknown'} MiB',
              style: theme.textTheme.bodySmall,
            ),
            Text(
              'Qualification: ${candidate.qualificationState} Â· Tested: ${candidate.testedCapabilities.isEmpty ? 'none' : candidate.testedCapabilities.join(', ')}',
              style: theme.textTheme.bodySmall,
            ),
            if (candidate.benchmarkEvidence != null)
              Text(
                'Evidence: ${candidate.benchmarkEvidence}',
                style: theme.textTheme.bodySmall,
              ),
            const SizedBox(height: UriSpace.xs),
            OutlinedButton(
              onPressed: () => state.qualifyExperimentalCandidate(candidate),
              child: const Text('Run qualification'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLifecycleHeader(
    BuildContext context,
    EdgeLabOverview? overview,
    EdgeSettings? settings,
    AppState state,
  ) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);
    final lifecycle = overview?.runtimeLifecycle ?? const {};

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.hub_outlined, color: colors.accent, size: 22),
              const SizedBox(width: UriSpace.sm),
              Text('Edge Brain Runtime', style: theme.textTheme.titleMedium),
              const Spacer(),
              StatusPill(
                label: lifecycle['state']?.toString() ?? 'RESIDENT',
                foreground: colors.accent,
                background: colors.accent.withValues(alpha: 0.15),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Text(
            'Managed Storage: ${lifecycle['managed_storage'] ?? 'user-space (.venv-needle)'} · Privileged elevation: ${lifecycle['elevation'] ?? 'none'}',
            style: theme.textTheme.bodySmall?.copyWith(color: colors.inkFaint),
          ),
          const Divider(height: UriSpace.lg),
          if (settings != null) ...[
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Enable Edge Assistance',
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
                Switch(
                  value: settings.enabled,
                  onChanged: (val) {
                    state.updateEdgeSettings(settings.copyWith(enabled: val));
                  },
                ),
              ],
            ),
            const SizedBox(height: UriSpace.xs),
            Row(
              children: [
                Text('Intelligence Mode:', style: theme.textTheme.bodySmall),
                const SizedBox(width: UriSpace.sm),
                DropdownButton<String>(
                  value: settings.intelligenceMode,
                  isDense: true,
                  items: const [
                    DropdownMenuItem(value: 'HYBRID', child: Text('HYBRID')),
                    DropdownMenuItem(
                      value: 'EDGE_ONLY',
                      child: Text('EDGE_ONLY'),
                    ),
                    DropdownMenuItem(
                      value: 'MAIN_BRAIN_PREFERRED',
                      child: Text('MAIN_BRAIN_PREFERRED'),
                    ),
                  ],
                  onChanged: (val) {
                    if (val != null) {
                      state.updateEdgeSettings(
                        settings.copyWith(intelligenceMode: val),
                      );
                    }
                  },
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildProbeSection(BuildContext context, AppState state) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.speed_outlined, color: colors.accent, size: 20),
              const SizedBox(width: UriSpace.sm),
              Text('Live Reflex Probe', style: theme.textTheme.titleMedium),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Text(
            'Test real-time reflex routing latency and decision outcome.',
            style: theme.textTheme.bodySmall?.copyWith(color: colors.inkFaint),
          ),
          const SizedBox(height: UriSpace.sm),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _probeController,
                  decoration: InputDecoration(
                    hintText: 'Enter test query (e.g. hello, ping, status)...',
                    isDense: true,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(UriRadius.sm),
                    ),
                  ),
                  onSubmitted: (_) => _runProbe(state),
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              FilledButton(
                onPressed: _isProbing ? null : () => _runProbe(state),
                child: _isProbing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Probe'),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.xs),
          Wrap(
            spacing: UriSpace.xs,
            runSpacing: UriSpace.xs,
            children: [
              ActionChip(
                label: const Text('hello'),
                onPressed: () {
                  _probeController.text = 'hello';
                  _runProbe(state);
                },
              ),
              ActionChip(
                label: const Text('ping'),
                onPressed: () {
                  _probeController.text = 'ping';
                  _runProbe(state);
                },
              ),
              ActionChip(
                label: const Text('summarize invoices'),
                onPressed: () {
                  _probeController.text = 'summarize invoices';
                  _runProbe(state);
                },
              ),
              ActionChip(
                label: const Text('Open my Downloads folder'),
                onPressed: () {
                  _probeController.text = 'Open my Downloads folder';
                  _runProbe(state);
                },
              ),
              ActionChip(
                label: const Text(
                  'Student Ravi Kumar, roll number B250046CS, fine Rs 7000',
                ),
                onPressed: () {
                  _probeController.text =
                      'Student Ravi Kumar, roll number B250046CS, fine Rs 7000';
                  _runProbe(state);
                },
              ),
            ],
          ),
          if (_lastProbeResult != null) ...[
            const Divider(height: UriSpace.lg),
            _buildProbeResultView(context, _lastProbeResult!),
          ],
        ],
      ),
    );
  }

  Widget _buildProbeResultView(BuildContext context, EdgeProbeResult res) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);
    final isEdge = res.decision == 'EDGE_REPLY';

    final funcCall = res.details?['function_call'] as Map<String, dynamic>?;
    final structured =
        res.details?['structured_output'] as Map<String, dynamic>?;

    return Container(
      padding: const EdgeInsets.all(UriSpace.sm),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: isEdge ? Colors.green : Colors.amber),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              StatusPill(
                label: res.decision,
                foreground: isEdge ? Colors.green : Colors.amber,
                background: (isEdge ? Colors.green : Colors.amber).withValues(
                  alpha: 0.15,
                ),
              ),
              const SizedBox(width: UriSpace.sm),
              Text(
                'Candidate: ${res.candidate}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              Text(
                '${res.latencyMs} ms · ${(res.confidence * 100).toInt()}% conf',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.inkFaint,
                ),
              ),
            ],
          ),
          if (res.advisoryNote != null) ...[
            const SizedBox(height: UriSpace.xs),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: UriSpace.sm,
                vertical: UriSpace.xs,
              ),
              decoration: BoxDecoration(
                color: Colors.amber.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(UriRadius.sm),
                border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, size: 14, color: Colors.amber),
                  const SizedBox(width: UriSpace.xs),
                  Expanded(
                    child: Text(
                      res.advisoryNote!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.amber[900],
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: UriSpace.xs),
          Text(
            'Reason Codes: ${res.reasonCodes.join(', ')}',
            style: theme.textTheme.bodySmall?.copyWith(color: colors.inkSoft),
          ),
          if (funcCall != null) ...[
            const SizedBox(height: UriSpace.xs),
            Text(
              'Function Call: ${funcCall['name']} (${funcCall['arguments']})',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.accent,
                fontFamily: 'monospace',
              ),
            ),
          ],
          if (structured != null) ...[
            const SizedBox(height: UriSpace.xs),
            Text(
              'Structured Record: $structured',
              style: theme.textTheme.bodySmall?.copyWith(
                color: Colors.green,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCandidateCard(
    BuildContext context,
    EdgeCandidateInfo candidate,
  ) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);

    Color badgeColor;
    switch (candidate.status) {
      case 'RESIDENT':
        badgeColor = Colors.green;
        break;
      case 'BYPASSED':
        badgeColor = Colors.amber;
        break;
      default:
        badgeColor = colors.inkFaint;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: UriSpace.sm),
      padding: const EdgeInsets.all(UriSpace.sm),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          StatusPill(
            label: candidate.status,
            foreground: badgeColor,
            background: badgeColor.withValues(alpha: 0.15),
          ),
          const SizedBox(width: UriSpace.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: UriSpace.xs,
                  children: [
                    Text(
                      candidate.name,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      '· ${candidate.role}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colors.inkFaint,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  candidate.detail,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.inkSoft,
                  ),
                ),
                if (candidate.status == 'RESIDENT') ...[
                  const SizedBox(height: 4),
                  Text(
                    'Reflex: ${candidate.reflexAccuracyPct}% · Structured: ${candidate.structuredExtractionPct}% · p50: ${candidate.p50LatencyMs}ms · RAM: ${candidate.ramMb}MB',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: colors.accent,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTraceList(BuildContext context, List<EdgeRoutingEvent> trace) {
    final colors = UriColors.of(context);
    final theme = Theme.of(context);

    if (trace.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(UriSpace.md),
        decoration: BoxDecoration(
          color: colors.surfaceSunken,
          borderRadius: BorderRadius.circular(UriRadius.sm),
        ),
        child: Center(
          child: Text(
            'No routing events recorded yet. Run a probe above or ask a question in chat.',
            style: theme.textTheme.bodySmall?.copyWith(color: colors.inkFaint),
          ),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.border),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: trace.length,
        separatorBuilder: (context, index) =>
            Divider(height: 1, color: colors.border),
        itemBuilder: (context, idx) {
          final event = trace[idx];
          final isEdge = event.decision == 'EDGE_REPLY';
          return Padding(
            padding: const EdgeInsets.all(UriSpace.sm),
            child: Row(
              children: [
                StatusPill(
                  label: event.decision,
                  foreground: isEdge ? Colors.green : Colors.amber,
                  background: (isEdge ? Colors.green : Colors.amber).withValues(
                    alpha: 0.15,
                  ),
                ),
                const SizedBox(width: UriSpace.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Layer: ${event.intelligenceLayer} · ${event.candidate ?? 'Needle 3'}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (event.reasonCodes.isNotEmpty)
                        Text(
                          event.reasonCodes.join(', '),
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: colors.inkFaint,
                          ),
                        ),
                    ],
                  ),
                ),
                if (event.latencyMs != null)
                  Text(
                    '${event.latencyMs} ms',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: colors.inkFaint,
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

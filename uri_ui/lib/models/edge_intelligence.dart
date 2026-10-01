/// Data models for URI Edge Intelligence, candidate qualification status,
/// and truthful runtime evidence.
class EdgeSettings {
  const EdgeSettings({
    required this.enabled,
    required this.intelligenceMode,
    required this.replyConfidenceThresholdPercent,
    this.runtimeId,
    this.modelId,
    this.revision = 0,
  });

  final bool enabled;
  final String intelligenceMode;
  final int replyConfidenceThresholdPercent;
  final String? runtimeId;
  final String? modelId;
  final int revision;

  factory EdgeSettings.fromJson(Map<String, dynamic> json) {
    final edge = json['edge'] as Map<String, dynamic>? ?? const {};
    return EdgeSettings(
      enabled: json['enabled'] as bool? ?? true,
      intelligenceMode: json['intelligence_mode'] as String? ?? 'HYBRID',
      replyConfidenceThresholdPercent:
          json['reply_confidence_threshold_percent'] as int? ?? 90,
      runtimeId: edge['runtime_id'] as String?,
      modelId: edge['model_id'] as String?,
      revision: json['revision'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
    'enabled': enabled,
    'intelligence_mode': intelligenceMode,
    'reply_confidence_threshold_percent': replyConfidenceThresholdPercent,
    'revision': revision,
    if (runtimeId != null || modelId != null)
      'edge': {'runtime_id': runtimeId, 'model_id': modelId},
  };

  EdgeSettings copyWith({
    bool? enabled,
    String? intelligenceMode,
    int? replyConfidenceThresholdPercent,
    String? runtimeId,
    String? modelId,
    int? revision,
  }) {
    return EdgeSettings(
      enabled: enabled ?? this.enabled,
      intelligenceMode: intelligenceMode ?? this.intelligenceMode,
      replyConfidenceThresholdPercent:
          replyConfidenceThresholdPercent ??
          this.replyConfidenceThresholdPercent,
      runtimeId: runtimeId ?? this.runtimeId,
      modelId: modelId ?? this.modelId,
      revision: revision ?? this.revision,
    );
  }
}

class EdgeEffectiveStatus {
  const EdgeEffectiveStatus({
    required this.status,
    required this.enabled,
    required this.deploymentEnabled,
    required this.effectiveEdgeEnabled,
    this.runtimeId,
    this.modelId,
  });

  final String status;
  final bool enabled;
  final bool deploymentEnabled;
  final bool effectiveEdgeEnabled;
  final String? runtimeId;
  final String? modelId;

  factory EdgeEffectiveStatus.fromJson(Map<String, dynamic> json) {
    return EdgeEffectiveStatus(
      status: json['status'] as String? ?? 'unknown',
      enabled: json['enabled'] as bool? ?? false,
      deploymentEnabled: json['deployment_enabled'] as bool? ?? false,
      effectiveEdgeEnabled: json['effective_edge_enabled'] as bool? ?? false,
      runtimeId: json['runtime_id'] as String?,
      modelId: json['model_id'] as String?,
    );
  }
}

class EdgeCandidateInfo {
  const EdgeCandidateInfo({
    required this.id,
    required this.name,
    required this.role,
    required this.status,
    required this.qualified,
    required this.argumentTrusted,
    required this.detail,
    this.reflexAccuracyPct,
    this.structuredExtractionPct,
    this.argumentAccuracyPct,
    this.p50LatencyMs,
    this.ramMb,
  });

  final String id;
  final String name;
  final String role;
  final String status; // RESIDENT, BYPASSED, UNAVAILABLE
  final bool qualified;
  final bool argumentTrusted;
  final String detail;
  final int? reflexAccuracyPct;
  final int? structuredExtractionPct;
  final int? argumentAccuracyPct;
  final int? p50LatencyMs;
  final int? ramMb;

  factory EdgeCandidateInfo.fromJson(Map<String, dynamic> json) {
    return EdgeCandidateInfo(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      role: json['role'] as String? ?? '',
      status: json['status'] as String? ?? 'UNAVAILABLE',
      qualified: json['qualified'] as bool? ?? false,
      argumentTrusted: json['argument_trusted'] as bool? ?? false,
      detail: json['detail'] as String? ?? '',
      reflexAccuracyPct: json['reflex_accuracy_pct'] as int?,
      structuredExtractionPct: json['structured_extraction_pct'] as int?,
      argumentAccuracyPct: json['argument_accuracy_pct'] as int?,
      p50LatencyMs: json['p50_latency_ms'] as int?,
      ramMb: json['ram_mb'] as int?,
    );
  }
}

class EdgeLabOverview {
  const EdgeLabOverview({
    required this.status,
    required this.runtimeLifecycle,
    required this.candidates,
    required this.routingPolicy,
  });

  final String status;
  final Map<String, dynamic> runtimeLifecycle;
  final List<EdgeCandidateInfo> candidates;
  final Map<String, dynamic> routingPolicy;

  factory EdgeLabOverview.fromJson(Map<String, dynamic> json) {
    final candList = json['candidates'] as List<dynamic>? ?? const [];
    return EdgeLabOverview(
      status: json['status'] as String? ?? 'unknown',
      runtimeLifecycle:
          json['runtime_lifecycle'] as Map<String, dynamic>? ?? const {},
      candidates: candList
          .map((c) => EdgeCandidateInfo.fromJson(c as Map<String, dynamic>))
          .toList(),
      routingPolicy:
          json['routing_policy'] as Map<String, dynamic>? ?? const {},
    );
  }
}

class ExperimentalCandidate {
  const ExperimentalCandidate({
    required this.modelId,
    required this.runtime,
    required this.loadedState,
    required this.qualificationState,
    required this.testedCapabilities,
    required this.productionPromoted,
    this.quantization,
    this.fileSizeBytes,
    this.ramMib,
    this.vramMib,
    this.benchmarkEvidence,
  });

  final String modelId;
  final String runtime;
  final String loadedState;
  final String qualificationState;
  final List<String> testedCapabilities;
  final bool productionPromoted;
  final String? quantization;
  final int? fileSizeBytes;
  final num? ramMib;
  final num? vramMib;
  final Map<String, dynamic>? benchmarkEvidence;

  factory ExperimentalCandidate.fromJson(Map<String, dynamic> json) =>
      ExperimentalCandidate(
        modelId: json['model_id'] as String? ?? '',
        runtime: json['runtime'] as String? ?? '',
        loadedState: json['loaded_state'] as String? ?? 'unknown',
        qualificationState:
            json['qualification_state'] as String? ?? 'NOT_TESTED',
        testedCapabilities: (json['tested_capabilities'] as List? ?? const [])
            .map((value) => value.toString())
            .toList(growable: false),
        productionPromoted: json['production_promoted'] as bool? ?? false,
        quantization: json['quantization'] as String?,
        fileSizeBytes: json['file_size_bytes'] as int?,
        ramMib: json['ram_mib'] as num?,
        vramMib: json['vram_mib'] as num?,
        benchmarkEvidence: json['benchmark_evidence'] as Map<String, dynamic>?,
      );

  ExperimentalCandidate withQualification(Map<String, dynamic> json) =>
      ExperimentalCandidate(
        modelId: modelId,
        runtime: runtime,
        loadedState: loadedState,
        qualificationState:
            json['qualification_state'] as String? ?? qualificationState,
        testedCapabilities: (json['tested_capabilities'] as List? ?? const [])
            .map((value) => value.toString())
            .toList(growable: false),
        productionPromoted: false,
        quantization: quantization,
        fileSizeBytes: fileSizeBytes,
        ramMib: ramMib,
        vramMib: vramMib,
        benchmarkEvidence: json['benchmark_evidence'] as Map<String, dynamic>?,
      );
}

class EdgeProbeResult {
  const EdgeProbeResult({
    required this.timestamp,
    required this.decision,
    required this.intelligenceLayer,
    required this.reasonCodes,
    required this.confidence,
    required this.latencyMs,
    required this.candidate,
    required this.thresholdPercent,
    this.querySample,
    this.details,
    this.advisoryNote,
  });

  final String timestamp;
  final String decision; // EDGE_REPLY, ESCALATE, SUPPRESS
  final String intelligenceLayer;
  final List<String> reasonCodes;
  final double confidence;
  final int latencyMs;
  final String candidate;
  final int thresholdPercent;
  final String? querySample;
  final Map<String, dynamic>? details;
  final String? advisoryNote;

  factory EdgeProbeResult.fromJson(Map<String, dynamic> json) {
    final list = json['reason_codes'] as List<dynamic>? ?? const [];
    return EdgeProbeResult(
      timestamp: json['timestamp'] as String? ?? '',
      decision: json['decision'] as String? ?? '',
      intelligenceLayer: json['intelligence_layer'] as String? ?? '',
      reasonCodes: list.map((e) => e.toString()).toList(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      latencyMs: json['latency_ms'] as int? ?? 0,
      candidate: json['candidate'] as String? ?? '',
      thresholdPercent: json['threshold_percent'] as int? ?? 90,
      querySample: json['query_sample'] as String?,
      details: json['details'] as Map<String, dynamic>?,
      advisoryNote: json['advisory_note'] as String?,
    );
  }
}

class EdgeRoutingEvent {
  const EdgeRoutingEvent({
    required this.timestamp,
    required this.decision,
    required this.intelligenceLayer,
    this.reasonCodes = const [],
    this.sessionId,
    this.outcome,
    this.latencyMs,
    this.candidate,
    this.confidenceScore,
    this.mainBrain,
    this.rawJson,
  });

  final String timestamp;
  final String decision;
  final String intelligenceLayer;
  final List<String> reasonCodes;
  final String? sessionId;
  final String? outcome;
  final int? latencyMs;
  final String? candidate;
  final double? confidenceScore;
  final Map<String, dynamic>? mainBrain;
  final Map<String, dynamic>? rawJson;

  factory EdgeRoutingEvent.fromJson(Map<String, dynamic> json) {
    final reasons = json['reason_codes'] as List<dynamic>? ?? const [];
    final latency = json['latency_ms'] as Map<String, dynamic>?;
    final edge = json['edge'] as Map<String, dynamic>?;
    final conf = json['confidence'] as Map<String, dynamic>?;
    return EdgeRoutingEvent(
      timestamp: json['timestamp'] as String? ?? '',
      decision: json['decision'] as String? ?? '',
      intelligenceLayer: json['intelligence_layer'] as String? ?? '',
      reasonCodes: reasons.map((e) => e.toString()).toList(),
      sessionId: json['session_id'] as String?,
      outcome: json['outcome'] as String?,
      latencyMs: latency?['total'] as int? ?? latency?['reflex'] as int?,
      candidate: edge?['model_id'] as String? ?? edge?['runtime_id'] as String?,
      confidenceScore: (conf?['score'] as num?)?.toDouble(),
      mainBrain: json['main_brain'] as Map<String, dynamic>?,
      rawJson: json,
    );
  }
}

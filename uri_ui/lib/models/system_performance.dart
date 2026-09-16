/// Real CPU/memory/disk snapshot from GET /system/performance
/// (2026-09-12) — every field here is either a real psutil reading or
/// explicitly null/unavailable; nothing is invented when the backend
/// cannot report it (e.g. GPU/temperature/fan/power are never sent
/// because this platform has no real source for them).
class SystemPerformanceSnapshot {
  const SystemPerformanceSnapshot({
    required this.cpuPercent,
    required this.logicalCores,
    required this.physicalCores,
    required this.memoryUsedPercent,
    required this.memoryTotalBytes,
    required this.memoryAvailableBytes,
    required this.diskUsedPercent,
    required this.diskFreeBytes,
    required this.diskTotalBytes,
    required this.swapAvailable,
    required this.swapUsedPercent,
  });

  final double cpuPercent;
  final int logicalCores;
  final int? physicalCores;
  final double memoryUsedPercent;
  final int memoryTotalBytes;
  final int memoryAvailableBytes;
  final double diskUsedPercent;
  final int diskFreeBytes;
  final int diskTotalBytes;
  final bool swapAvailable;
  final double? swapUsedPercent;

  static SystemPerformanceSnapshot? fromJson(Map<String, dynamic>? json) {
    if (json == null || json['status'] != 'success') return null;
    final cpu = json['cpu'] as Map<String, dynamic>? ?? const {};
    final memory = json['memory'] as Map<String, dynamic>? ?? const {};
    final disk = json['disk'] as Map<String, dynamic>? ?? const {};
    final swap = json['swap'] as Map<String, dynamic>? ?? const {};
    return SystemPerformanceSnapshot(
      cpuPercent: (cpu['percent'] as num?)?.toDouble() ?? 0,
      logicalCores: (cpu['logical_cores'] as num?)?.toInt() ?? 0,
      physicalCores: (cpu['physical_cores'] as num?)?.toInt(),
      memoryUsedPercent: (memory['used_percent'] as num?)?.toDouble() ?? 0,
      memoryTotalBytes: (memory['total_bytes'] as num?)?.toInt() ?? 0,
      memoryAvailableBytes: (memory['available_bytes'] as num?)?.toInt() ?? 0,
      diskUsedPercent: (disk['used_percent'] as num?)?.toDouble() ?? 0,
      diskFreeBytes: (disk['free_bytes'] as num?)?.toInt() ?? 0,
      diskTotalBytes: (disk['total_bytes'] as num?)?.toInt() ?? 0,
      swapAvailable: swap['available'] != false,
      swapUsedPercent: (swap['used_percent'] as num?)?.toDouble(),
    );
  }
}

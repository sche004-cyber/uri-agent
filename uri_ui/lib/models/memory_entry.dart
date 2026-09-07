/// One fact URI holds about the user, mirroring the backend's bounded
/// view exactly (see server.py's _memory_entry_to_dict) — never the
/// full internal Fact/MemoryEntry shape (source, evidence ids,
/// verification metadata are deliberately not exposed to the client).
class MemoryEntry {
  const MemoryEntry({
    required this.memoryId,
    required this.category,
    required this.consent,
    required this.content,
    required this.confidence,
    required this.notes,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String memoryId;
  final String category;

  /// How this entry came to exist — always "user_provided" today (see
  /// server.py's add_memory docstring: nothing in this milestone lets
  /// the model write memory on its own).
  final String consent;
  final String content;
  final double? confidence;
  final String? notes;
  final String status;
  final String createdAt;
  final String updatedAt;
}

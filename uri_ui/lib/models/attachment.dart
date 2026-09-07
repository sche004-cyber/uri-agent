/// A file the user attached to the conversation. Mirrors the backend's
/// bounded reference exactly (see StoredFile.to_reference) — metadata
/// only, never content, and never a storage path.
///
/// Lives in `models/` (rather than alongside [UriClient]) so both the
/// client layer and [UriTurn] — which records which attachments were
/// staged when a given turn was sent — can depend on it without a
/// circular import between `uri_client.dart` and `uri_turn.dart`.
class Attachment {
  const Attachment({
    required this.fileId,
    required this.filename,
    required this.mediaType,
    required this.sizeBytes,
  });

  final String fileId;
  final String filename;
  final String mediaType;
  final int sizeBytes;
}

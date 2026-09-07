/// A plugin-free abstraction over "let the user open/verify a file
/// they attached", the same DI split file_picker_service.dart already
/// uses for choosing a file: the real `package:open_filex`
/// implementation lives alone in platform_attachment_opener.dart, and
/// only main.dart wires it in. Keeping the plugin out of the screens
/// means the UI stays testable — importing a platform plugin anywhere
/// in the widget tree hangs every widget test that builds it.
library;

/// Outcome of trying to open a downloaded attachment with whatever the
/// device would normally use for that file type.
enum AttachmentOpenOutcome {
  /// A viewer app opened (or was launched to open) the file.
  opened,

  /// The file opened fine but the device has no app registered for
  /// its type — a real, common outcome (e.g. an unusual document
  /// type), not an error to alarm the user with.
  noViewerAvailable,

  /// Writing the file locally or invoking the platform opener failed.
  failed,
}

/// Saves [bytes] as [filename] somewhere the platform can read it back
/// from, then asks the OS to open it with whatever app the user has
/// for that type — the same "tap to open" verification WhatsApp offers
/// for a chat attachment.
typedef AttachmentOpenerFn =
    Future<AttachmentOpenOutcome> Function({
      required String filename,
      required List<int> bytes,
    });

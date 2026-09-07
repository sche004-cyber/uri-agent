/// The ONLY file in this app that imports `package:open_filex`.
///
/// Isolated deliberately — see attachment_opener_service.dart for why:
/// pulling the plugin into the widget tree hangs every widget test
/// that builds it. Nothing here is imported by any screen; only
/// main.dart wires this into [AskUriScreen].
library;

import 'dart:io';

import 'package:open_filex/open_filex.dart';

import 'attachment_opener_service.dart';

/// Writes [bytes] to a fresh temp file named [filename] and asks the
/// OS to open it. A fresh subdirectory per call (rather than reusing
/// one file path) avoids ever serving a stale/mismatched body if the
/// same filename is opened twice with different content.
Future<AttachmentOpenOutcome> openPlatformAttachment({
  required String filename,
  required List<int> bytes,
}) async {
  final File file;
  try {
    final dir = await Directory.systemTemp.createTemp('uri_attachment_');
    file = File('${dir.path}/$filename');
    await file.writeAsBytes(bytes, flush: true);
  } catch (_) {
    return AttachmentOpenOutcome.failed;
  }

  final result = await OpenFilex.open(file.path);
  switch (result.type) {
    case ResultType.done:
      return AttachmentOpenOutcome.opened;
    case ResultType.noAppToOpen:
      return AttachmentOpenOutcome.noViewerAvailable;
    case ResultType.fileNotFound:
    case ResultType.permissionDenied:
    case ResultType.error:
      return AttachmentOpenOutcome.failed;
  }
}

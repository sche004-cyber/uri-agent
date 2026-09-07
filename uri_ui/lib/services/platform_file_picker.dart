/// M16: the ONLY file in this app that imports `package:file_picker`.
///
/// Isolated deliberately — see file_picker_service.dart for why:
/// pulling the plugin into the widget tree hangs every widget test
/// that builds it. Nothing here is imported by any screen; only
/// main.dart wires this into [AskUriScreen].
library;

import 'package:file_picker/file_picker.dart';

import 'file_picker_service.dart';

/// Opens the real platform file dialog. Returns null when the user
/// cancels.
///
/// Deliberately applies no extension filter: the backend's allow-list
/// is the single source of truth for what is acceptable (see
/// file_store.py), so the user gets one consistent, real reason for a
/// rejection rather than a client-side rule that could drift out of
/// step with it.
Future<PickedFile?> pickPlatformFile() async {
  final file = await FilePicker.pickFile();
  if (file == null) return null;

  final bytes = await file.readAsBytes();
  return PickedFile(name: file.name, bytes: bytes);
}

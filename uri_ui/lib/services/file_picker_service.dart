/// M16: a plugin-free abstraction over "let the user choose a file".
///
/// This file deliberately imports NOTHING platform-specific. The real
/// `package:file_picker` implementation lives alone in
/// platform_file_picker.dart, and only the app entry point (main.dart)
/// wires it in.
///
/// That split exists for a concrete reason: importing the file_picker
/// plugin anywhere in the widget tree makes every widget test that
/// builds that tree hang on plugin resolution under `flutter test`.
/// Keeping the plugin out of the screens means the UI stays testable,
/// and the picker stays swappable (a fake in tests, the real dialog in
/// the app) — the same dependency-injection discipline UriClient and
/// the backend's own stores already follow.
library;

/// A file the user chose, already read into memory. Deliberately not
/// tied to any picker package's own type.
class PickedFile {
  const PickedFile({required this.name, required this.bytes});

  final String name;
  final List<int> bytes;
}

/// Opens the platform picker and returns the chosen file, or null when
/// the user cancelled.
typedef FilePickerFn = Future<PickedFile?> Function();

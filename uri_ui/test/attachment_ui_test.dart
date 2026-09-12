// M16 Priority 1 (client half): the attach control must only appear
// when a picker is actually available, attached files must be shown as
// real chips, and a backend rejection must surface its real reason -
// never a silent failure or a fabricated success.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uri_ui/screens/ask/ask_uri_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/file_picker_service.dart';
import 'package:uri_ui/services/mock_uri_client.dart';
import 'package:uri_ui/services/uri_client.dart';

class _RejectingClient extends MockUriClient {
  @override
  Future<Attachment> uploadAttachment({
    required String filename,
    required List<int> bytes,
  }) async {
    throw const AttachmentException("Files of type '.exe' are not accepted.");
  }
}

Future<void> _pump(
  WidgetTester tester,
  AppState state, {
  FilePickerFn? picker,
}) async {
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    AppStateScope(
      state: state,
      child: MaterialApp(
        home: Scaffold(body: AskUriScreen(filePicker: picker)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('no attach control is shown when no picker is available', (
    tester,
  ) async {
    await _pump(tester, AppState(MockUriClient()));

    // The UI must not offer an affordance it cannot fulfil.
    expect(find.byIcon(Icons.attach_file_rounded), findsNothing);
  });

  testWidgets('the attach control appears when a picker is available', (
    tester,
  ) async {
    await _pump(tester, AppState(MockUriClient()), picker: () async => null);

    expect(find.byIcon(Icons.attach_file_rounded), findsOneWidget);
  });

  testWidgets('a picked file is uploaded and shown as an attachment chip', (
    tester,
  ) async {
    await _pump(
      tester,
      AppState(MockUriClient()),
      picker: () async =>
          const PickedFile(name: 'minutes.pdf', bytes: [1, 2, 3, 4]),
    );

    await tester.tap(find.byIcon(Icons.attach_file_rounded));
    await tester.pumpAndSettle();

    expect(find.textContaining('minutes.pdf'), findsOneWidget);
  });

  testWidgets('a cancelled pick attaches nothing', (tester) async {
    await _pump(tester, AppState(MockUriClient()), picker: () async => null);

    await tester.tap(find.byIcon(Icons.attach_file_rounded));
    await tester.pumpAndSettle();

    expect(find.byType(Chip), findsNothing);
  });

  testWidgets('a rejected upload shows the real backend reason', (
    tester,
  ) async {
    await _pump(
      tester,
      AppState(_RejectingClient()),
      picker: () async => const PickedFile(name: 'payload.exe', bytes: [1, 2]),
    );

    await tester.tap(find.byIcon(Icons.attach_file_rounded));
    await tester.pumpAndSettle();

    expect(find.textContaining('not accepted'), findsOneWidget);
    // Nothing was attached, and no success was implied.
    expect(find.byType(Chip), findsNothing);
  });

  testWidgets('an attachment can be removed', (tester) async {
    final state = AppState(MockUriClient());
    await _pump(
      tester,
      state,
      picker: () async =>
          const PickedFile(name: 'minutes.pdf', bytes: [1, 2, 3]),
    );

    await tester.tap(find.byIcon(Icons.attach_file_rounded));
    await tester.pumpAndSettle();
    expect(find.byType(Chip), findsOneWidget);

    await tester.tap(find.byIcon(Icons.cancel));
    await tester.pumpAndSettle();

    expect(find.byType(Chip), findsNothing);
  });
}

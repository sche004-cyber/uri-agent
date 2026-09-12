import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uri_ui/screens/settings/providers_screen.dart';
import 'package:uri_ui/screens/settings/settings_shell.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  testWidgets('ProvidersScreen has visible height inside wide SettingsShell', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(AppStateScope(
      state: AppState(MockUriClient()),
      child: const MaterialApp(home: SettingsShell()),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Model Providers').first);
    await tester.pumpAndSettle();
    final box = tester.renderObject<RenderBox>(find.byType(ProvidersScreen));
    expect(box.size.height, greaterThan(0));
    expect(find.text('Ollama (Local)'), findsOneWidget);
  });
}

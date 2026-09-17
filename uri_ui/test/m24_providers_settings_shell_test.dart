import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uri_ui/screens/connections/connections_providers_screen.dart';
import 'package:uri_ui/screens/settings/providers_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

// Hybrid Blueprint §4.6/§6 Batch 3: Providers moved out of SettingsShell
// into the combined Connections & Providers screen, visible directly on
// a wide layout (no category tap needed — both sections render at
// once). Retargeted from the old "Model Providers" settings category,
// which this batch removes.
void main() {
  testWidgets('ProvidersScreen has visible height inside wide ConnectionsProvidersScreen', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(AppStateScope(
      state: AppState(MockUriClient()),
      child: const MaterialApp(home: ConnectionsProvidersScreen()),
    ));
    await tester.pumpAndSettle();
    final box = tester.renderObject<RenderBox>(find.byType(ProvidersScreen));
    expect(box.size.height, greaterThan(0));
    expect(find.text('Ollama (Local)'), findsOneWidget);
  });
}

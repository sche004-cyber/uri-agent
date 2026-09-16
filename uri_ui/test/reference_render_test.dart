import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/app.dart';
import 'package:uri_ui/models/user_preferences.dart';

import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<void> pumpDashboard(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1024, 682);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final state = AppState(MockUriClient());
    await state.updatePreferences(
      const UserPreferences.initial().copyWith(completedOnboarding: true),
    );
    final loader = FontLoader('Segoe UI')..addFont(Future.value(ByteData.sublistView(File('C:/Windows/Fonts/segoeui.ttf').readAsBytesSync())));
    await loader.load();
    for (final family in ['Roboto', 'Arial', 'sans-serif']) {
      final font = FontLoader(family)..addFont(Future.value(ByteData.sublistView(File('C:/Windows/Fonts/segoeui.ttf').readAsBytesSync())));
      await font.load();
    }
    final fallback = FontLoader('Ahem')..addFont(Future.value(ByteData.sublistView(File('C:/Windows/Fonts/segoeui.ttf').readAsBytesSync())));
    await fallback.load();
    await tester.pumpWidget(RepaintBoundary(key: const ValueKey('capture'), child: UriApp(appState: state, filePicker: () async => null)));
    await tester.runAsync(() async {
      final context = tester.element(find.byType(UriApp));
      await precacheImage(const AssetImage('assets/misty_forest_sikkim.jpg'), context);
      await precacheImage(const AssetImage('assets/uri_app_logo_refined_v2.png'), context);
      final icons = FontLoader('MaterialIcons')..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
      await icons.load();
    });
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
  }

  testWidgets('render desktop dashboard', (tester) async {
    await pumpDashboard(tester);
    await tester.runAsync(() async {
      final boundary = tester.renderObject<RenderRepaintBoundary>(find.byKey(const ValueKey('capture')));
      final image = await boundary.toImage();
      final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
      File('../.tmp_m26_render/rebuilt_dashboard.png').writeAsBytesSync(bytes!.buffer.asUint8List());
    });
    expect(tester.takeException(), isNull);
  });
}

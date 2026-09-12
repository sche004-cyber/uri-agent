import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:uri_ui/screens/settings/providers_screen.dart';
import 'package:uri_ui/services/app_state.dart';
import 'package:uri_ui/services/app_state_scope.dart';
import 'package:uri_ui/services/mock_uri_client.dart';

void main() {
  testWidgets('basic provider view never renders token or context window', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1280, 900);
    addTearDown(tester.view.resetPhysicalSize);
    await tester.pumpWidget(
      AppStateScope(
        state: AppState(MockUriClient()),
        child: const MaterialApp(home: ProvidersScreen()),
      ),
    );
    await tester.pumpAndSettle();
    final text = tester
        .widgetList<Text>(find.byType(Text))
        .map((item) => item.data ?? item.textSpan?.toPlainText() ?? '')
        .join(' ')
        .toLowerCase();
    expect(text, isNot(contains('token')));
    expect(text, isNot(contains('context window')));
  });
}

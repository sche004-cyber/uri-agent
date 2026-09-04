import 'package:flutter/widgets.dart';

import 'app_state.dart';

/// Makes a single [AppState] available to the whole widget tree without
/// pulling in an external state-management package — this prototype's
/// state needs are simple enough that Flutter's own [InheritedNotifier]
/// is sufficient.
class AppStateScope extends InheritedNotifier<AppState> {
  const AppStateScope({super.key, required AppState state, required super.child})
    : super(notifier: state);

  static AppState of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppStateScope>();
    assert(scope != null, 'No AppStateScope found in context');
    return scope!.notifier!;
  }
}

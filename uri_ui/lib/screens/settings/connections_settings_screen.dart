import 'package:flutter/material.dart';

import '../connections/connections_screen.dart';

/// Real in-place connection management, embedded directly in Settings -
/// not a second copy of the Connections screen's logic (that would be
/// exactly the kind of duplicate surface this redesign is meant to
/// remove) and not a redirect trampoline either: [ConnectionsScreen]
/// itself is just a scrollable panel with no Scaffold of its own, so it
/// embeds here unmodified as the single real implementation, reused
/// verbatim from the one place connections are actually managed.
class ConnectionsSettingsScreen extends StatelessWidget {
  const ConnectionsSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) => const ConnectionsScreen();
}

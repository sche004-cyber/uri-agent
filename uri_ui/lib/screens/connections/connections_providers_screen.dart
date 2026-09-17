import 'package:flutter/material.dart';

import '../../theme/uri_theme.dart';
import '../settings/providers_screen.dart';
import 'connections_screen.dart';

/// Hybrid UI Frozen Blueprint §4.6: the combined "Connections &
/// Providers" destination — two sections, Connections (real Google
/// OAuth status, [ConnectionsScreen]) and Providers (real discovered
/// provider inventory, [ProvidersScreen], absorbing M31's Connect
/// Provider work per §7). Side by side on a wide layout; stacked on a
/// narrow one.
///
/// [ProvidersScreen] is embedded verbatim, not flattened into
/// `.list-row`s: its configuration/verification/fallback-routing
/// dialogs are exactly the M31 contract §6 Batch 3 requires preserved,
/// and collapsing that into a static status-pill list would regress
/// real functionality the blueprint explicitly protects — the
/// structural "restyle" §7 asks for is this screen's two-section
/// layout, not a rebuild of Providers' internals. Disclosed in the
/// Batch 3 report as a deliberate reconciliation, same footing as
/// Batch 2's model-selector/empty-state reconciliations.
///
/// Both [ConnectionsScreen] and [ProvidersScreen] render their content
/// directly (no scroll wrapper of their own) so this screen's single
/// [SingleChildScrollView] owns the page-level scroll for both
/// sections, rather than nesting independent scroll regions.
class ConnectionsProvidersScreen extends StatelessWidget {
  const ConnectionsProvidersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= UriBreakpoints.wide;
        if (wide) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(UriSpace.xl),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Expanded(child: ConnectionsScreen()),
                SizedBox(width: UriSpace.xl),
                Expanded(child: ProvidersScreen()),
              ],
            ),
          );
        }
        return const SingleChildScrollView(
          padding: EdgeInsets.all(UriSpace.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ConnectionsScreen(),
              SizedBox(height: UriSpace.xl),
              ProvidersScreen(),
            ],
          ),
        );
      },
    );
  }
}

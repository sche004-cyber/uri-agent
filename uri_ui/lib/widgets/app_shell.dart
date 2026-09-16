import 'package:flutter/material.dart';

import '../theme/dashboard_manifest.dart';
import '../theme/uri_theme.dart';
import '../services/app_state_scope.dart';
import 'uri_wordmark.dart';

class UriSection {
  const UriSection({
    required this.label,
    required this.icon,
    required this.builder,
    this.group,
  });

  final String label;
  final IconData icon;
  final WidgetBuilder builder;

  /// Sidebar group heading (2026-09-12 accepted dashboard shell —
  /// docs/plans/M26_DASHBOARD_DESIGN_SPECIFICATION.md §4). Null keeps a
  /// section in a flat, ungrouped list, which is what every existing
  /// test/screen not yet updated for grouping still gets.
  final String? group;
}

/// Section indices in [AppShell] — kept in one place so any screen can
/// jump to another tab (e.g. a blocked Ask URI turn pointing at
/// Connections) without depending on the sections list. There is no
/// "ask" index: Home itself holds the one canonical conversation, so
/// nothing ever needs to navigate to a separate Ask URI destination.
class ShellIndex {
  ShellIndex._();
  static const home = 0;
  static const tasks = 1;
  static const connections = 2;
  static const activity = 3;
  // M19: promoted to a top-level destination (was previously nested
  // inside Settings, per user request to see conversation history
  // directly rather than three taps deep) - not duplicated in
  // Settings' own category list.
  static const history = 4;
  static const settings = 5;
}

/// The persistent application shell: a sidebar on wide (desktop-first)
/// layouts, collapsing to a bottom navigation bar on narrow/mobile
/// widths. Screens are swapped in place — this is what makes
/// Home -> Tasks -> Connections navigable within one running app.
class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.sections, this.initialIndex = 0});

  final List<UriSection> sections;
  final int initialIndex;

  @override
  State<AppShell> createState() => AppShellState();
}

class AppShellState extends State<AppShell> {
  late int _index = widget.initialIndex;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) AppStateScope.of(context).loadActiveBrain();
    });
  }

  void goTo(int index, {String? settingsCategory}) {
    if (settingsCategory != null) {
      AppStateScope.of(context).openSettingsCategory(settingsCategory);
    }
    setState(() => _index = index);
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final isWide = UriBreakpoints.isWide(context);

    final content = KeyedSubtree(
      key: ValueKey(_index),
      child: widget.sections[_index].builder(context),
    );

    if (isWide) {
      return Scaffold(
        backgroundColor: colors.canvas,
        body: LayoutBuilder(
          builder: (context, constraints) {
            final scale = DashboardScale.scaleFor(constraints.biggest);
            return DashboardScale(
              scale: scale,
              child: Row(
                children: [
                  _Sidebar(
                    sections: widget.sections,
                    index: _index,
                    onSelect: goTo,
                    onBrainTap: () => goTo(
                      ShellIndex.settings,
                      settingsCategory: 'Model Providers',
                    ),
                  ),
                  Expanded(child: SafeArea(child: content)),
                ],
              ),
            );
          },
        ),
      );
    }

    return Scaffold(
      backgroundColor: colors.canvas,
      appBar: AppBar(
        backgroundColor: colors.canvas,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [_Wordmark()],
        ),
        actions: [
          SizedBox(
            width: MediaQuery.sizeOf(context).width < 500 ? 170 : 280,
            child: _BrainStatusPill(
              onTap: () => goTo(
                ShellIndex.settings,
                settingsCategory: 'Model Providers',
              ),
            ),
          ),
          const SizedBox(width: UriSpace.sm),
        ],
      ),
      body: SafeArea(child: content),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: goTo,
        backgroundColor: colors.surface,
        destinations: [
          for (final section in widget.sections)
            NavigationDestination(
              icon: Icon(section.icon),
              label: section.label,
            ),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.sections,
    required this.index,
    required this.onSelect,
    required this.onBrainTap,
  });
  final List<UriSection> sections;
  final int index;
  final ValueChanged<int> onSelect;
  final VoidCallback onBrainTap;
  @override
  Widget build(BuildContext context) {
    // This is the left region of the same frozen desktop board rendered by
    // HomeScreen. Reads the one shared scale AppShell computed for the
    // whole board (see DashboardScale) so this rail always agrees with
    // HomeScreen's own center/right columns - a fraction of the raw
    // window width would drift from the board's actual scale at any
    // window aspect ratio other than the board's native one.
    final width = DashboardManifest.leftRailWidth * DashboardScale.of(context);
    void navigate(int target, {String? category}) {
      if (category != null) {
        AppStateScope.of(context).openSettingsCategory(category);
      }
      onSelect(target);
    }

    final items = DashboardManifest.navItems.map((label) {
      final detail = switch (label) {
        'Home' => (Icons.auto_awesome_outlined, ShellIndex.home, null),
        'Chat' => (Icons.chat_bubble_outline, ShellIndex.home, null),
        // Email/Drive retain the Connections route; Files retains History;
        // Insights retains Activity.  These are the surviving entry points
        // for the duplicate labels removed from the visual nav.
        'Email' => (Icons.mail_outline, ShellIndex.connections, null),
        'Drive' => (Icons.link, ShellIndex.connections, null),
        'Files' => (Icons.description_outlined, ShellIndex.history, null),
        'Tasks' => (Icons.check, ShellIndex.tasks, null),
        'Calendar' => (
          Icons.calendar_month_outlined,
          ShellIndex.connections,
          null,
        ),
        'Graph' => (
          Icons.hub_outlined,
          ShellIndex.settings,
          'Memory & Context',
        ),
        'Memory' => (Icons.memory, ShellIndex.settings, 'Memory'),
        'Insights' => (Icons.insights, ShellIndex.activity, null),
        'Model' => (
          Icons.memory_outlined,
          ShellIndex.settings,
          'Model Providers',
        ),
        'Tools & Skills' => (
          Icons.extension_outlined,
          ShellIndex.settings,
          'Capabilities',
        ),
        'Settings' => (Icons.settings_outlined, ShellIndex.settings, null),
        _ => throw StateError('Unknown dashboard navigation item: $label'),
      };
      return (label, detail.$1, detail.$2, detail.$3);
    }).toList();
    final colors = UriColors.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: width,
      // The near-black gradient is the approved dark theme's own
      // branded treatment (M26 dashboard spec) - kept verbatim for
      // dark mode. Light mode reads the active theme's own surface/
      // border tokens instead of staying on this hardcoded dark
      // gradient regardless of the selected Appearance (User-reported:
      // Appearance must visibly change the left navigation/shell).
      decoration: BoxDecoration(
        gradient: isDark
            ? const LinearGradient(
                colors: [Color(0xff020910), Color(0xff04121c)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        color: isDark ? null : colors.surface,
        border: Border(
          right: BorderSide(
            color: isDark ? const Color(0xff15334a) : colors.border,
          ),
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            SizedBox(
              height: MediaQuery.sizeOf(context).height < 760 ? 125 : 180,
              child: Column(
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Image.asset(
                        'assets/uri_app_logo_refined_v2.png',
                        color: const Color(0xff020910),
                        colorBlendMode: BlendMode.screen,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 0, 8, 12),
                    child: Text(
                      'INTELLIGENCE FOR A BETTER TOMORROW',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: colors.inkFaint,
                        fontSize: 7,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  for (final item in items)
                    _SidebarItem(
                      section: UriSection(
                        label: item.$1,
                        icon: item.$2,
                        builder: (_) => const SizedBox(),
                      ),
                      selected:
                          (index == 0 && item.$1 == 'Home') ||
                          (index == 1 && item.$1 == 'Tasks') ||
                          (index == 5 && item.$1 == 'Settings'),
                      onTap: () => navigate(item.$3, category: item.$4),
                    ),
                ],
              ),
            ),
            const Padding(padding: EdgeInsets.all(12), child: _SidebarFooter()),
          ],
        ),
      ),
    );
  }
}

/// Thin wrapper kept only so the many `_Wordmark()` call sites in this
/// file don't all need renaming - the actual mark is the single
/// canonical [UriWordmark] (see widgets/uri_wordmark.dart), previously
/// duplicated here as its own copy.
class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) => UriWordmark(markSize: 30);
}

class _SidebarItem extends StatelessWidget {
  const _SidebarItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final UriSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.sm),
          onTap: onTap,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(7),
              gradient: selected
                  ? const LinearGradient(
                      colors: [Color(0xff0875d7), Color(0xff06419d)],
                    )
                  : null,
              border: selected
                  ? Border.all(color: const Color(0xff178fe9))
                  : null,
              boxShadow: selected
                  ? const [BoxShadow(color: Color(0x550f85ff), blurRadius: 12)]
                  : null,
            ),
            child: Row(
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  width: 3,
                  height: 18,
                  margin: const EdgeInsets.only(left: 2),
                  decoration: BoxDecoration(
                    color: selected ? colors.accent : Colors.transparent,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 7,
                      vertical: MediaQuery.sizeOf(context).height < 760 ? 2 : 5,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          section.icon,
                          size: 17,
                          // Selected text/icon sit on the fixed blue
                          // accent gradient above (a brand highlight,
                          // not the page background) and stay a light
                          // color in both themes; unselected reads the
                          // active theme so the shell responds to
                          // Appearance like every other surface.
                          color: selected
                              ? const Color(0xffaac5d8)
                              : colors.inkSoft,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            section.label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: selected
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                              color: selected
                                  ? const Color(0xffccdded)
                                  : colors.ink,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _BrainStatusPill extends StatelessWidget {
  const _BrainStatusPill({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final state = AppStateScope.of(context);
    final brain = state.activeBrain;
    final configured = brain?.isConfigured ?? false;
    final reachable =
        configured && (state.activeBrainProvider?.available ?? false);
    final label = !configured
        ? 'Brain: None (click to configure)'
        : 'Brain: ${brain!.providerId} (${brain.model})';
    final statusColor = reachable ? Colors.green : Colors.orange;
    return Semantics(
      button: true,
      label:
          '$label${configured ? (reachable ? ', reachable' : ', unreachable') : ''}',
      child: Tooltip(
        message: configured
            ? '${reachable ? 'Reachable' : 'Unreachable'} — open Model Providers'
            : 'Open Model Providers',
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(999),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: UriSpace.sm,
                vertical: UriSpace.xs,
              ),
              decoration: BoxDecoration(
                color: colors.surfaceSunken,
                border: Border.all(color: colors.border),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: statusColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SidebarFooter extends StatelessWidget {
  const _SidebarFooter();
  @override
  Widget build(BuildContext context) => ShaderMask(
    shaderCallback: (rect) => const LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [Colors.transparent, Colors.black],
      stops: [0.0, 0.55],
    ).createShader(rect),
    blendMode: BlendMode.dstIn,
    child: Container(
      height: 150,
      width: double.infinity,
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/misty_forest_sikkim.jpg'),
          fit: BoxFit.cover,
        ),
      ),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.transparent, Color(0xff020910)],
            stops: [0.0, 0.85],
          ),
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Text(
              '\u201cSmall steps.\nA more organized tomorrow.\u201d\n\u2014 URI',
              style: TextStyle(color: Color(0xffccdded), fontSize: 9),
            ),
            SizedBox(height: 12),
            Text(
              'NIT Sikkim  v0.1.0',
              style: TextStyle(color: Color(0xffaac5d8), fontSize: 9),
            ),
          ],
        ),
      ),
    ),
  );
}

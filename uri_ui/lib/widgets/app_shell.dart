import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/app_state_scope.dart';
import '../theme/uri_theme.dart';
import 'uri_wordmark.dart';

class UriSection {
  const UriSection({
    required this.label,
    required this.icon,
    required this.builder,
    this.mobileLabel,
  });

  final String label;
  final String? mobileLabel;
  final IconData icon;
  final WidgetBuilder builder;
}

/// 5 primary destination indices in [AppShell] per Hybrid UI Frozen Blueprint §4.1:
/// Home, Chat, Tasks, Connections & Providers, Settings.
class ShellIndex {
  ShellIndex._();
  static const home = 0;
  static const chat = 1;
  static const tasks = 2;
  static const connections = 3;
  static const settings = 4;

  // Compatibility aliases for legacy references (activity and history now live under Chat)
  static const activity = 1;
  static const history = 1;
}

/// The persistent application shell: a collapsible sidebar on wide (desktop-first)
/// layouts, and a 5-item bottom navigation bar on narrow/mobile widths.
class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.sections, this.initialIndex = 0});

  final List<UriSection> sections;
  final int initialIndex;

  @override
  State<AppShell> createState() => AppShellState();
}

class AppShellState extends State<AppShell> {
  late int _index = widget.initialIndex;
  bool _sidebarCollapsed = false;

  static const String _sidebarCollapsedPrefKey = 'uri_sidebar_collapsed_v1';

  @override
  void initState() {
    super.initState();
    _loadSidebarPreference();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) AppStateScope.of(context).loadActiveBrain();
    });
  }

  Future<void> _loadSidebarPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getBool(_sidebarCollapsedPrefKey);
    if (saved != null && mounted) {
      setState(() => _sidebarCollapsed = saved);
    }
  }

  Future<void> _toggleSidebar() async {
    setState(() => _sidebarCollapsed = !_sidebarCollapsed);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_sidebarCollapsedPrefKey, _sidebarCollapsed);
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
        body: Row(
          children: [
            _Sidebar(
              sections: widget.sections,
              index: _index,
              collapsed: _sidebarCollapsed,
              onToggleCollapse: _toggleSidebar,
              onSelect: goTo,
            ),
            Expanded(
              child: Column(
                children: [
                  _ShellTopbar(
                    title: widget.sections[_index].label,
                    // Frozen Blueprint §4.4: Compact is a Workspace
                    // (desktop-width) presentation only — the reference's
                    // MobileApp.dc.html has no equivalent toggle, and a
                    // fixed 420x580 floating window has nowhere to fit
                    // on a narrow layout, so this button only exists in
                    // the wide topbar built here.
                    onCompactToggle: () =>
                        AppStateScope.of(context).setCompact(true),
                  ),
                  Expanded(
                    child: SafeArea(
                      top: false,
                      child: content,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: colors.canvas,
      appBar: AppBar(
        backgroundColor: colors.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const _Wordmark(),
            const SizedBox(width: UriSpace.xs),
            Text(
              '/ ${widget.sections[_index].label}',
              style: TextStyle(
                fontSize: 14,
                color: colors.inkSoft,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
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
              label: section.mobileLabel ?? section.label,
            ),
        ],
      ),
    );
  }
}

/// Topbar across wide layouts: breadcrumb page title on the left;
/// compact mode button on the right.
///
/// Live UX Repair §1: the 4 circular theme swatches (Frozen Blueprint
/// §4.1 / Palettes.dc.html) were removed from here on the User's direct
/// instruction - theme selection lives only under Settings > Appearance
/// now (already implemented, see appearance_settings_screen.dart),
/// which was always the second, redundant place this same choice lived.
class _ShellTopbar extends StatelessWidget {
  const _ShellTopbar({
    required this.title,
    required this.onCompactToggle,
  });

  final String title;
  final VoidCallback onCompactToggle;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(
          bottom: BorderSide(color: colors.border),
        ),
      ),
      child: Row(
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: colors.ink,
            ),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.picture_in_picture_alt_outlined, size: 18),
            tooltip: 'Compact mode',
            onPressed: onCompactToggle,
            color: colors.inkSoft,
            splashRadius: 18,
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
    required this.collapsed,
    required this.onToggleCollapse,
    required this.onSelect,
  });

  final List<UriSection> sections;
  final int index;
  final bool collapsed;
  final VoidCallback onToggleCollapse;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final width = collapsed ? 64.0 : 240.0;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: width,
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(
          right: BorderSide(color: colors.border),
        ),
      ),
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isRail = collapsed || constraints.maxWidth < 180;

            return Column(
              children: [
                // Brand Row
                Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: isRail ? 8 : 12,
                    vertical: 12,
                  ),
                  child: SizedBox(
                    height: 36,
                    child: isRail
                        ? Center(
                            child: IconButton(
                              key: const ValueKey('expand_btn'),
                              icon: const Icon(Icons.menu, size: 20),
                              tooltip: 'Expand sidebar',
                              onPressed: onToggleCollapse,
                              color: colors.inkSoft,
                              splashRadius: 18,
                              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                              padding: EdgeInsets.zero,
                            ),
                          )
                        : Row(
                            key: const ValueKey('expanded_brand_row'),
                            children: [
                              const Expanded(
                                child: Align(
                                  alignment: Alignment.centerLeft,
                                  child: FittedBox(
                                    fit: BoxFit.scaleDown,
                                    child: UriWordmark(markSize: 24),
                                  ),
                                ),
                              ),
                              IconButton(
                                key: const ValueKey('collapse_btn'),
                                icon: const Icon(Icons.menu_open, size: 20),
                                tooltip: 'Collapse sidebar',
                                onPressed: onToggleCollapse,
                                color: colors.inkSoft,
                                splashRadius: 18,
                                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                                padding: EdgeInsets.zero,
                              ),
                            ],
                          ),
                  ),
                ),
                Divider(height: 1, color: colors.border),
                const SizedBox(height: 8),
                // Nav Items
                Expanded(
                  child: ListView.separated(
                    padding: EdgeInsets.symmetric(
                      horizontal: isRail ? 10 : 8,
                    ),
                    itemCount: sections.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 4),
                    itemBuilder: (context, i) {
                      final section = sections[i];
                      final isSelected = index == i;

                      if (isRail) {
                        return _CollapsedRailItem(
                          icon: section.icon,
                          label: section.label,
                          selected: isSelected,
                          onTap: () => onSelect(i),
                        );
                      }

                      return _ExpandedNavItem(
                        icon: section.icon,
                        label: section.label,
                        selected: isSelected,
                        onTap: () => onSelect(i),
                      );
                    },
                  ),
                ),
                // Footer
                if (!isRail)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Colors.green,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'URI System Active',
                            style: TextStyle(
                              fontSize: 11,
                              color: colors.inkFaint,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CollapsedRailItem extends StatelessWidget {
  const _CollapsedRailItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    return Tooltip(
      message: label,
      preferBelow: false,
      child: Material(
        color: selected ? colors.accentSoft : Colors.transparent,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.sm),
          onTap: onTap,
          child: SizedBox(
            width: 44,
            height: 44,
            child: Center(
              child: Icon(
                icon,
                size: 20,
                color: selected ? colors.accent : colors.inkSoft,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ExpandedNavItem extends StatelessWidget {
  const _ExpandedNavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);

    return Material(
      color: selected ? colors.accentSoft : Colors.transparent,
      borderRadius: BorderRadius.circular(UriRadius.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(UriRadius.sm),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              Icon(
                icon,
                size: 18,
                color: selected ? colors.accent : colors.inkSoft,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    color: selected ? colors.accent : colors.ink,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) => const UriWordmark(markSize: 24);
}

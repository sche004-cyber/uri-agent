import 'package:flutter/material.dart';

import '../theme/uri_theme.dart';

class UriSection {
  const UriSection({required this.label, required this.icon, required this.builder});

  final String label;
  final IconData icon;
  final WidgetBuilder builder;
}

/// Section indices in [AppShell] — kept in one place so any screen can
/// jump to another tab (e.g. Home's Ask box, or a blocked Ask URI turn
/// pointing at Connections) without depending on the sections list.
class ShellIndex {
  ShellIndex._();
  static const home = 0;
  static const ask = 1;
  static const tasks = 2;
  static const connections = 3;
  static const activity = 4;
  static const settings = 5;
}

/// The persistent application shell: a sidebar on wide (desktop-first)
/// layouts, collapsing to a bottom navigation bar on narrow/mobile
/// widths. Screens are swapped in place — this is what makes
/// Home -> Ask URI -> Connections navigable within one running app.
class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.sections, this.initialIndex = 0});

  final List<UriSection> sections;
  final int initialIndex;

  @override
  State<AppShell> createState() => AppShellState();
}

class AppShellState extends State<AppShell> {
  late int _index = widget.initialIndex;

  void goTo(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 900;

    final content = KeyedSubtree(
      key: ValueKey(_index),
      child: widget.sections[_index].builder(context),
    );

    if (isWide) {
      return Scaffold(
        backgroundColor: UriColors.canvas,
        body: Row(
          children: [
            _Sidebar(sections: widget.sections, index: _index, onSelect: goTo),
            Expanded(
              child: SafeArea(
                child: content,
              ),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: UriColors.canvas,
      appBar: AppBar(
        backgroundColor: UriColors.canvas,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [_Wordmark()],
        ),
      ),
      body: SafeArea(child: content),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: goTo,
        backgroundColor: UriColors.surface,
        destinations: [
          for (final section in widget.sections)
            NavigationDestination(icon: Icon(section.icon), label: section.label),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.sections, required this.index, required this.onSelect});

  final List<UriSection> sections;
  final int index;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 260,
      decoration: const BoxDecoration(
        color: UriColors.surface,
        border: Border(right: BorderSide(color: UriColors.border)),
      ),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(UriSpace.lg, UriSpace.xl, UriSpace.lg, UriSpace.lg),
              child: _Wordmark(),
            ),
            for (var i = 0; i < sections.length; i++)
              _SidebarItem(
                section: sections[i],
                selected: i == index,
                onTap: () => onSelect(i),
              ),
            const Spacer(),
            const Padding(
              padding: EdgeInsets.all(UriSpace.lg),
              child: _SidebarFooter(),
            ),
          ],
        ),
      ),
    );
  }
}

class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: UriColors.ink,
            borderRadius: BorderRadius.circular(9),
          ),
          alignment: Alignment.center,
          child: const Text(
            'U',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16),
          ),
        ),
        const SizedBox(width: 10),
        Text('URI', style: Theme.of(context).textTheme.headlineSmall),
      ],
    );
  }
}

class _SidebarItem extends StatelessWidget {
  const _SidebarItem({required this.section, required this.selected, required this.onTap});

  final UriSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: UriSpace.sm, vertical: 2),
      child: Material(
        color: selected ? UriColors.accentSoft : Colors.transparent,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.sm),
          onTap: onTap,
          child: Row(
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: 3,
                height: 18,
                margin: const EdgeInsets.only(left: 2),
                decoration: BoxDecoration(
                  color: selected ? UriColors.accent : Colors.transparent,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
                  child: Row(
                    children: [
                      Icon(
                        section.icon,
                        size: 19,
                        color: selected ? UriColors.accentInk : UriColors.inkFaint,
                      ),
                      const SizedBox(width: 12),
                      Text(
                        section.label,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? UriColors.accentInk : UriColors.inkSoft,
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
    );
  }
}

class _SidebarFooter extends StatelessWidget {
  const _SidebarFooter();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          const Icon(Icons.shield_outlined, size: 16, color: UriColors.inkFaint),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'URI never acts without your approval unless you\'ve allowed it.',
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../theme/uri_theme.dart';
import '../../widgets/screen_header.dart';
import 'about_settings_screen.dart';
import 'capabilities_settings_screen.dart';
import 'connections_settings_screen.dart';
import 'diagnostics_settings_screen.dart';
import 'memory_settings_screen.dart';
import 'preferences_settings_screen.dart';
import 'profile_settings_screen.dart';
import 'uri_server_settings_screen.dart';

class _SettingsCategory {
  const _SettingsCategory({
    required this.label,
    required this.subtitle,
    required this.icon,
    required this.builder,
  });

  final String label;
  final String subtitle;
  final IconData icon;
  final WidgetBuilder builder;
}

final _categories = <_SettingsCategory>[
  _SettingsCategory(
    label: 'Profile',
    subtitle: 'Who is signed in on this device, and this install\'s identity.',
    icon: Icons.person_outline_rounded,
    builder: (_) => const ProfileSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'URI',
    subtitle: 'Which backend this device talks to.',
    icon: Icons.dns_outlined,
    builder: (_) => const UriServerSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'Preferences',
    subtitle: 'How much URI does on its own, its tone, and how the app looks.',
    icon: Icons.tune_rounded,
    builder: (_) => const PreferencesSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'Connections',
    subtitle: 'Services URI can use on your behalf.',
    icon: Icons.hub_outlined,
    builder: (_) => const ConnectionsSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'Memory',
    subtitle: 'Facts URI holds about you, and what it remembers between conversations.',
    icon: Icons.psychology_outlined,
    builder: (_) => const MemorySettingsScreen(),
  ),
  _SettingsCategory(
    label: 'Capabilities',
    subtitle: 'What URI can actually do right now, reported by the server.',
    icon: Icons.checklist_rounded,
    builder: (_) => const CapabilitiesSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'Diagnostics',
    subtitle: 'Connection health and this device\'s identifiers.',
    icon: Icons.monitor_heart_outlined,
    builder: (_) => const DiagnosticsSettingsScreen(),
  ),
  _SettingsCategory(
    label: 'About',
    subtitle: 'App and backend information.',
    icon: Icons.info_outline_rounded,
    builder: (_) => const AboutSettingsScreen(),
  ),
];

/// Settings, organized into named categories rather than one long
/// scroll: a phone gets a list that swaps in-place to the selected
/// category (with a back affordance), a tablet/desktop gets a
/// persistent category list with the selected category's content
/// beside it (master-detail) — matching the same wide-layout
/// threshold [AppShell] itself uses.
///
/// Deliberately never uses [Navigator.push] for this: every category
/// screen (see ConnectionsSettingsScreen) needs to reach
/// [AppShellState] via [BuildContext.findAncestorStateOfType] to jump
/// to another shell tab, and a pushed route would sit in the
/// Navigator's stack as a sibling of the shell rather than a
/// descendant of it — breaking that lookup. An in-place selection
/// (same mechanism the wide layout already uses) keeps every category
/// screen's context a true descendant of the shell on every layout.
class SettingsShell extends StatefulWidget {
  const SettingsShell({super.key});

  @override
  State<SettingsShell> createState() => _SettingsShellState();
}

class _SettingsShellState extends State<SettingsShell> {
  /// Null only on a compact layout showing the category list; a wide
  /// layout always has a selection (defaults to the first category).
  int? _selected;

  @override
  Widget build(BuildContext context) {
    if (UriBreakpoints.isWide(context)) {
      return _WideSettings(
        selected: _selected ?? 0,
        onSelect: (i) => setState(() => _selected = i),
      );
    }

    final selected = _selected;
    if (selected == null) {
      return _CompactSettingsList(onSelect: (i) => setState(() => _selected = i));
    }
    return _CompactSettingsDetail(
      category: _categories[selected],
      onBack: () => setState(() => _selected = null),
    );
  }
}

class _WideSettings extends StatelessWidget {
  const _WideSettings({required this.selected, required this.onSelect});

  final int selected;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final category = _categories[selected];

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          width: 260,
          child: Container(
            decoration: BoxDecoration(border: Border(right: BorderSide(color: colors.border))),
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: UriSpace.md),
              children: [
                for (var i = 0; i < _categories.length; i++)
                  _CategoryListTile(
                    category: _categories[i],
                    selected: i == selected,
                    onTap: () => onSelect(i),
                  ),
              ],
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(UriSpace.xl),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ScreenHeader(title: category.label, subtitle: category.subtitle),
                  category.builder(context),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _CategoryListTile extends StatelessWidget {
  const _CategoryListTile({required this.category, required this.selected, required this.onTap});

  final _SettingsCategory category;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Material(
      color: selected ? colors.accentSoft : Colors.transparent,
      child: ListTile(
        leading: Icon(category.icon, color: selected ? colors.accentInk : colors.inkFaint),
        title: Text(
          category.label,
          style: TextStyle(
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            color: selected ? colors.accentInk : colors.ink,
          ),
        ),
        trailing: selected ? null : const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
      ),
    );
  }
}

class _CompactSettingsList extends StatelessWidget {
  const _CompactSettingsList({required this.onSelect});

  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(UriSpace.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const ScreenHeader(
            title: 'Settings',
            subtitle: 'Account, connections, preferences, and how URI behaves.',
          ),
          Card(
            child: Column(
              children: [
                for (var i = 0; i < _categories.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  _CategoryListTile(
                    category: _categories[i],
                    selected: false,
                    onTap: () => onSelect(i),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CompactSettingsDetail extends StatelessWidget {
  const _CompactSettingsDetail({required this.category, required this.onBack});

  final _SettingsCategory category;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(UriSpace.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: onBack,
                icon: const Icon(Icons.arrow_back_rounded),
                tooltip: 'Back to Settings',
              ),
              const SizedBox(width: UriSpace.xs),
              Expanded(child: Text(category.label, style: Theme.of(context).textTheme.headlineMedium)),
            ],
          ),
          const SizedBox(height: 6),
          Text(category.subtitle, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: UriSpace.xl),
          category.builder(context),
        ],
      ),
    );
  }
}

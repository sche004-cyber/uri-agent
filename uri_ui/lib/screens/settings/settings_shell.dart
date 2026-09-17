import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/screen_header.dart';
import 'about_settings_screen.dart';
import 'admin_grants_screen.dart';
import 'appearance_settings_screen.dart';
import 'capabilities_settings_screen.dart';
import 'diagnostics_settings_screen.dart';
import 'memory_context_settings_screen.dart';
import 'memory_settings_screen.dart';
import 'preferences_settings_screen.dart';
import 'profile_settings_screen.dart';
import 'uri_server_settings_screen.dart';

/// Hybrid UI Frozen Blueprint §4.7's two named groups. Connections and
/// Model Providers are deliberately absent here — both moved to the new
/// top-level Connections & Providers screen (§4.6); "Tools & Skills" is
/// the reference's own illustrative label with no real URI screen and
/// is never built (per the uri-ux-design skill's "map only real,
/// verified backend capability" rule).
enum _SettingsGroup { account, system }

extension on _SettingsGroup {
  String get label => switch (this) {
    _SettingsGroup.account => 'Account',
    _SettingsGroup.system => 'System',
  };
}

class _SettingsCategory {
  const _SettingsCategory({
    required this.group,
    required this.label,
    required this.subtitle,
    required this.icon,
    required this.builder,
  });

  final _SettingsGroup group;
  final String label;
  final String subtitle;
  final IconData icon;
  final WidgetBuilder builder;
}

final _categories = <_SettingsCategory>[
  _SettingsCategory(
    group: _SettingsGroup.account,
    label: 'Profile',
    subtitle: 'Who is signed in on this device, and this install\'s identity.',
    icon: Icons.person_outline_rounded,
    builder: (_) => const ProfileSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.account,
    label: 'Preferences',
    subtitle: 'How much URI does on its own, and its tone.',
    icon: Icons.tune_rounded,
    builder: (_) => const PreferencesSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.account,
    label: 'Memory',
    subtitle: 'Facts URI holds about you, and what it remembers between conversations.',
    icon: Icons.psychology_outlined,
    builder: (_) => const MemorySettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.account,
    label: 'Memory & Context',
    subtitle:
        'Memory budgets, provider settings, and conversation compression.',
    icon: Icons.memory_outlined,
    builder: (_) => const MemoryContextSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.system,
    label: 'URI',
    subtitle: 'Which backend this device talks to.',
    icon: Icons.dns_outlined,
    builder: (_) => const UriServerSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.system,
    label: 'Capabilities',
    subtitle: 'What URI can actually do right now, reported by the server.',
    icon: Icons.checklist_rounded,
    builder: (_) => const CapabilitiesSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.system,
    label: 'Diagnostics',
    subtitle: 'Connection health and this device\'s identifiers.',
    icon: Icons.monitor_heart_outlined,
    builder: (_) => const DiagnosticsSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.system,
    label: 'About',
    subtitle: 'App and backend information.',
    icon: Icons.info_outline_rounded,
    builder: (_) => const AboutSettingsScreen(),
  ),
  _SettingsCategory(
    group: _SettingsGroup.system,
    label: 'Appearance',
    subtitle: 'The 4 URI themes, or follow your device.',
    icon: Icons.palette_outlined,
    builder: (_) => const AppearanceSettingsScreen(),
  ),
];

List<_SettingsCategory> _getCategories(BuildContext context) {
  final isAdmin = AppStateScope.of(context).isAdmin;
  return [
    ..._categories,
    if (isAdmin)
      _SettingsCategory(
        group: _SettingsGroup.system,
        label: 'Capability Grants',
        subtitle:
            'Per-user capability authorization and grants administration.',
        icon: Icons.admin_panel_settings_outlined,
        builder: (_) => const AdminGrantsScreen(),
      ),
  ];
}

/// Settings, organized into named categories rather than one long
/// scroll: a phone gets a list that swaps in-place to the selected
/// category (with a back affordance), a tablet/desktop gets a
/// persistent category list with the selected category's content
/// beside it (master-detail) — matching the same wide-layout
/// threshold [AppShell] itself uses.
///
/// Deliberately never uses [Navigator.push] for this: a category
/// screen may need to reach [AppShellState] via
/// [BuildContext.findAncestorStateOfType] to jump to another shell tab
/// (see `ask_uri_screen.dart`/`history_screen.dart`'s own uses of the
/// same lookup), and a pushed route would sit in the
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
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedAccountInfo) state.loadAccountInfo();
      _selectRequestedCategory(state.targetSettingsCategory);
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _selectRequestedCategory(AppStateScope.of(context).targetSettingsCategory);
  }

  void _selectRequestedCategory(String? label) {
    if (label == null) return;
    final index = _getCategories(context)
        .indexWhere((category) => category.label == label);
    if (index >= 0) {
      _selected = index;
      AppStateScope.of(context).targetSettingsCategory = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final categories = _getCategories(context);
        final requested = AppStateScope.of(context).targetSettingsCategory;
        if (requested != null) {
          final index = categories.indexWhere(
            (category) => category.label == requested,
          );
          if (index >= 0) {
            _selected = index;
            AppStateScope.of(context).targetSettingsCategory = null;
          }
        }

        if (UriBreakpoints.isWide(context)) {
          final selected = (_selected != null && _selected! < categories.length)
              ? _selected!
              : 0;
          return _WideSettings(
            categories: categories,
            selected: selected,
            onSelect: (i) => setState(() => _selected = i),
          );
        }

        final selected = _selected;
        if (selected == null || selected >= categories.length) {
          return _CompactSettingsList(
            categories: categories,
            onSelect: (i) => setState(() => _selected = i),
          );
        }
        return _CompactSettingsDetail(
          category: categories[selected],
          onBack: () => setState(() => _selected = null),
        );
      },
    );
  }
}

class _WideSettings extends StatelessWidget {
  const _WideSettings({
    required this.categories,
    required this.selected,
    required this.onSelect,
  });

  final List<_SettingsCategory> categories;
  final int selected;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final category = categories[selected];

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          width: 260,
          child: Container(
            decoration: BoxDecoration(
              border: Border(right: BorderSide(color: colors.border)),
            ),
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: UriSpace.md),
              children: [
                for (final group in _SettingsGroup.values) ...[
                  _GroupHeader(label: group.label),
                  for (var i = 0; i < categories.length; i++)
                    if (categories[i].group == group)
                      _CategoryListTile(
                        category: categories[i],
                        selected: i == selected,
                        onTap: () => onSelect(i),
                      ),
                ],
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
                  ScreenHeader(
                    title: category.label,
                    subtitle: category.subtitle,
                  ),
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

class _GroupHeader extends StatelessWidget {
  const _GroupHeader({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: colors.inkFaint,
        ),
      ),
    );
  }
}

class _CategoryListTile extends StatelessWidget {
  const _CategoryListTile({
    required this.category,
    required this.selected,
    required this.onTap,
  });

  final _SettingsCategory category;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Material(
      color: selected ? colors.accentSoft : Colors.transparent,
      child: ListTile(
        leading: Icon(
          category.icon,
          color: selected ? colors.accentInk : colors.inkFaint,
        ),
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
  const _CompactSettingsList({
    required this.categories,
    required this.onSelect,
  });

  final List<_SettingsCategory> categories;
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
          for (final group in _SettingsGroup.values) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: UriSpace.xs),
              child: _GroupHeader(label: group.label),
            ),
            Card(
              margin: const EdgeInsets.only(bottom: UriSpace.md),
              child: Column(
                children: [
                  for (var i = 0; i < categories.length; i++)
                    if (categories[i].group == group) ...[
                      if (categories.sublist(0, i).any((c) => c.group == group))
                        const Divider(height: 1),
                      _CategoryListTile(
                        category: categories[i],
                        selected: false,
                        onTap: () => onSelect(i),
                      ),
                    ],
                ],
              ),
            ),
          ],
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
              Expanded(
                child: Text(
                  category.label,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
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

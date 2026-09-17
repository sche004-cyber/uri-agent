import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';

/// Hybrid UI Frozen Blueprint §4.7: the 4-theme picker, moved into
/// Settings (out of the old Preferences/topbar-only locations). Backed
/// by [UriThemeChoice] + `ThemeStore`, the same choice the topbar's own
/// 4 swatches (Frozen Blueprint §4.1, the one approved exception) write
/// to — picking here or there is the same action on the same state.
class AppearanceSettingsScreen extends StatelessWidget {
  const AppearanceSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(UriSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Theme', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 2),
                Text(
                  'Pick one of the 4 URI themes, or follow your device.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: UriSpace.md),
                Wrap(
                  spacing: UriSpace.sm,
                  runSpacing: UriSpace.sm,
                  children: [
                    for (final choice in UriThemeChoice.values)
                      _ThemeChoiceCard(
                        choice: choice,
                        selected: state.themeChoice == choice,
                        onTap: () => state.setThemeChoice(choice),
                      ),
                  ],
                ),
                const SizedBox(height: UriSpace.sm),
                Text(
                  'System follows your device\'s light/dark setting until '
                  'you pick a theme here.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: colors.inkFaint),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ThemeChoiceCard extends StatelessWidget {
  const _ThemeChoiceCard({
    required this.choice,
    required this.selected,
    required this.onTap,
  });

  final UriThemeChoice choice;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final swatch = choice.swatch;

    return Semantics(
      button: true,
      selected: selected,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: Container(
          width: 150,
          padding: const EdgeInsets.all(UriSpace.sm),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(UriRadius.sm),
            border: Border.all(
              color: selected ? colors.accent : colors.border,
              width: selected ? 2 : 1,
            ),
            color: selected ? colors.accentSoft : Colors.transparent,
          ),
          child: Row(
            children: [
              if (swatch != null)
                Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(color: swatch, shape: BoxShape.circle),
                )
              else
                Icon(
                  Icons.brightness_auto_outlined,
                  size: 16,
                  color: colors.inkFaint,
                ),
              const SizedBox(width: UriSpace.sm),
              Expanded(
                child: Text(
                  choice.label,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: selected ? colors.accentInk : colors.ink,
                  ),
                ),
              ),
              if (selected)
                Icon(Icons.check_circle, size: 16, color: colors.accentInk),
            ],
          ),
        ),
      ),
    );
  }
}

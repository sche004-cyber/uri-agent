import 'package:flutter/material.dart';

import '../../models/user_preferences.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';

/// How URI behaves for this user: approval level and tone. Appearance
/// (how this app itself looks) moved to Settings → Appearance per
/// Hybrid UI Frozen Blueprint §4.7.
class PreferencesSettingsScreen extends StatelessWidget {
  const PreferencesSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final prefs = state.preferences;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Section(
              title: 'Approval level',
              description: 'How much URI does before checking with you.',
              child: RadioGroup<AutonomyLevel>(
                groupValue: prefs.autonomyLevel,
                onChanged: (value) {
                  if (value != null) {
                    state.updatePreferences(prefs.copyWith(autonomyLevel: value));
                  }
                },
                child: const Column(
                  children: [
                    RadioListTile<AutonomyLevel>(
                      contentPadding: EdgeInsets.zero,
                      value: AutonomyLevel.askEveryTime,
                      title: Text('Ask me every time'),
                    ),
                    RadioListTile<AutonomyLevel>(
                      contentPadding: EdgeInsets.zero,
                      value: AutonomyLevel.routineAutoApprove,
                      title: Text('Auto-approve routine work'),
                    ),
                  ],
                ),
              ),
            ),
            _Section(
              title: 'Communication style',
              description: 'The tone URI uses in drafts and replies.',
              child: Wrap(
                spacing: 8,
                children: [
                  for (final style in CommunicationStyle.values)
                    ChoiceChip(
                      label: Text(_styleLabel(style)),
                      selected: prefs.communicationStyle == style,
                      onSelected: (_) => state.updatePreferences(
                        prefs.copyWith(communicationStyle: style),
                      ),
                    ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  String _styleLabel(CommunicationStyle style) {
    switch (style) {
      case CommunicationStyle.formal:
        return 'Formal';
      case CommunicationStyle.concise:
        return 'Concise';
      case CommunicationStyle.conversational:
        return 'Conversational';
    }
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.description, required this.child});

  final String title;
  final String description;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.lg),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(UriSpace.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: theme.textTheme.titleMedium),
              const SizedBox(height: 2),
              Text(description, style: theme.textTheme.bodyMedium),
              const SizedBox(height: UriSpace.sm),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

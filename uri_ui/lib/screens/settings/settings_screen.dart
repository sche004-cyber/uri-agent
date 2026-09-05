import 'package:flutter/material.dart';

import '../../models/user_preferences.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/server_address_section.dart';

/// A sensible home for the controls a first version needs a place for,
/// even where the underlying feature (accounts, privacy policy, connection
/// management detail) isn't built yet. Preference controls here are wired
/// to real (if UI-only) state; the rest are clearly-labelled placeholders.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final prefs = state.preferences;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(UriSpace.xl),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const ScreenHeader(
                  title: 'Settings',
                  subtitle: 'Account, connections, privacy, and how URI behaves.',
                ),

                _SettingsSection(
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

                _SettingsSection(
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

                _SettingsSection(
                  title: 'Account',
                  description: 'Sign-in and identity management.',
                  child: _AccountRow(
                    username: state.currentUsername,
                    onLogOut: () => state.logout(),
                  ),
                ),
                _SettingsSection(
                  title: 'URI server',
                  description:
                      'Which backend this device talks to. On a phone, point this at your '
                      "PC's address on the same network — not localhost, which means this "
                      'phone itself.',
                  child: ServerAddressSection(
                    baseUrl: state.baseUrl,
                    connectionStatus: state.connectionStatus,
                    connectionErrorDetail: state.lastConnectionErrorDetail,
                    onSave: (url) => state.setBaseUrl(url),
                    onTestConnection: (address) => state.checkConnection(addressOverride: address),
                  ),
                ),
                const _SettingsSection(
                  title: 'Privacy & data',
                  description: 'What URI retains, and for how long.',
                  child: _PlaceholderRow(label: 'Not available in this prototype'),
                ),
                const _SettingsSection(
                  title: 'Connection management',
                  description: 'Fine-grained per-service permissions.',
                  child: _PlaceholderRow(label: 'See the Connections tab for basic connect/disconnect'),
                ),
              ],
            ),
          ),
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

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({required this.title, required this.description, required this.child});

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

/// Prototype 1 (multi-user identity): shows which account is signed in
/// on this device and lets it log out - the one way (besides closing
/// and reopening at the login screen) to switch which user's isolated
/// URI state this client acts as. Logging back in as a different
/// account is the login screen's job, not this row's.
class _AccountRow extends StatelessWidget {
  const _AccountRow({required this.username, required this.onLogOut});

  final String? username;
  final VoidCallback onLogOut;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          const Icon(Icons.person_outline_rounded, size: 16, color: UriColors.inkFaint),
          const SizedBox(width: UriSpace.sm),
          Expanded(
            child: Text(
              username != null ? 'Signed in as $username' : 'Not signed in',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          TextButton(onPressed: onLogOut, child: const Text('Log out')),
        ],
      ),
    );
  }
}

class _PlaceholderRow extends StatelessWidget {
  const _PlaceholderRow({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: UriColors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded, size: 16, color: UriColors.inkFaint),
          const SizedBox(width: UriSpace.sm),
          Expanded(child: Text(label, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

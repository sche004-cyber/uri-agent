import 'package:flutter/material.dart';

import '../../models/user_preferences.dart';
import '../../services/app_state.dart' show BackendConnectionStatus;
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/screen_header.dart';

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
                  child: _ServerAddressSection(
                    baseUrl: state.baseUrl,
                    connectionStatus: state.connectionStatus,
                    onSave: (url) => state.setBaseUrl(url),
                    onTestConnection: () => state.checkConnection(),
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

/// Prototype 2 (multi-client + runtime awareness): lets this device be
/// pointed at a specific backend address, and proves reconnect/
/// disconnect with a clear, explicit "Test connection" action rather
/// than only surfacing connectivity problems as a failed Ask URI
/// request later.
class _ServerAddressSection extends StatefulWidget {
  const _ServerAddressSection({
    required this.baseUrl,
    required this.connectionStatus,
    required this.onSave,
    required this.onTestConnection,
  });

  final String baseUrl;
  final BackendConnectionStatus connectionStatus;
  final ValueChanged<String> onSave;
  final Future<bool> Function() onTestConnection;

  @override
  State<_ServerAddressSection> createState() => _ServerAddressSectionState();
}

class _ServerAddressSectionState extends State<_ServerAddressSection> {
  late final TextEditingController _controller = TextEditingController(text: widget.baseUrl);
  bool _isTesting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() => _isTesting = true);
    await widget.onTestConnection();
    if (mounted) setState(() => _isTesting = false);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _controller,
          decoration: const InputDecoration(
            labelText: 'Backend address',
            hintText: 'http://192.168.1.23:8000',
          ),
          onSubmitted: widget.onSave,
        ),
        const SizedBox(height: UriSpace.sm),
        Row(
          children: [
            ElevatedButton(
              onPressed: () => widget.onSave(_controller.text.trim()),
              child: const Text('Save'),
            ),
            const SizedBox(width: UriSpace.sm),
            OutlinedButton(
              onPressed: _isTesting ? null : _testConnection,
              child: _isTesting
                  ? const SizedBox(
                      height: 14,
                      width: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Test connection'),
            ),
            const SizedBox(width: UriSpace.sm),
            _ConnectionStatusBadge(status: widget.connectionStatus),
          ],
        ),
      ],
    );
  }
}

class _ConnectionStatusBadge extends StatelessWidget {
  const _ConnectionStatusBadge({required this.status});

  final BackendConnectionStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = switch (status) {
      BackendConnectionStatus.reachable => ('Connected', UriColors.success, UriColors.successSoft),
      BackendConnectionStatus.unreachable => ('Not reachable', UriColors.danger, UriColors.dangerSoft),
      BackendConnectionStatus.unknown => ('Not tested yet', UriColors.inkFaint, UriColors.surfaceSunken),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: UriSpace.sm, vertical: 4),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(UriRadius.sm)),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: color, fontWeight: FontWeight.w600),
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

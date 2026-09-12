import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';
import 'memory_settings_screen.dart';

/// Content-sized settings section: intentionally no Scaffold or scroll view,
/// because SettingsShell supplies the page scroll contract.
class MemoryContextSettingsScreen extends StatefulWidget {
  const MemoryContextSettingsScreen({super.key});
  @override
  State<MemoryContextSettingsScreen> createState() =>
      _MemoryContextSettingsScreenState();
}

class _MemoryContextSettingsScreenState
    extends State<MemoryContextSettingsScreen> {
  bool _loaded = false;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_loaded) {
      _loaded = true;
      AppStateScope.of(context).loadMemoryContextSettings();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = AppStateScope.of(context);
    final settings = state.memoryContextSettings;
    if (settings == null) {
      return const Padding(
        padding: EdgeInsets.all(UriSpace.xl),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Control what URI retains and how long conversations are compacted. These preferences never change memory consent.',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: UriSpace.md),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(UriSpace.md),
            child: Column(
              children: [
                _toggle(
                  'Persistent Memory',
                  settings.persistentMemory,
                  (value) => _save(state, {'persistent_memory': value}),
                ),
                _toggle(
                  'User Profile',
                  settings.userProfile,
                  (value) => _save(state, {'user_profile': value}),
                ),
                _number(
                  'Memory budget',
                  settings.memoryBudget,
                  'tokens',
                  (value) => _save(state, {'memory_budget': value}),
                ),
                _number(
                  'Profile budget',
                  settings.profileBudget,
                  'tokens',
                  (value) => _save(state, {'profile_budget': value}),
                ),
                _choice(
                  'Memory provider',
                  'Built-in (Local JSON)',
                  enabled: false,
                ),
                _choice('Context engine', 'Compressor', enabled: false),
              ],
            ),
          ),
        ),
        const SizedBox(height: UriSpace.md),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(UriSpace.md),
            child: Column(
              children: [
                _toggle(
                  'Auto-compression',
                  settings.autoCompression,
                  (value) => _save(state, {'auto_compression': value}),
                ),
                _number(
                  'Compression threshold',
                  settings.compressionThreshold,
                  'tokens',
                  (value) => _save(state, {'compression_threshold': value}),
                ),
                _number(
                  'Compression target',
                  settings.compressionTarget,
                  'tokens',
                  (value) => _save(state, {'compression_target': value}),
                ),
                _number(
                  'Protected recent messages',
                  settings.protectedRecentMessages,
                  'messages',
                  (value) => _save(state, {'protected_recent_messages': value}),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: UriSpace.xl),
        Text('Saved memories', style: Theme.of(context).textTheme.titleLarge),
        const MemorySettingsScreen(),
      ],
    );
  }

  Widget _toggle(String label, bool value, ValueChanged<bool> changed) =>
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(label),
        value: value,
        onChanged: changed,
      );
  Widget _choice(String label, String value, {required bool enabled}) =>
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(label),
        subtitle: Text(value),
        trailing: const Icon(Icons.lock_outline),
      );
  Widget _number(
    String label,
    int value,
    String unit,
    ValueChanged<int> changed,
  ) => ListTile(
    contentPadding: EdgeInsets.zero,
    title: Text(label),
    subtitle: Text('$value $unit'),
    trailing: IconButton(
      icon: const Icon(Icons.edit_outlined),
      onPressed: () => _editNumber(label, value, changed),
    ),
  );
  Future<void> _save(AppState state, Map<String, dynamic> values) async {
    await state.saveMemoryContextSettings(values);
  }

  Future<void> _editNumber(
    String label,
    int current,
    ValueChanged<int> changed,
  ) async {
    final controller = TextEditingController(text: '$current');
    final value = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(label),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.pop(context, int.tryParse(controller.text)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (value != null && value >= 0) changed(value);
  }
}

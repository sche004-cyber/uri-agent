import 'package:flutter/material.dart';

import '../../services/app_state.dart';
import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart'
    show AccountInfo, DeviceSession, ModeInfo;
import '../../theme/uri_theme.dart';
import '../../widgets/status_pill.dart';

/// Who is signed in, this account's role and experience tier (M22.2),
/// this install's durable identity (see GET /identity), and the
/// account's own active devices/sessions (GET /auth/devices) — real
/// values only; nothing here is a placeholder field waiting for a
/// feature that doesn't exist yet.
class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  bool _isChangingTier = false;
  bool _isChangingMode = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedIdentity) state.loadIdentity();
      if (!state.hasLoadedAccountInfo) state.loadAccountInfo();
      if (!state.hasLoadedDevices) state.loadDevices();
      if (!state.hasLoadedModeInfo) state.loadModeInfo();
    });
  }

  Future<void> _changeMode(AppState state, String mode) async {
    if (state.modeInfo?.mode == mode) return;
    setState(() => _isChangingMode = true);
    await state.setMode(mode);
    if (mounted) setState(() => _isChangingMode = false);
  }

  Future<void> _changeTier(AppState state, String tier) async {
    if (state.accountInfo?.experienceTier == tier) return;
    setState(() => _isChangingTier = true);
    await state.setExperienceTier(tier);
    if (mounted) setState(() => _isChangingTier = false);
  }

  Future<void> _revokeDevice(AppState state, DeviceSession device) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Log out this device?'),
        content: Text(
          'This ends every session on device ${device.deviceId}. That '
          'device will need to sign in again.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Log out device'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await state.revokeDevice(device.deviceId);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);
        final account = state.accountInfo;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Row(
              icon: Icons.person_outline_rounded,
              trailing: TextButton(
                onPressed: state.logout,
                child: const Text('Log out'),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      state.currentUsername != null
                          ? 'Signed in as ${state.currentUsername}'
                          : 'Not signed in',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                  if (state.hasLoadedAccountInfo && account?.role != null) ...[
                    StatusPill.forRole(context, account!.role),
                    const SizedBox(width: UriSpace.sm),
                  ],
                ],
              ),
            ),
            const SizedBox(height: UriSpace.sm),
            _Row(
              icon: Icons.badge_outlined,
              child: Text(
                state.hasLoadedIdentity
                    ? (state.identity != null
                          ? 'User ID: ${state.identity!.userId}'
                          : 'Could not read this install\'s identity from the server.')
                    : 'Checking…',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: state.identity == null && state.hasLoadedIdentity
                      ? colors.inkFaint
                      : null,
                ),
              ),
            ),
            const SizedBox(height: UriSpace.lg),
            _ExperienceTierSection(
              account: account,
              loaded: state.hasLoadedAccountInfo,
              busy: _isChangingTier,
              onSelect: (tier) => _changeTier(state, tier),
            ),
            const SizedBox(height: UriSpace.lg),
            _ModeSection(
              modeInfo: state.modeInfo,
              loaded: state.hasLoadedModeInfo,
              busy: _isChangingMode,
              onSelect: (mode) => _changeMode(state, mode),
            ),
            const SizedBox(height: UriSpace.lg),
            _DevicesSection(
              devices: state.devices,
              loaded: state.hasLoadedDevices,
              currentDeviceId: account?.deviceId,
              onRevoke: (device) => _revokeDevice(state, device),
            ),
          ],
        );
      },
    );
  }
}

/// The `mode` capability-filtering axis (M22.8) - office/diagnostic/admin.
/// Deliberately never shown alongside jargon like "token" or "context
/// window": it is a distinct axis from experience_tier (see
/// _ExperienceTierSection below) and must never be confused with it -
/// experience_tier changes how much this client explains, mode changes
/// which capabilities CapabilityResolver actually returns.
class _ModeSection extends StatelessWidget {
  const _ModeSection({
    required this.modeInfo,
    required this.loaded,
    required this.busy,
    required this.onSelect,
  });
  final ModeInfo? modeInfo;
  final bool loaded;
  final bool busy;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(UriSpace.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Work mode', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 2),
          const Text(
            'Adjusts capability dispatch scope. Does not change account security role.',
          ),
          const SizedBox(height: UriSpace.sm),
          if (!loaded)
            const SizedBox(
              height: 32,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'office', label: Text('Office')),
                ButtonSegment(value: 'diagnostic', label: Text('Diagnostic')),
                ButtonSegment(
                  value: 'admin',
                  label: Text('Full Capability (Admin Mode)'),
                ),
              ],
              selected: {modeInfo?.mode ?? 'office'},
              onSelectionChanged: busy
                  ? null
                  : (selection) => onSelect(selection.first),
            ),
        ],
      ),
    ),
  );
}

/// BASIC/ADVANCED — a zero-authority display/guidance preference (see
/// AccountInfo.experienceTier's own doc). Changing this can never
/// change what the account is authorized to do; it only ever changes
/// how much configuration surface this client shows elsewhere.
class _ExperienceTierSection extends StatelessWidget {
  const _ExperienceTierSection({
    required this.account,
    required this.loaded,
    required this.busy,
    required this.onSelect,
  });

  final AccountInfo? account;
  final bool loaded;
  final bool busy;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final tier = loaded ? account?.experienceTier : null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Experience level', style: theme.textTheme.titleMedium),
            const SizedBox(height: 2),
            Text(
              'How much configuration detail URI shows you. This never '
              'changes what your account is allowed to do.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: UriSpace.sm),
            if (!loaded)
              const SizedBox(
                height: 32,
                child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
              )
            else
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'BASIC', label: Text('Basic')),
                  ButtonSegment(value: 'ADVANCED', label: Text('Advanced')),
                ],
                selected: {tier ?? 'BASIC'},
                onSelectionChanged: busy
                    ? null
                    : (selection) => onSelect(selection.first),
              ),
          ],
        ),
      ),
    );
  }
}

/// GET /auth/devices — the logged-in account's own currently-active
/// devices. Self-scoped only: this can never show or affect another
/// account's devices (see server.py's list_my_devices).
class _DevicesSection extends StatelessWidget {
  const _DevicesSection({
    required this.devices,
    required this.loaded,
    required this.currentDeviceId,
    required this.onRevoke,
  });

  final List<DeviceSession> devices;
  final bool loaded;
  final String? currentDeviceId;
  final ValueChanged<DeviceSession> onRevoke;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(UriSpace.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Devices', style: theme.textTheme.titleMedium),
            const SizedBox(height: 2),
            Text(
              'Where this account is currently signed in.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: UriSpace.sm),
            if (!loaded)
              const SizedBox(
                height: 32,
                child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
              )
            else if (devices.isEmpty)
              Text(
                'No active devices could be read from the server.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.inkFaint,
                ),
              )
            else
              for (final device in devices)
                Padding(
                  padding: const EdgeInsets.only(top: UriSpace.xs),
                  child: Row(
                    children: [
                      Icon(
                        Icons.devices_other_outlined,
                        size: 16,
                        color: colors.inkFaint,
                      ),
                      const SizedBox(width: UriSpace.sm),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Flexible(
                                  child: Text(
                                    device.deviceId,
                                    style: theme.textTheme.bodyMedium,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (device.deviceId == currentDeviceId) ...[
                                  const SizedBox(width: UriSpace.xs),
                                  Text(
                                    '(this device)',
                                    style: theme.textTheme.labelSmall,
                                  ),
                                ],
                              ],
                            ),
                            Text(
                              '${device.sessionCount} active session(s)',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: colors.inkFaint,
                              ),
                            ),
                          ],
                        ),
                      ),
                      TextButton(
                        onPressed: () => onRevoke(device),
                        child: const Text('Log out'),
                      ),
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.icon, required this.child, this.trailing});

  final IconData icon;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.surfaceSunken,
        borderRadius: BorderRadius.circular(UriRadius.sm),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: colors.inkFaint),
          const SizedBox(width: UriSpace.sm),
          Expanded(child: child),
          ?trailing,
        ],
      ),
    );
  }
}

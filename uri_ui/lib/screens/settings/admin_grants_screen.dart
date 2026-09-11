import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../services/uri_client.dart' show AdminUserEntry, UserGrantsInfo;
import '../../theme/uri_theme.dart';
import '../../utils/capability_display.dart';
import '../../widgets/status_pill.dart';

/// M22.4: Admin-only capability grant administration screen.
///
/// Visible only when [AccountInfo.isAdmin] is true in settings navigation.
/// Displays registered users, their current capability grants, and the full
/// registry ceiling. An admin can toggle individual capabilities per user.
///
/// Optimistic UI: Toggles immediately update local state, and revert with an
/// honest error notice if the backend PUT is rejected.
/// If viewed by a non-admin, the controls remain strictly read-only.
class AdminGrantsScreen extends StatefulWidget {
  const AdminGrantsScreen({super.key});

  @override
  State<AdminGrantsScreen> createState() => _AdminGrantsScreenState();
}

class _AdminGrantsScreenState extends State<AdminGrantsScreen> {
  List<AdminUserEntry> _users = const [];
  String? _selectedUserId;
  UserGrantsInfo? _grantsInfo;
  Set<String> _optimisticGrants = {};
  bool _loadingUsers = true;
  bool _loadingGrants = false;
  bool _isSaving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _loadUsers();
    });
  }

  Future<void> _loadUsers() async {
    setState(() {
      _loadingUsers = true;
      _errorMessage = null;
    });

    final state = AppStateScope.of(context);
    try {
      final users = await state.listAdminUsers();
      if (!mounted) return;

      setState(() {
        _users = users;
        _loadingUsers = false;
        if (users.isNotEmpty) {
          _selectedUserId = users.first.userId;
        }
      });

      if (_selectedUserId != null) {
        await _loadGrantsForUser(_selectedUserId!);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingUsers = false;
        _errorMessage = 'Could not load users: $e';
      });
    }
  }

  Future<void> _loadGrantsForUser(String userId) async {
    setState(() {
      _loadingGrants = true;
      _errorMessage = null;
    });

    final state = AppStateScope.of(context);
    try {
      final info = await state.getUserGrants(userId);
      if (!mounted) return;

      setState(() {
        _grantsInfo = info;
        _optimisticGrants = Set<String>.from(info.grants);
        _loadingGrants = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingGrants = false;
        _errorMessage = 'Could not load grants for $userId: $e';
      });
    }
  }

  Future<void> _toggleGrant(String capabilityId, bool enable) async {
    final userId = _selectedUserId;
    if (userId == null || _isSaving) return;

    final state = AppStateScope.of(context);
    if (!state.isAdmin) return;

    final previousGrants = Set<String>.from(_optimisticGrants);
    final updatedGrants = Set<String>.from(_optimisticGrants);

    if (enable) {
      updatedGrants.add(capabilityId);
    } else {
      updatedGrants.remove(capabilityId);
    }

    setState(() {
      _optimisticGrants = updatedGrants;
      _isSaving = true;
    });

    final success = await state.updateUserGrants(
      userId,
      updatedGrants.toList(),
    );

    if (!mounted) return;

    setState(() {
      _isSaving = false;
      if (!success) {
        _optimisticGrants = previousGrants;
        _errorMessage = 'Backend rejected grant update for $capabilityId.';
      }
    });

    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to update grant. Reverted $capabilityId.'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final state = AppStateScope.of(context);
    final isAdmin = state.isAdmin;

    if (_loadingUsers) {
      return Container(
        padding: const EdgeInsets.all(UriSpace.md),
        decoration: BoxDecoration(
          color: colors.surfaceSunken,
          borderRadius: BorderRadius.circular(UriRadius.sm),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline_rounded, size: 16, color: colors.inkFaint),
            const SizedBox(width: UriSpace.sm),
            Expanded(
              child: Text(
                'Loading user accounts…',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: colors.inkSoft),
              ),
            ),
          ],
        ),
      );
    }

    if (_users.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(UriSpace.lg),
        decoration: BoxDecoration(
          color: colors.surface,
          borderRadius: BorderRadius.circular(UriRadius.md),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'No Accounts Found',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(color: colors.ink),
            ),
            const SizedBox(height: UriSpace.xs),
            Text(
              'No registered user accounts are currently available to configure.',
              style: TextStyle(color: colors.inkSoft),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!isAdmin) ...[
          Container(
            padding: const EdgeInsets.all(UriSpace.md),
            margin: const EdgeInsets.only(bottom: UriSpace.md),
            decoration: BoxDecoration(
              color: Colors.amber.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(UriRadius.md),
              border: Border.all(color: Colors.amber.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.lock_outline_rounded, color: Colors.amber),
                const SizedBox(width: UriSpace.sm),
                Expanded(
                  child: Text(
                    'Read-only view: Administrative privileges required to alter grants.',
                    style: TextStyle(color: colors.ink),
                  ),
                ),
              ],
            ),
          ),
        ],
        if (_errorMessage != null) ...[
          Container(
            padding: const EdgeInsets.all(UriSpace.md),
            margin: const EdgeInsets.only(bottom: UriSpace.md),
            decoration: BoxDecoration(
              color: Colors.red.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(UriRadius.md),
              border: Border.all(color: Colors.red.withValues(alpha: 0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded, color: Colors.redAccent),
                const SizedBox(width: UriSpace.sm),
                Expanded(
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(color: Colors.redAccent),
                  ),
                ),
              ],
            ),
          ),
        ],
        Container(
          padding: const EdgeInsets.all(UriSpace.md),
          decoration: BoxDecoration(
            color: colors.surface,
            borderRadius: BorderRadius.circular(UriRadius.md),
            border: Border.all(color: colors.border),
          ),
          child: Row(
            children: [
              const Icon(Icons.account_circle_outlined),
              const SizedBox(width: UriSpace.md),
              Expanded(
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedUserId,
                    isExpanded: true,
                    items: [
                      for (final u in _users)
                        DropdownMenuItem<String>(
                          value: u.userId,
                          child: Row(
                            children: [
                              Text(
                                u.username.isNotEmpty ? u.username : u.userId,
                                style: TextStyle(fontWeight: FontWeight.w600, color: colors.ink),
                              ),
                              const SizedBox(width: UriSpace.sm),
                              StatusPill(
                                label: u.role,
                                foreground: u.role == 'ADMIN' ? colors.accentInk : colors.inkSoft,
                                background: u.role == 'ADMIN' ? colors.accentSoft : colors.surfaceSunken,
                              ),
                              const SizedBox(width: UriSpace.sm),
                              Text(
                                '(${u.userId})',
                                style: TextStyle(
                                  color: colors.inkFaint,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                    onChanged: (newId) {
                      if (newId != null && newId != _selectedUserId) {
                        setState(() => _selectedUserId = newId);
                        _loadGrantsForUser(newId);
                      }
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: UriSpace.lg),
        if (_loadingGrants) ...[
          Container(
            padding: const EdgeInsets.all(UriSpace.md),
            decoration: BoxDecoration(
              color: colors.surfaceSunken,
              borderRadius: BorderRadius.circular(UriRadius.sm),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline_rounded, size: 16, color: colors.inkFaint),
                const SizedBox(width: UriSpace.sm),
                Expanded(
                  child: Text(
                    'Loading capability grants…',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: colors.inkSoft),
                  ),
                ),
              ],
            ),
          ),
        ] else if (_grantsInfo != null) ...[
          _GrantsList(
            grantsInfo: _grantsInfo!,
            optimisticGrants: _optimisticGrants,
            isAdmin: isAdmin,
            onToggle: _toggleGrant,
          ),
        ],
      ],
    );
  }
}

class _GrantsList extends StatelessWidget {
  const _GrantsList({
    required this.grantsInfo,
    required this.optimisticGrants,
    required this.isAdmin,
    required this.onToggle,
  });

  final UserGrantsInfo grantsInfo;
  final Set<String> optimisticGrants;
  final bool isAdmin;
  final void Function(String capId, bool enable) onToggle;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    final ceiling = List<String>.from(grantsInfo.registryCeiling)..sort();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: UriSpace.sm),
          child: Text(
            'Capabilities (${optimisticGrants.length}/${ceiling.length} Granted)',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: colors.inkSoft,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ),
        Material(
          color: colors.surface,
          borderRadius: BorderRadius.circular(UriRadius.md),
          clipBehavior: Clip.antiAlias,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(UriRadius.md),
              border: Border.all(color: colors.border),
            ),
            child: ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: ceiling.length,
            separatorBuilder: (_, _) => Divider(color: colors.border, height: 1),
            itemBuilder: (context, index) {
              final capId = ceiling[index];
              final isGranted = optimisticGrants.contains(capId);

              return SwitchListTile(
                title: Text(
                  humanizeIdentifier(capId),
                  style: TextStyle(fontWeight: FontWeight.w500, color: colors.ink),
                ),
                subtitle: Text(
                  capId,
                  style: TextStyle(color: colors.inkFaint, fontSize: 12),
                ),
                value: isGranted,
                activeThumbColor: colors.accent,
                onChanged: isAdmin ? (val) => onToggle(capId, val) : null,
              );
            },
          ),
        ),
      ),
    ],
  );
  }
}

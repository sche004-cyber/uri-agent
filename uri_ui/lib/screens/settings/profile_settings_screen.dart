import 'package:flutter/material.dart';

import '../../services/app_state_scope.dart';
import '../../theme/uri_theme.dart';

/// Who is signed in, and this install's durable identity (see
/// GET /identity) — real values only; nothing here is a placeholder
/// field waiting for a feature that doesn't exist yet.
class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = AppStateScope.of(context);
      if (!state.hasLoadedIdentity) state.loadIdentity();
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: AppStateScope.of(context),
      builder: (context, _) {
        final state = AppStateScope.of(context);
        final colors = UriColors.of(context);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Row(
              icon: Icons.person_outline_rounded,
              trailing: TextButton(onPressed: state.logout, child: const Text('Log out')),
              child: Text(
                state.currentUsername != null
                    ? 'Signed in as ${state.currentUsername}'
                    : 'Not signed in',
                style: Theme.of(context).textTheme.bodyMedium,
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
          ],
        );
      },
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
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

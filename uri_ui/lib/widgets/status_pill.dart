import 'package:flutter/material.dart';

import '../models/connection.dart';
import '../models/uri_turn.dart';
import '../theme/uri_theme.dart';

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.foreground, required this.background});

  final String label;
  final Color foreground;
  final Color background;

  factory StatusPill.forConnection(ConnectionStatus status) {
    switch (status) {
      case ConnectionStatus.connected:
        return const StatusPill(
          label: 'Connected',
          foreground: UriColors.success,
          background: UriColors.successSoft,
        );
      case ConnectionStatus.needsAuthorization:
        return const StatusPill(
          label: 'Needs authorization',
          foreground: UriColors.warning,
          background: UriColors.warningSoft,
        );
      case ConnectionStatus.notConnected:
        return const StatusPill(
          label: 'Not connected',
          foreground: UriColors.inkFaint,
          background: UriColors.surfaceSunken,
        );
    }
  }

  factory StatusPill.forStage(TurnStage stage) {
    switch (stage) {
      case TurnStage.understanding:
        return const StatusPill(label: 'Understanding', foreground: UriColors.inkFaint, background: UriColors.surfaceSunken);
      case TurnStage.proposalReady:
      case TurnStage.awaitingApproval:
        return const StatusPill(label: 'Awaiting your approval', foreground: UriColors.warning, background: UriColors.warningSoft);
      case TurnStage.executing:
        return const StatusPill(label: 'Executing', foreground: UriColors.accentInk, background: UriColors.accentSoft);
      case TurnStage.completed:
        return const StatusPill(label: 'Completed', foreground: UriColors.success, background: UriColors.successSoft);
      case TurnStage.cancelled:
        return const StatusPill(label: 'Cancelled', foreground: UriColors.inkFaint, background: UriColors.surfaceSunken);
      case TurnStage.needsConnection:
        return const StatusPill(label: 'Needs connection', foreground: UriColors.warning, background: UriColors.warningSoft);
      case TurnStage.failed:
        return const StatusPill(label: 'Failed', foreground: UriColors.danger, background: UriColors.dangerSoft);
    }
  }

  factory StatusPill.forImpact(ActionImpact impact) {
    switch (impact) {
      case ActionImpact.routine:
        return const StatusPill(label: 'Routine', foreground: UriColors.inkFaint, background: UriColors.surfaceSunken);
      case ActionImpact.notable:
        return const StatusPill(label: 'Notable', foreground: UriColors.accentInk, background: UriColors.accentSoft);
      case ActionImpact.sensitive:
        return const StatusPill(label: 'Sensitive', foreground: UriColors.warning, background: UriColors.warningSoft);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(999)),
      child: Text(
        label,
        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: foreground),
      ),
    );
  }
}

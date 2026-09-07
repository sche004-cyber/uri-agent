import 'package:flutter/material.dart';

import '../models/connection.dart';
import '../models/uri_turn.dart';
import '../theme/uri_theme.dart';

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.foreground, required this.background});

  final String label;
  final Color foreground;
  final Color background;

  factory StatusPill.forConnection(BuildContext context, ConnectionStatus status) {
    final colors = UriColors.of(context);
    switch (status) {
      case ConnectionStatus.connected:
        return StatusPill(
          label: 'Connected',
          foreground: colors.success,
          background: colors.successSoft,
        );
      case ConnectionStatus.needsAuthorization:
        return StatusPill(
          label: 'Needs authorization',
          foreground: colors.warning,
          background: colors.warningSoft,
        );
      case ConnectionStatus.notConnected:
        return StatusPill(
          label: 'Not connected',
          foreground: colors.inkFaint,
          background: colors.surfaceSunken,
        );
    }
  }

  factory StatusPill.forStage(BuildContext context, TurnStage stage) {
    final colors = UriColors.of(context);
    switch (stage) {
      case TurnStage.understanding:
        return StatusPill(label: 'Understanding', foreground: colors.inkFaint, background: colors.surfaceSunken);
      case TurnStage.proposalReady:
      case TurnStage.awaitingApproval:
        return StatusPill(label: 'Awaiting your approval', foreground: colors.warning, background: colors.warningSoft);
      case TurnStage.executing:
        return StatusPill(label: 'Executing', foreground: colors.accentInk, background: colors.accentSoft);
      case TurnStage.completed:
        return StatusPill(label: 'Completed', foreground: colors.success, background: colors.successSoft);
      case TurnStage.cancelled:
        return StatusPill(label: 'Cancelled', foreground: colors.inkFaint, background: colors.surfaceSunken);
      case TurnStage.needsConnection:
        return StatusPill(label: 'Needs connection', foreground: colors.warning, background: colors.warningSoft);
      case TurnStage.failed:
        return StatusPill(label: 'Failed', foreground: colors.danger, background: colors.dangerSoft);
    }
  }

  factory StatusPill.forImpact(BuildContext context, ActionImpact impact) {
    final colors = UriColors.of(context);
    switch (impact) {
      case ActionImpact.routine:
        return StatusPill(label: 'Routine', foreground: colors.inkFaint, background: colors.surfaceSunken);
      case ActionImpact.notable:
        return StatusPill(label: 'Notable', foreground: colors.accentInk, background: colors.accentSoft);
      case ActionImpact.sensitive:
        return StatusPill(label: 'Sensitive', foreground: colors.warning, background: colors.warningSoft);
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

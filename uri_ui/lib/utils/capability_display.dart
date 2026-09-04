import '../models/uri_turn.dart';

/// Turns a raw snake_case capability/tool identifier (e.g.
/// "draft_institutional_note") into a human-readable label ("Draft
/// Institutional Note") for display. A pure string transform only -
/// it never changes what capability is actually being referred to,
/// only how its name is shown.
String humanizeIdentifier(String raw) {
  if (raw.isEmpty) return raw;

  return raw
      .split('_')
      .where((word) => word.isNotEmpty)
      .map((word) => word[0].toUpperCase() + word.substring(1))
      .join(' ');
}

/// Maps the capability registry's risk vocabulary (see
/// capability_registry.py: "controlled"/"low"/"variable"/"high"/
/// "unknown") onto [ActionImpact]. Every value this is ever called
/// with comes from a proposal that already required explicit
/// approval by definition - so [ActionImpact.routine] is never
/// produced here, even for "controlled"/"low" risk, since showing
/// "Routine" would undersell exactly why the user is being asked at
/// all. Used by both the Ask URI proposal flow
/// (http_uri_client.dart) and the Tasks screen (tasks_screen.dart) -
/// one shared mapping so they can never visually disagree.
ActionImpact impactFromRisk(String? risk) {
  switch (risk) {
    case 'controlled':
    case 'low':
    case 'variable':
      return ActionImpact.notable;
    case 'high':
    default:
      return ActionImpact.sensitive;
  }
}

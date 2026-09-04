/// How much URI should do on its own before asking for a human decision.
enum AutonomyLevel {
  /// URI proposes; a human approves every action before execution.
  askEveryTime,

  /// URI proposes and auto-approves routine, low-impact actions but
  /// still asks before anything notable or sensitive.
  routineAutoApprove,
}

/// Preferred tone for URI's responses and drafts.
enum CommunicationStyle { formal, concise, conversational }

/// The small set of onboarding answers that materially change URI's
/// behaviour. Deliberately short — no unrelated profile questions.
class UserPreferences {
  const UserPreferences({
    required this.focusAreas,
    required this.communicationStyle,
    required this.autonomyLevel,
    required this.completedOnboarding,
  });

  const UserPreferences.initial()
    : focusAreas = const <String>[],
      communicationStyle = CommunicationStyle.concise,
      autonomyLevel = AutonomyLevel.askEveryTime,
      completedOnboarding = false;

  final List<String> focusAreas;
  final CommunicationStyle communicationStyle;
  final AutonomyLevel autonomyLevel;
  final bool completedOnboarding;

  UserPreferences copyWith({
    List<String>? focusAreas,
    CommunicationStyle? communicationStyle,
    AutonomyLevel? autonomyLevel,
    bool? completedOnboarding,
  }) {
    return UserPreferences(
      focusAreas: focusAreas ?? this.focusAreas,
      communicationStyle: communicationStyle ?? this.communicationStyle,
      autonomyLevel: autonomyLevel ?? this.autonomyLevel,
      completedOnboarding: completedOnboarding ?? this.completedOnboarding,
    );
  }
}

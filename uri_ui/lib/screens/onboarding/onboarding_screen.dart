import 'package:flutter/material.dart';

import '../../models/user_preferences.dart';
import '../../theme/uri_theme.dart';
import '../../widgets/uri_wordmark.dart';

/// A short first-run flow. Every question here is meant to change how
/// URI actually behaves (what it looks for, how it phrases things, how
/// much it does unprompted) — nothing is a decorative profile field.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key, required this.onComplete});

  final ValueChanged<UserPreferences> onComplete;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

const _focusOptions = <String>[
  'Email & correspondence',
  'Document drafting',
  'Scheduling & meetings',
  'Records & data lookups',
  'Approvals & compliance',
];

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _step = 0;
  final Set<String> _focusAreas = {};
  CommunicationStyle _style = CommunicationStyle.concise;
  AutonomyLevel _autonomy = AutonomyLevel.askEveryTime;

  static const _totalSteps = 3;

  void _next() {
    if (_step < _totalSteps - 1) {
      setState(() => _step++);
    } else {
      widget.onComplete(
        UserPreferences(
          focusAreas: _focusAreas.toList(),
          communicationStyle: _style,
          autonomyLevel: _autonomy,
          completedOnboarding: true,
        ),
      );
    }
  }

  void _back() => setState(() => _step = (_step - 1).clamp(0, _totalSteps - 1));

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Scaffold(
      backgroundColor: colors.canvas,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Padding(
              padding: const EdgeInsets.all(UriSpace.xl),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const UriWordmark(markSize: 40, showTagline: true),
                  const SizedBox(height: UriSpace.lg),
                  Row(
                    children: [
                      for (var i = 0; i < _totalSteps; i++) ...[
                        if (i > 0) const SizedBox(width: 6),
                        Expanded(
                          child: Container(
                            height: 4,
                            decoration: BoxDecoration(
                              color: i <= _step ? colors.accent : colors.border,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: UriSpace.xl),
                  _buildStep(context),
                  const SizedBox(height: UriSpace.xl),
                  Row(
                    children: [
                      if (_step > 0)
                        TextButton(onPressed: _back, child: const Text('Back')),
                      const Spacer(),
                      ElevatedButton(
                        onPressed: _next,
                        child: Text(_step == _totalSteps - 1 ? 'Get started' : 'Continue'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStep(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    switch (_step) {
      case 0:
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('What kind of work do you want help with?', style: theme.textTheme.headlineMedium),
              const SizedBox(height: UriSpace.xs),
              Text(
                'This shapes what URI pays attention to first — pick as many as apply. '
                'It will still try to help with anything else you ask.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: UriSpace.lg),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final option in _focusOptions)
                    FilterChip(
                      label: Text(option),
                      selected: _focusAreas.contains(option),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _focusAreas.add(option);
                          } else {
                            _focusAreas.remove(option);
                          }
                        });
                      },
                      showCheckmark: false,
                      selectedColor: colors.accentSoft,
                      labelStyle: TextStyle(
                        color: _focusAreas.contains(option) ? colors.accentInk : colors.inkSoft,
                        fontWeight: FontWeight.w600,
                      ),
                      side: BorderSide(
                        color: _focusAreas.contains(option) ? colors.accent : colors.border,
                      ),
                      backgroundColor: colors.surface,
                    ),
                ],
              ),
            ],
          ),
        );
      case 1:
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('How should URI talk to you?', style: theme.textTheme.headlineMedium),
              const SizedBox(height: UriSpace.xs),
              Text('This changes the tone of drafts and replies URI prepares.', style: theme.textTheme.bodyLarge),
              const SizedBox(height: UriSpace.lg),
              _ChoiceTile(
                title: 'Formal',
                subtitle: 'Institutional, precise language for official communication.',
                selected: _style == CommunicationStyle.formal,
                onTap: () => setState(() => _style = CommunicationStyle.formal),
              ),
              _ChoiceTile(
                title: 'Concise',
                subtitle: 'Short and to the point, with detail only when it matters.',
                selected: _style == CommunicationStyle.concise,
                onTap: () => setState(() => _style = CommunicationStyle.concise),
              ),
              _ChoiceTile(
                title: 'Conversational',
                subtitle: 'Natural and approachable, still professional.',
                selected: _style == CommunicationStyle.conversational,
                onTap: () => setState(() => _style = CommunicationStyle.conversational),
              ),
            ],
          ),
        );
      case 2:
      default:
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('How much should URI decide on its own?', style: theme.textTheme.headlineMedium),
              const SizedBox(height: UriSpace.xs),
              Text(
                'URI never acts on anything sensitive without asking first. '
                'This only controls routine, low-impact actions.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: UriSpace.lg),
              _ChoiceTile(
                title: 'Ask me every time',
                subtitle: 'Every proposed action waits for your explicit approval.',
                selected: _autonomy == AutonomyLevel.askEveryTime,
                onTap: () => setState(() => _autonomy = AutonomyLevel.askEveryTime),
              ),
              _ChoiceTile(
                title: 'Auto-approve routine work',
                subtitle: 'URI proceeds on its own for routine, low-impact actions; '
                    'anything notable or sensitive still comes to you first.',
                selected: _autonomy == AutonomyLevel.routineAutoApprove,
                onTap: () => setState(() => _autonomy = AutonomyLevel.routineAutoApprove),
              ),
            ],
          ),
        );
    }
  }
}

class _ChoiceTile extends StatelessWidget {
  const _ChoiceTile({
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = UriColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: UriSpace.sm),
      child: Material(
        color: selected ? colors.accentSoft : colors.surface,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(UriRadius.sm),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(UriSpace.md),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(UriRadius.sm),
              border: Border.all(color: selected ? colors.accent : colors.border),
            ),
            child: Row(
              children: [
                Icon(
                  selected ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                  size: 20,
                  color: selected ? colors.accentInk : colors.inkFaint,
                ),
                const SizedBox(width: UriSpace.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 2),
                      Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

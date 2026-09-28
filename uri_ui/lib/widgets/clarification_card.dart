// M33.3-R S12: inline reference-clarification card (fixture-backed).
//
// Structure follows the existing inline decision card in the conversation
// stream (TurnCard's _ProposalBlock): one bordered block with the question,
// the grounded choices, and the escape path. A candidate tap emits the
// candidate_id + fingerprint, an attribute chip emits its a* option key,
// and "None of these / Enter something else" opens a free-input field whose
// text becomes the authoritative clarification. Once answered, the card
// locks so the same round cannot be answered twice.

import 'package:flutter/material.dart';

import '../models/clarification.dart';
import '../theme/uri_theme.dart';

typedef ClarificationResponder = void Function(ClarificationResponsePayload payload);

class ClarificationCard extends StatefulWidget {
  const ClarificationCard({super.key, required this.request, required this.onRespond});

  final ClarificationRequest request;
  final ClarificationResponder onRespond;

  @override
  State<ClarificationCard> createState() => _ClarificationCardState();
}

class _ClarificationCardState extends State<ClarificationCard> {
  late final TextEditingController _controller = TextEditingController();
  late bool _freeInputOpen = widget.request.kind == ClarificationKind.freeInputOnly;
  String? _answeredLabel;

  @override
  void didUpdateWidget(covariant ClarificationCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.request.ambiguityId != widget.request.ambiguityId) {
      _controller.clear();
      _answeredLabel = null;
      _freeInputOpen = widget.request.kind == ClarificationKind.freeInputOnly;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _emit(ClarificationResponsePayload payload, String shown) {
    if (_answeredLabel != null) return; // one answer per round
    setState(() => _answeredLabel = shown);
    widget.onRespond(payload);
  }

  void _submitFreeInput() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _emit(ClarificationResponsePayload.freeInput(widget.request, text), text);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);
    final request = widget.request;
    final answered = _answeredLabel != null;

    return Container(
      key: const Key('clarification-card'),
      width: double.infinity,
      padding: const EdgeInsets.all(UriSpace.md),
      decoration: BoxDecoration(
        color: colors.accentSoft,
        borderRadius: BorderRadius.circular(UriRadius.sm),
        border: Border.all(color: colors.accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.help_outline_rounded, size: 16, color: colors.accentInk),
              const SizedBox(width: UriSpace.xs),
              Flexible(
                child: Text(
                  'Which one?',
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelLarge?.copyWith(color: colors.accentInk),
                ),
              ),
            ],
          ),
          const SizedBox(height: UriSpace.sm),
          Text(request.question, style: theme.textTheme.bodyLarge),
          const SizedBox(height: UriSpace.sm),
          if (answered)
            Text(
              'Using: $_answeredLabel',
              key: const Key('clarification-answered'),
              style: theme.textTheme.labelLarge?.copyWith(color: colors.accentInk),
            )
          else ...[
            for (final option in request.options)
              Padding(
                padding: const EdgeInsets.only(bottom: UriSpace.xs),
                child: SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    key: Key('clarification-option-${option.optionKey}'),
                    style: OutlinedButton.styleFrom(alignment: Alignment.centerLeft),
                    onPressed: () =>
                        _emit(ClarificationResponsePayload.candidate(request, option), option.label),
                    child: Text(option.label, maxLines: 2, overflow: TextOverflow.ellipsis),
                  ),
                ),
              ),
            if (request.attributeFilters.isNotEmpty) ...[
              Text(
                'Filter by ${request.attributeAxis ?? 'attribute'}',
                style: theme.textTheme.labelSmall,
              ),
              const SizedBox(height: UriSpace.xs),
              Wrap(
                spacing: UriSpace.sm,
                runSpacing: UriSpace.xs,
                children: [
                  for (final filter in request.attributeFilters)
                    ActionChip(
                      key: Key('clarification-filter-${filter.optionKey}'),
                      label: Text(filter.label),
                      onPressed: () =>
                          _emit(ClarificationResponsePayload.attribute(request, filter), filter.label),
                    ),
                ],
              ),
              const SizedBox(height: UriSpace.xs),
            ],
            if (request.kind != ClarificationKind.freeInputOnly)
              TextButton(
                key: const Key('clarification-escape'),
                onPressed: () => setState(() => _freeInputOpen = true),
                child: Text(request.escapeLabel),
              ),
            if (_freeInputOpen)
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('clarification-free-input'),
                      controller: _controller,
                      autofocus: request.kind != ClarificationKind.freeInputOnly,
                      decoration: const InputDecoration(hintText: 'Describe what you mean'),
                      onSubmitted: (_) => _submitFreeInput(),
                    ),
                  ),
                  const SizedBox(width: UriSpace.sm),
                  ElevatedButton(
                    key: const Key('clarification-free-input-submit'),
                    onPressed: _submitFreeInput,
                    child: const Text('Use this'),
                  ),
                ],
              ),
          ],
        ],
      ),
    );
  }
}

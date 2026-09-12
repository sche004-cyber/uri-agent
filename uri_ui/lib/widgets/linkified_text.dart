import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Renders [text] with any markdown link (`[title](https://...)`) or
/// bare URL turned into a tappable, accent-colored, underlined span
/// that opens in the system's default browser - everything else stays
/// plain text in [style]. Used for a Brain-authored narrative/result
/// summary that may mention a source inline, so the User can actually
/// follow it rather than only ever seeing a URL as inert text.
class LinkifiedText extends StatelessWidget {
  const LinkifiedText(this.text, {super.key, this.style});

  final String text;
  final TextStyle? style;

  static final RegExp _pattern = RegExp(
    r'\[([^\]]+)\]\((https?://[^\s)]+)\)|(https?://[^\s<>"\]\)]+)',
  );

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final baseStyle = style ?? DefaultTextStyle.of(context).style;
    final linkStyle = baseStyle.copyWith(
      color: colors.primary,
      decoration: TextDecoration.underline,
    );

    final spans = <InlineSpan>[];
    var cursor = 0;

    for (final match in _pattern.allMatches(text)) {
      if (match.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, match.start)));
      }
      final markdownLabel = match.group(1);
      final url = match.group(2) ?? match.group(3)!;
      spans.add(
        TextSpan(
          text: markdownLabel ?? url,
          style: linkStyle,
          recognizer: TapGestureRecognizer()
            ..onTap = () => launchUrl(
              Uri.parse(url),
              mode: LaunchMode.externalApplication,
            ),
        ),
      );
      cursor = match.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }

    if (spans.length == 1 && spans.first is TextSpan && (spans.first as TextSpan).recognizer == null) {
      // No links found - render as plain Text (identical to before).
      return Text(text, style: baseStyle);
    }

    return Text.rich(TextSpan(style: baseStyle, children: spans));
  }
}

/// One clickable "• Title — url" source row, replacing the previous
/// plain-text rendering - opens [url] in the system's default browser.
class SourceLink extends StatelessWidget {
  const SourceLink({super.key, required this.title, required this.url, this.style});

  final String title;
  final String url;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final baseStyle = style ?? DefaultTextStyle.of(context).style;
    return InkWell(
      onTap: () => launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 1),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('• $title — ', style: baseStyle),
            Flexible(
              child: Text(
                url,
                style: baseStyle.copyWith(
                  color: colors.primary,
                  decoration: TextDecoration.underline,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(left: 4),
              child: Icon(Icons.open_in_new_rounded, size: 12, color: colors.primary),
            ),
          ],
        ),
      ),
    );
  }
}

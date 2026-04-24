import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../shared/models/message.dart';

class MessageBubble extends StatelessWidget {
  final Message message;
  const MessageBubble({super.key, required this.message});

  bool get _isUser => message.role == 'user';

  static final _urlRegex = RegExp(
    r'https?://[^\s\)]+',
    caseSensitive: false,
  );

  /// Build a RichText with clickable links
  Widget _buildContent(Color textColor) {
    final text = message.content;
    final matches = _urlRegex.allMatches(text).toList();

    if (matches.isEmpty) {
      return Text(text, style: TextStyle(color: textColor, fontSize: 15));
    }

    final spans = <InlineSpan>[];
    int lastEnd = 0;

    for (final match in matches) {
      // Text before URL
      if (match.start > lastEnd) {
        spans.add(TextSpan(
          text: text.substring(lastEnd, match.start),
          style: TextStyle(color: textColor, fontSize: 15),
        ));
      }

      // The URL — clickable
      final url = match.group(0)!;
      // Show a friendly label for known actions
      String label = url;
      if (url.contains('/connect/google')) {
        label = '🔗 Conectar Google';
      } else if (url.contains('/connect/')) {
        final name = url.split('/connect/').last.split('?').first;
        label = '🔗 Conectar $name';
      }

      spans.add(TextSpan(
        text: label,
        style: TextStyle(
          color: const Color(0xFF00B4D8),
          fontSize: 15,
          fontWeight: FontWeight.w600,
          decoration: TextDecoration.underline,
          decorationColor: const Color(0xFF00B4D8),
        ),
        recognizer: TapGestureRecognizer()
          ..onTap = () async {
            final uri = Uri.parse(url);
            if (await canLaunchUrl(uri)) {
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            }
          },
      ));

      lastEnd = match.end;
    }

    // Text after last URL
    if (lastEnd < text.length) {
      spans.add(TextSpan(
        text: text.substring(lastEnd),
        style: TextStyle(color: textColor, fontSize: 15),
      ));
    }

    return RichText(text: TextSpan(children: spans));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textColor = _isUser ? Colors.black : Colors.white;

    return Align(
      alignment: _isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: _isUser
              ? theme.colorScheme.primary
              : const Color(0xFF16213E),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(_isUser ? 16 : 4),
            bottomRight: Radius.circular(_isUser ? 4 : 16),
          ),
        ),
        child: _buildContent(textColor),
      ),
    );
  }
}

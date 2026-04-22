import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobius_app/features/chat/chat_screen.dart';
import 'package:mobius_app/features/chat/chat_provider.dart';
import 'package:mobius_app/features/settings/settings_provider.dart';
import 'package:mobius_app/shared/models/message.dart';

void main() {
  testWidgets('Claude chip is disabled when no Claude API key is set', (tester) async {
    final container = ProviderContainer(
      overrides: [
        settingsNotifierProvider.overrideWith(() => _NoClaudeKeySettings()),
        chatNotifierProvider.overrideWith(() => _EmptyChatNotifier()),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: ChatScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final claudeChip = find.widgetWithText(FilterChip, 'claude-sonnet');
    expect(claudeChip, findsOneWidget);
    final chip = tester.widget<FilterChip>(claudeChip);
    expect(chip.onSelected, isNull); // disabled
  });

  testWidgets('Gemini chip is enabled when selected model', (tester) async {
    final container = ProviderContainer(
      overrides: [
        settingsNotifierProvider.overrideWith(() => _NoClaudeKeySettings()),
        chatNotifierProvider.overrideWith(() => _EmptyChatNotifier()),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: ChatScreen()),
      ),
    );
    await tester.pumpAndSettle();

    final geminiChip = find.widgetWithText(FilterChip, 'gemini-flash');
    expect(geminiChip, findsOneWidget);
    final chip = tester.widget<FilterChip>(geminiChip);
    expect(chip.onSelected, isNotNull); // enabled
  });
}

class _NoClaudeKeySettings extends SettingsNotifier {
  @override
  SettingsState build() => const SettingsState(
        apiKeys: {AiModel.geminiFlash: 'some-key'},
      );
}

class _EmptyChatNotifier extends ChatNotifier {
  @override
  Future<List<Message>> build() async => [];
}

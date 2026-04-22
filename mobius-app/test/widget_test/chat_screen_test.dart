import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobius_app/features/chat/chat_screen.dart';
import 'package:mobius_app/features/chat/chat_provider.dart';
import 'package:mobius_app/shared/models/message.dart';

void main() {
  testWidgets('ChatScreen renders message list and send button', (tester) async {
    final messages = [
      Message(role: 'user', content: 'Hello', timestamp: DateTime.now()),
      Message(role: 'assistant', content: 'Hi there!', timestamp: DateTime.now()),
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chatNotifierProvider.overrideWith(() => _FakeChatNotifier(messages)),
        ],
        child: const MaterialApp(home: ChatScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Hello'), findsOneWidget);
    expect(find.text('Hi there!'), findsOneWidget);
    expect(find.byIcon(Icons.send), findsOneWidget);
  });
}

class _FakeChatNotifier extends ChatNotifier {
  final List<Message> _messages;
  _FakeChatNotifier(this._messages);

  @override
  Future<List<Message>> build() async => _messages;
}

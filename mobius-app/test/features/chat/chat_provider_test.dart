import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:mobius_app/features/chat/chat_provider.dart';
import 'package:mobius_app/services/websocket_service.dart';
import 'package:mobius_app/shared/models/message.dart';

import 'chat_provider_test.mocks.dart';

@GenerateMocks([WebSocketService])
void main() {
  late MockWebSocketService mockWs;
  late StreamController<WsEvent> wsController;

  setUp(() {
    wsController = StreamController<WsEvent>.broadcast();
    mockWs = MockWebSocketService();
    when(mockWs.stream).thenAnswer((_) => wsController.stream);
  });

  tearDown(() => wsController.close());

  test('sendMessage appends user message then builds assistant message token by token', () async {
    final container = ProviderContainer(
      overrides: [webSocketServiceProvider.overrideWithValue(mockWs)],
    );

    // Initialize the provider by reading it first and waiting for build() to complete
    await container.read(chatNotifierProvider.future);

    final notifier = container.read(chatNotifierProvider.notifier);

    // Start sendMessage and add tokens then DoneEvent
    final sendFuture = notifier.sendMessage('Hello', 'gemini-flash');

    // Let the first state update (user message + assistant placeholder) propagate
    await Future.delayed(const Duration(milliseconds: 10));
    final msgs1 = container.read(chatNotifierProvider).value ?? [];
    expect(msgs1.any((m) => m.role == 'user' && m.content == 'Hello'), isTrue);

    // Stream tokens and close
    wsController.add(TokenEvent('Hi'));
    wsController.add(TokenEvent(' there'));
    wsController.add(DoneEvent());

    // Wait for sendMessage to finish processing all events
    await sendFuture;

    final msgs2 = container.read(chatNotifierProvider).value ?? [];
    final assistant = msgs2.firstWhere((m) => m.role == 'assistant');
    expect(assistant.content, 'Hi there');
    container.dispose();
  });
}

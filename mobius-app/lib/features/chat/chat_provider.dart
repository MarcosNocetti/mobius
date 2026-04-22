import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/websocket_service.dart';
import '../../shared/models/message.dart';

final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final service = WebSocketService();
  ref.onDispose(service.dispose);
  return service;
});

final isStreamingProvider = StateProvider<bool>((ref) => false);

class ChatNotifier extends AsyncNotifier<List<Message>> {
  @override
  Future<List<Message>> build() async => [];

  Future<void> sendMessage(String text, String model) async {
    final ws = ref.read(webSocketServiceProvider);
    final current = state.value ?? [];

    // Add user message
    final userMsg = Message(role: 'user', content: text, timestamp: DateTime.now());
    state = AsyncValue.data([...current, userMsg]);

    ref.read(isStreamingProvider.notifier).state = true;

    // Placeholder assistant message
    var assistantContent = '';
    final assistantMsg = Message(role: 'assistant', content: '', timestamp: DateTime.now());
    state = AsyncValue.data([...(state.value ?? []), assistantMsg]);

    ws.sendMessage(text, model);

    await for (final event in ws.stream) {
      if (event is TokenEvent) {
        assistantContent += event.content;
        final messages = List<Message>.from(state.value ?? []);
        final lastIndex = messages.length - 1;
        messages[lastIndex] = messages[lastIndex].copyWith(content: assistantContent);
        state = AsyncValue.data(messages);
      } else if (event is DoneEvent) {
        break;
      }
    }

    ref.read(isStreamingProvider.notifier).state = false;
  }
}

final chatNotifierProvider =
    AsyncNotifierProvider<ChatNotifier, List<Message>>(ChatNotifier.new);

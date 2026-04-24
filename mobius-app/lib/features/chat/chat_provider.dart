import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/storage.dart';
import '../../services/websocket_service.dart';
import '../../shared/models/message.dart';
import 'conversation_provider.dart';

final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final service = WebSocketService();
  ref.onDispose(service.dispose);
  return service;
});

final isStreamingProvider = StateProvider<bool>((ref) => false);
final agentStatusProvider = StateProvider<String>((ref) => '');

class ChatNotifier extends AsyncNotifier<List<Message>> {
  bool _connected = false;

  @override
  Future<List<Message>> build() async => [];

  Future<void> _ensureConnected() async {
    if (_connected) return;
    final storage = AppStorage();
    final token = await storage.getToken() ?? '';
    final serverUrl = await storage.getServerUrl();
    // Convert http(s):// to ws(s)://
    final uri = Uri.parse(serverUrl);
    final wsScheme = uri.scheme == 'https' ? 'wss' : 'ws';
    final host = uri.port != 80 && uri.port != 443
        ? '${uri.host}:${uri.port}'
        : uri.host;
    final ws = ref.read(webSocketServiceProvider);
    ws.connect(host, token, scheme: wsScheme);
    _connected = true;
  }

  Future<void> sendMessage(String text, String model) async {
    await _ensureConnected();
    final ws = ref.read(webSocketServiceProvider);
    final current = state.value ?? [];

    final userMsg = Message(role: 'user', content: text, timestamp: DateTime.now());
    state = AsyncValue.data([...current, userMsg]);

    ref.read(isStreamingProvider.notifier).state = true;

    var assistantContent = '';
    final assistantMsg = Message(role: 'assistant', content: '', timestamp: DateTime.now());
    state = AsyncValue.data([...(state.value ?? []), assistantMsg]);

    final convId = ref.read(activeConversationIdProvider);
    ws.sendMessage(text, model, conversationId: convId);

    await for (final event in ws.stream) {
      if (event is TokenEvent) {
        assistantContent += event.content;
        final messages = List<Message>.from(state.value ?? []);
        final lastIndex = messages.length - 1;
        messages[lastIndex] = messages[lastIndex].copyWith(content: assistantContent);
        state = AsyncValue.data(messages);
      } else if (event is StatusEvent) {
        ref.read(agentStatusProvider.notifier).state = event.status;
      } else if (event is ConversationIdEvent) {
        ref.read(activeConversationIdProvider.notifier).state = event.conversationId;
      } else if (event is DoneEvent) {
        break;
      }
    }

    ref.read(isStreamingProvider.notifier).state = false;
    ref.read(agentStatusProvider.notifier).state = '';
  }
}

final chatNotifierProvider =
    AsyncNotifierProvider<ChatNotifier, List<Message>>(ChatNotifier.new);

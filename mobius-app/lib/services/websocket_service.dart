import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

sealed class WsEvent {}

class TokenEvent extends WsEvent {
  final String content;
  TokenEvent(this.content);
}

class DoneEvent extends WsEvent {}

class StatusEvent extends WsEvent {
  final String status;
  StatusEvent(this.status);
}

class ConversationIdEvent extends WsEvent {
  final String conversationId;
  ConversationIdEvent(this.conversationId);
}

typedef ChannelFactory = WebSocketChannel Function(Uri uri);

class WebSocketService {
  WebSocketChannel? _channel;
  final _controller = StreamController<WsEvent>.broadcast();
  final ChannelFactory? channelFactory;
  StreamSubscription? _subscription;

  WebSocketService({this.channelFactory});

  Stream<WsEvent> get stream => _controller.stream;

  void connect(String serverHost, String token, {String scheme = 'ws'}) {
    final uri = Uri.parse('$scheme://$serverHost/ws/chat?token=$token');
    _channel = channelFactory != null
        ? channelFactory!(uri)
        : WebSocketChannel.connect(uri);

    _subscription = _channel!.stream.listen(
      _onData,
      onError: _onError,
      onDone: _onDone,
    );
  }

  void _onData(dynamic raw) {
    try {
      final json = jsonDecode(raw as String) as Map<String, dynamic>;
      if (json['type'] == 'token') {
        _controller.add(TokenEvent(json['content'] as String));
      } else if (json['type'] == 'error') {
        _controller.add(TokenEvent('[Erro] ${json['content']}'));
      } else if (json['type'] == 'status') {
        _controller.add(StatusEvent(json['content'] as String));
      } else if (json['type'] == 'done') {
        _controller.add(DoneEvent());
      } else if (json['type'] == 'conversation_id') {
        _controller.add(ConversationIdEvent(json['content'] as String));
      }
    } catch (_) {}
  }

  void _onError(Object error) {
    // Reconnect logic can be added here (e.g., exponential backoff)
  }

  void _onDone() {
    // Channel closed — could trigger reconnect
  }

  void sendMessage(String message, String model, {String? conversationId}) {
    final payload = <String, dynamic>{'message': message, 'model': model};
    if (conversationId != null) payload['conversation_id'] = conversationId;
    _channel?.sink.add(jsonEncode(payload));
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    await _channel?.sink.close();
  }

  void dispose() {
    disconnect();
    _controller.close();
  }
}

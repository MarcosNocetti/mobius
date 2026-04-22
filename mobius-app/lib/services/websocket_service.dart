import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

sealed class WsEvent {}

class TokenEvent extends WsEvent {
  final String content;
  TokenEvent(this.content);
}

class DoneEvent extends WsEvent {}

typedef ChannelFactory = WebSocketChannel Function(Uri uri);

class WebSocketService {
  WebSocketChannel? _channel;
  final _controller = StreamController<WsEvent>.broadcast();
  final ChannelFactory? channelFactory;
  StreamSubscription? _subscription;

  WebSocketService({this.channelFactory});

  Stream<WsEvent> get stream => _controller.stream;

  void connect(String serverHost, String token) {
    final uri = Uri.parse('ws://$serverHost/ws/chat?token=$token');
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
      } else if (json['type'] == 'done') {
        _controller.add(DoneEvent());
      }
    } catch (_) {}
  }

  void _onError(Object error) {
    // Reconnect logic can be added here (e.g., exponential backoff)
  }

  void _onDone() {
    // Channel closed — could trigger reconnect
  }

  void sendMessage(String message, String model) {
    final payload = jsonEncode({'message': message, 'model': model});
    _channel?.sink.add(payload);
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

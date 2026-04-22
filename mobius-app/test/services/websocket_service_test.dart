import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:mobius_app/services/websocket_service.dart';

import 'websocket_service_test.mocks.dart';

@GenerateMocks([WebSocketChannel, WebSocketSink])
void main() {
  late StreamController<dynamic> incomingController;
  late MockWebSocketChannel mockChannel;
  late MockWebSocketSink mockSink;

  setUp(() {
    incomingController = StreamController<dynamic>.broadcast();
    mockChannel = MockWebSocketChannel();
    mockSink = MockWebSocketSink();
    when(mockChannel.stream).thenAnswer((_) => incomingController.stream);
    when(mockChannel.sink).thenReturn(mockSink);
  });

  tearDown(() => incomingController.close());

  test('stream emits TokenEvent and DoneEvent from raw WS messages', () async {
    final service = WebSocketService(channelFactory: (uri) => mockChannel);
    service.connect('localhost:8000', 'test-token');

    final events = <WsEvent>[];
    final sub = service.stream.listen(events.add);

    incomingController.add(jsonEncode({'type': 'token', 'content': 'Hello'}));
    incomingController.add(jsonEncode({'type': 'token', 'content': ' world'}));
    incomingController.add(jsonEncode({'type': 'done'}));

    await Future.delayed(const Duration(milliseconds: 50));
    await sub.cancel();

    expect(events[0], isA<TokenEvent>());
    expect((events[0] as TokenEvent).content, 'Hello');
    expect(events[1], isA<TokenEvent>());
    expect((events[1] as TokenEvent).content, ' world');
    expect(events[2], isA<DoneEvent>());
  });

  test('sendMessage sends JSON payload over sink', () async {
    final service = WebSocketService(channelFactory: (uri) => mockChannel);
    service.connect('localhost:8000', 'test-token');

    service.sendMessage('Hello AI', 'gemini-flash');

    verify(mockSink.add(argThat(allOf(
      contains('"message":"Hello AI"'),
      contains('"model":"gemini-flash"'),
    )))).called(1);
  });
}

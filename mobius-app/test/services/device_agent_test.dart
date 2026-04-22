import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobius_app/services/device_agent.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late List<MethodCall> log;

  setUp(() {
    log = [];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.mobius/device'),
      (call) async {
        log.add(call);
        return switch (call.method) {
          'openApp' => true,
          'readScreen' => 'Sample screen text',
          'tapElement' => true,
          _ => null,
        };
      },
    );
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('com.mobius/device'),
      null,
    );
  });

  test('openApp calls correct MethodChannel method with package name', () async {
    final agent = DeviceAgent();
    final result = await agent.openApp('com.whatsapp');
    expect(result, isTrue);
    expect(log.length, 1);
    expect(log[0].method, 'openApp');
    expect(log[0].arguments['packageName'], 'com.whatsapp');
  });

  test('readScreen returns string from MethodChannel', () async {
    final agent = DeviceAgent();
    final text = await agent.readScreen();
    expect(text, 'Sample screen text');
  });

  test('tapElement calls correct method with content description', () async {
    final agent = DeviceAgent();
    final result = await agent.tapElement('Submit button');
    expect(result, isTrue);
    expect(log[0].arguments['contentDesc'], 'Submit button');
  });
}

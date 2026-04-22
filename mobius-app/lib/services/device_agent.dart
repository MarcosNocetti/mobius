import 'package:flutter/services.dart';

class DeviceAgent {
  static const _channel = MethodChannel('com.mobius/device');

  Future<bool> openApp(String packageName) async {
    final result = await _channel.invokeMethod<bool>(
      'openApp',
      {'packageName': packageName},
    );
    return result ?? false;
  }

  Future<String> readScreen() async {
    final result = await _channel.invokeMethod<String>('readScreen');
    return result ?? '';
  }

  Future<bool> tapElement(String contentDesc) async {
    final result = await _channel.invokeMethod<bool>(
      'tapElement',
      {'contentDesc': contentDesc},
    );
    return result ?? false;
  }
}

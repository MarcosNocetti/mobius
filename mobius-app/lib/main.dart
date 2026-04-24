import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Debug: test server connectivity on startup
  _testServerConnection();

  runApp(const ProviderScope(child: MobiusApp()));
}

Future<void> _testServerConnection() async {
  const serverUrl = 'https://uptown-stew-viewing.ngrok-free.dev';
  debugPrint('[MOBIUS] Testing connection to $serverUrl ...');
  try {
    final dio = Dio();
    dio.options.headers['ngrok-skip-browser-warning'] = 'true';
    final resp = await dio.get('$serverUrl/health');
    debugPrint('[MOBIUS] Server health: ${resp.statusCode} ${resp.data}');
  } catch (e) {
    debugPrint('[MOBIUS] Server connection FAILED: $e');
  }
}

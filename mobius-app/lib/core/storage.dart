import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AppStorage {
  final FlutterSecureStorage _storage;

  AppStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _tokenKey = 'jwt_token';
  static const _serverUrlKey = 'server_url';
  static const _defaultServerUrl = 'https://uptown-stew-viewing.ngrok-free.dev';

  Future<void> saveToken(String token) =>
      _storage.write(key: _tokenKey, value: token);

  Future<String?> getToken() => _storage.read(key: _tokenKey);

  Future<void> deleteToken() => _storage.delete(key: _tokenKey);

  Future<void> saveServerUrl(String url) =>
      _storage.write(key: _serverUrlKey, value: url);

  Future<String> getServerUrl() async {
    final url = await _storage.read(key: _serverUrlKey);
    return url ?? _defaultServerUrl;
  }
}

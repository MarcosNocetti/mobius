import 'storage.dart';

class AppConfig {
  AppConfig._();
  static final AppConfig instance = AppConfig._();

  final AppStorage _storage = AppStorage();

  Future<String> get serverUrl => _storage.getServerUrl();
  Future<String?> get jwtToken => _storage.getToken();

  Future<void> setServerUrl(String url) => _storage.saveServerUrl(url);
  Future<void> setToken(String token) => _storage.saveToken(token);
  Future<void> clearToken() => _storage.deleteToken();
}

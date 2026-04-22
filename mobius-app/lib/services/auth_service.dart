import '../core/storage.dart';
import 'backend_client.dart';

class AuthService {
  final BackendClient _client;
  final AppStorage _storage;

  AuthService({required BackendClient client, AppStorage? storage})
      : _client = client,
        _storage = storage ?? AppStorage();

  Future<void> register(String email, String password) async {
    await _client.post('/auth/register', data: {
      'email': email,
      'password': password,
    });
    await login(email, password);
  }

  Future<void> login(String email, String password) async {
    final response = await _client.post('/auth/token', data: {
      'email': email,
      'password': password,
    });
    final token = response.data['access_token'] as String;
    await _storage.saveToken(token);
  }

  Future<void> logout() async {
    await _storage.deleteToken();
  }

  Future<bool> isLoggedIn() async {
    final token = await _storage.getToken();
    return token != null && token.isNotEmpty;
  }
}

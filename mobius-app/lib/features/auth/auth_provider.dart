import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/auth_service.dart';
import '../../services/backend_client.dart';

enum AuthState { unknown, authenticated, unauthenticated }

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(client: BackendClient(baseUrl: 'https://api-production-74cf.up.railway.app'));
});

class AuthNotifier extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    final service = ref.read(authServiceProvider);
    final loggedIn = await service.isLoggedIn();
    return loggedIn ? AuthState.authenticated : AuthState.unauthenticated;
  }

  Future<void> register(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await ref.read(authServiceProvider).register(email, password);
      return AuthState.authenticated;
    });
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await ref.read(authServiceProvider).login(email, password);
      return AuthState.authenticated;
    });
  }

  Future<void> logout() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      await ref.read(authServiceProvider).logout();
      return AuthState.unauthenticated;
    });
  }
}

final authNotifierProvider =
    AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

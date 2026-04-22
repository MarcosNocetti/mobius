import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:mobius_app/services/auth_service.dart';
import 'package:mobius_app/features/auth/auth_provider.dart';

import 'auth_provider_test.mocks.dart';

@GenerateMocks([AuthService])
void main() {
  late MockAuthService mockAuthService;

  setUp(() {
    mockAuthService = MockAuthService();
  });

  test('login transitions state to authenticated', () async {
    when(mockAuthService.login('user@test.com', 'password'))
        .thenAnswer((_) async {});
    when(mockAuthService.isLoggedIn()).thenAnswer((_) async => true);

    final container = ProviderContainer(
      overrides: [authServiceProvider.overrideWithValue(mockAuthService)],
    );
    addTearDown(container.dispose);

    await container.read(authNotifierProvider.notifier).login('user@test.com', 'password');

    verify(mockAuthService.login('user@test.com', 'password')).called(1);
    final state = container.read(authNotifierProvider);
    expect(state.value, AuthState.authenticated);
  });

  test('logout transitions state to unauthenticated', () async {
    when(mockAuthService.logout()).thenAnswer((_) async {});
    final container = ProviderContainer(
      overrides: [authServiceProvider.overrideWithValue(mockAuthService)],
    );
    addTearDown(container.dispose);

    await container.read(authNotifierProvider.notifier).logout();

    verify(mockAuthService.logout()).called(1);
    final state = container.read(authNotifierProvider);
    expect(state.value, AuthState.unauthenticated);
  });
}

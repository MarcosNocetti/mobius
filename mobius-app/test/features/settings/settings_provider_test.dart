import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:mobius_app/features/settings/settings_provider.dart';
import 'package:mobius_app/services/backend_client.dart';

import 'settings_provider_test.mocks.dart';

@GenerateMocks([BackendClient])
void main() {
  late MockBackendClient mockClient;

  setUp(() {
    mockClient = MockBackendClient();
  });

  test('testConnection returns true when GET /health returns 200', () async {
    when(mockClient.get('/health')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/health'),
        statusCode: 200,
      ),
    );

    final container = ProviderContainer(
      overrides: [backendClientProvider.overrideWithValue(mockClient)],
    );
    addTearDown(container.dispose);

    final result =
        await container.read(settingsNotifierProvider.notifier).testConnection();
    expect(result, isTrue);
  });

  test('testConnection returns false when GET /health throws', () async {
    when(mockClient.get('/health')).thenThrow(Exception('unreachable'));

    final container = ProviderContainer(
      overrides: [backendClientProvider.overrideWithValue(mockClient)],
    );
    addTearDown(container.dispose);

    final result =
        await container.read(settingsNotifierProvider.notifier).testConnection();
    expect(result, isFalse);
  });
}

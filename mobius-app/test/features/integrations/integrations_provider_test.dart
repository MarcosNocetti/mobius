import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:mobius_app/features/integrations/integrations_provider.dart';
import 'package:mobius_app/features/settings/settings_provider.dart';
import 'package:mobius_app/services/backend_client.dart';

import 'integrations_provider_test.mocks.dart';

@GenerateMocks([BackendClient])
void main() {
  late MockBackendClient mockClient;

  setUp(() {
    mockClient = MockBackendClient();
  });

  test('fetches integration status and maps to IntegrationStatus list', () async {
    when(mockClient.get('/integrations/status')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/integrations/status'),
        statusCode: 200,
        data: {
          'google': true,
          'notion': false,
          'instagram': false,
          'twitter': true,
          'linkedin': false,
        },
      ),
    );

    final container = ProviderContainer(
      overrides: [backendClientProvider.overrideWithValue(mockClient)],
    );
    addTearDown(container.dispose);

    final result = await container.read(integrationsProvider.future);
    expect(result.where((i) => i.connected).length, 2);
    expect(result.where((i) => !i.connected).length, 3);
  });
}

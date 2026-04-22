import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:mobius_app/features/automations/automations_provider.dart';
import 'package:mobius_app/features/settings/settings_provider.dart';
import 'package:mobius_app/services/backend_client.dart';
import 'package:mobius_app/shared/models/automation.dart';

import 'automations_provider_test.mocks.dart';

@GenerateMocks([BackendClient])
void main() {
  late MockBackendClient mockClient;

  setUp(() {
    mockClient = MockBackendClient();
  });

  test('loads automations from GET /automations', () async {
    when(mockClient.get('/automations')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/automations'),
        statusCode: 200,
        data: [
          {
            'id': '1',
            'prompt': 'Post daily summary',
            'cron_expr': '0 9 * * *',
            'active': true,
            'last_run': null,
          },
          {
            'id': '2',
            'prompt': 'Check emails',
            'cron_expr': '0 * * * *',
            'active': false,
            'last_run': '2026-04-20T09:00:00Z',
          },
        ],
      ),
    );

    final container = ProviderContainer(
      overrides: [backendClientProvider.overrideWithValue(mockClient)],
    );
    addTearDown(container.dispose);

    final automations = await container.read(automationsProvider.future);
    expect(automations.length, 2);
    expect(automations[0].prompt, 'Post daily summary');
    expect(automations[1].active, isFalse);
  });
}

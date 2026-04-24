import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/settings/settings_provider.dart';

class IntegrationStatus {
  final String name;
  final String displayName;
  final bool connected;
  final String authType;

  const IntegrationStatus({
    required this.name,
    required this.displayName,
    required this.connected,
    required this.authType,
  });

  factory IntegrationStatus.fromJson(Map<String, dynamic> json) => IntegrationStatus(
    name: json['name'] as String,
    displayName: json['display_name'] as String,
    connected: json['connected'] as bool,
    authType: json['auth_type'] as String,
  );
}

final integrationsProvider = FutureProvider<List<IntegrationStatus>>((ref) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/connect/status');
  final data = response.data as Map<String, dynamic>;
  final list = data['integrations'] as List<dynamic>;
  return list.map((e) => IntegrationStatus.fromJson(e as Map<String, dynamic>)).toList();
});

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/settings/settings_provider.dart';

class IntegrationStatus {
  final String name;
  final String displayName;
  final bool connected;
  final String oauthPath;

  const IntegrationStatus({
    required this.name,
    required this.displayName,
    required this.connected,
    required this.oauthPath,
  });
}

const _integrationMeta = {
  'google': ('Google', '/oauth/google'),
  'notion': ('Notion', '/oauth/notion'),
  'instagram': ('Instagram', '/oauth/instagram'),
  'twitter': ('Twitter / X', '/oauth/twitter'),
  'linkedin': ('LinkedIn', '/oauth/linkedin'),
};

final integrationsProvider = FutureProvider<List<IntegrationStatus>>((ref) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/integrations/status');
  final data = response.data as Map<String, dynamic>;

  return _integrationMeta.entries.map((entry) {
    final (displayName, oauthPath) = entry.value;
    return IntegrationStatus(
      name: entry.key,
      displayName: displayName,
      connected: (data[entry.key] as bool?) ?? false,
      oauthPath: oauthPath,
    );
  }).toList();
});

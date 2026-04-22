import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../features/settings/settings_provider.dart';
import 'integrations_provider.dart';

class IntegrationsScreen extends ConsumerWidget {
  const IntegrationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final integrationsAsync = ref.watch(integrationsProvider);
    final settings = ref.watch(settingsNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Integrations')),
      body: integrationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (integrations) => ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: integrations.length,
          separatorBuilder: (_, __) => const Divider(),
          itemBuilder: (context, index) {
            final integration = integrations[index];
            return ListTile(
              title: Text(integration.displayName),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Chip(
                    label: Text(
                      integration.connected ? 'Connected' : 'Disconnected',
                      style: TextStyle(
                        color: integration.connected ? Colors.green : Colors.grey,
                        fontSize: 12,
                      ),
                    ),
                    backgroundColor: integration.connected
                        ? Colors.green.withOpacity(0.15)
                        : Colors.grey.withOpacity(0.15),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () async {
                      final url = Uri.parse(
                          '${settings.serverUrl}${integration.oauthPath}');
                      if (await canLaunchUrl(url)) {
                        await launchUrl(url, mode: LaunchMode.externalApplication);
                      }
                    },
                    child: Text(integration.connected ? 'Disconnect' : 'Connect'),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

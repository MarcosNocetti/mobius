import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'settings_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final TextEditingController _serverUrlController;

  @override
  void initState() {
    super.initState();
    final url = ref.read(settingsNotifierProvider).serverUrl;
    _serverUrlController = TextEditingController(text: url);
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    final ok = await ref.read(settingsNotifierProvider.notifier).testConnection();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? 'Connected' : 'Connection failed'),
        backgroundColor: ok ? Colors.green : Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(settingsNotifierProvider);
    final notifier = ref.read(settingsNotifierProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Server', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          TextField(
            controller: _serverUrlController,
            decoration: const InputDecoration(labelText: 'Server URL'),
            onChanged: notifier.setServerUrl,
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: _testConnection,
            child: const Text('Test Connection'),
          ),
          const Divider(height: 32),
          const Text('AI Model', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          DropdownButtonFormField<AiModel>(
            value: settings.selectedModel,
            decoration: const InputDecoration(labelText: 'Default Model'),
            items: AiModel.values
                .map((m) => DropdownMenuItem(value: m, child: Text(m.label)))
                .toList(),
            onChanged: (m) => m != null ? notifier.setModel(m) : null,
          ),
          const Divider(height: 32),
          const Text('API Keys', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ...AiModel.values.map((model) => Padding(
                padding: const EdgeInsets.only(top: 12),
                child: TextField(
                  decoration: InputDecoration(
                    labelText: '${model.label} API Key',
                  ),
                  obscureText: true,
                  onChanged: (key) => notifier.setApiKey(model, key),
                ),
              )),
          const SizedBox(height: 24),
          const Divider(height: 32),
          const Text('Accessibility', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: () {
              // Opens Android accessibility settings; handled by device_agent
            },
            child: const Text('Enable Accessibility Service'),
          ),
        ],
      ),
    );
  }
}

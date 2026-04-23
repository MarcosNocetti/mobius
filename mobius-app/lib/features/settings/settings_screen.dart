import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/backend_client.dart';
import 'settings_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final TextEditingController _serverUrlController;
  final Map<AiModel, TextEditingController> _keyControllers = {};
  final Map<AiModel, bool> _testing = {};

  @override
  void initState() {
    super.initState();
    final url = ref.read(settingsNotifierProvider).serverUrl;
    _serverUrlController = TextEditingController(text: url);
    for (final model in AiModel.values) {
      _keyControllers[model] = TextEditingController();
      _testing[model] = false;
    }
  }

  @override
  void dispose() {
    _serverUrlController.dispose();
    for (final c in _keyControllers.values) {
      c.dispose();
    }
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

  Future<void> _testApiKey(AiModel model) async {
    final key = _keyControllers[model]?.text.trim() ?? '';
    if (key.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cole a API key primeiro'), backgroundColor: Colors.orange),
      );
      return;
    }

    setState(() => _testing[model] = true);

    try {
      final client = ref.read(backendClientProvider);
      final resp = await client.post('/auth/api-keys/test', data: {
        'provider': model.providerKey,
        'key': key,
      });
      if (!mounted) return;
      final success = resp.data['success'] == true;
      final message = success
          ? '✅ ${model.label}: ${resp.data['reply']}'
          : '❌ ${model.label}: ${resp.data['error']}';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message, maxLines: 2, overflow: TextOverflow.ellipsis),
          backgroundColor: success ? Colors.green : Colors.red,
          duration: const Duration(seconds: 4),
        ),
      );

      // Se deu certo, salva a key automaticamente
      if (success) {
        await ref.read(settingsNotifierProvider.notifier).setApiKey(model, key);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro: $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _testing[model] = false);
    }
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
          const SizedBox(height: 4),
          const Text(
            'Cole a key e clique ▶ para testar. Se funcionar, salva automaticamente.',
            style: TextStyle(color: Colors.grey, fontSize: 12),
          ),
          ...AiModel.values.map((model) => Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _keyControllers[model],
                        decoration: InputDecoration(
                          labelText: '${model.label} API Key',
                        ),
                        obscureText: true,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _testing[model] == true
                        ? const SizedBox(
                            width: 36,
                            height: 36,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : IconButton(
                            icon: const Icon(Icons.play_arrow, color: Color(0xFF00B4D8)),
                            tooltip: 'Testar key',
                            onPressed: () => _testApiKey(model),
                          ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

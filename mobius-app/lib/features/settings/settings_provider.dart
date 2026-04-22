import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/storage.dart';
import '../../services/backend_client.dart';

enum AiModel { geminiFlash, claudeSonnet, gpt4o }

extension AiModelLabel on AiModel {
  String get label => switch (this) {
        AiModel.geminiFlash => 'gemini-flash',
        AiModel.claudeSonnet => 'claude-sonnet',
        AiModel.gpt4o => 'gpt-4o',
      };
}

class SettingsState {
  final String serverUrl;
  final AiModel selectedModel;
  final Map<AiModel, String> apiKeys;

  const SettingsState({
    this.serverUrl = 'http://localhost:8000',
    this.selectedModel = AiModel.geminiFlash,
    this.apiKeys = const {},
  });

  SettingsState copyWith({
    String? serverUrl,
    AiModel? selectedModel,
    Map<AiModel, String>? apiKeys,
  }) =>
      SettingsState(
        serverUrl: serverUrl ?? this.serverUrl,
        selectedModel: selectedModel ?? this.selectedModel,
        apiKeys: apiKeys ?? this.apiKeys,
      );
}

final backendClientProvider = Provider<BackendClient>((ref) {
  return BackendClient(baseUrl: 'http://localhost:8000');
});

class SettingsNotifier extends Notifier<SettingsState> {
  @override
  SettingsState build() => const SettingsState();

  Future<void> setServerUrl(String url) async {
    await AppStorage().saveServerUrl(url);
    state = state.copyWith(serverUrl: url);
  }

  void setModel(AiModel model) {
    state = state.copyWith(selectedModel: model);
  }

  void setApiKey(AiModel model, String key) {
    final updated = Map<AiModel, String>.from(state.apiKeys);
    updated[model] = key;
    state = state.copyWith(apiKeys: updated);
  }

  bool hasApiKey(AiModel model) => state.apiKeys.containsKey(model) &&
      state.apiKeys[model]!.isNotEmpty;

  Future<bool> testConnection() async {
    try {
      final client = ref.read(backendClientProvider);
      final response = await client.get('/health');
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

final settingsNotifierProvider =
    NotifierProvider<SettingsNotifier, SettingsState>(SettingsNotifier.new);

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/settings/settings_provider.dart';
import '../../shared/models/automation.dart';

final automationsProvider =
    FutureProvider<List<Automation>>((ref) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/automations');
  final data = response.data as List<dynamic>;
  return data.map((e) => Automation.fromJson(e as Map<String, dynamic>)).toList();
});

final automationProvider =
    FutureProvider.family<Automation, String>((ref, id) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/automations/$id');
  return Automation.fromJson(response.data as Map<String, dynamic>);
});

final automationsNotifierProvider =
    AsyncNotifierProvider<AutomationsNotifier, List<Automation>>(
        AutomationsNotifier.new);

class AutomationsNotifier extends AsyncNotifier<List<Automation>> {
  @override
  Future<List<Automation>> build() async {
    final client = ref.read(backendClientProvider);
    final response = await client.get('/automations');
    final data = response.data as List<dynamic>;
    return data.map((e) => Automation.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createAutomation(String prompt, String cronExpr) async {
    final client = ref.read(backendClientProvider);
    await client.post('/automations', data: {'prompt': prompt, 'cron_expr': cronExpr});
    ref.invalidateSelf();
  }

  Future<void> deleteAutomation(String id) async {
    final client = ref.read(backendClientProvider);
    await client.delete('/automations/$id');
    ref.invalidateSelf();
  }

  Future<void> toggleActive(Automation automation) async {
    final client = ref.read(backendClientProvider);
    await client.post('/automations/${automation.id}/toggle', data: {});
    ref.invalidateSelf();
  }

  Future<Automation> runAutomationNow(String id) async {
    final client = ref.read(backendClientProvider);
    final response = await client.post('/automations/$id/run');
    ref.invalidateSelf();
    return Automation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Automation> toggleAutomation(String id, String currentStatus) async {
    final newStatus = currentStatus == 'active' ? 'paused' : 'active';
    final client = ref.read(backendClientProvider);
    final response = await client.patch('/automations/$id', data: {'status': newStatus});
    ref.invalidateSelf();
    return Automation.fromJson(response.data as Map<String, dynamic>);
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/models/automation.dart';
import 'automations_provider.dart';

class AutomationsScreen extends ConsumerWidget {
  const AutomationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final automationsAsync = ref.watch(automationsNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Automations')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateSheet(context, ref),
        child: const Icon(Icons.add),
      ),
      body: automationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (automations) => automations.isEmpty
            ? const Center(child: Text('No automations yet. Tap + to add one.'))
            : ListView.builder(
                itemCount: automations.length,
                itemBuilder: (context, index) {
                  final automation = automations[index];
                  return Dismissible(
                    key: Key(automation.id),
                    direction: DismissDirection.endToStart,
                    background: Container(
                      color: Colors.red,
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.only(right: 16),
                      child: const Icon(Icons.delete, color: Colors.white),
                    ),
                    onDismissed: (_) => ref
                        .read(automationsNotifierProvider.notifier)
                        .deleteAutomation(automation.id),
                    child: ListTile(
                      title: Text(
                        automation.prompt,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(automation.cronExpr),
                      trailing: Switch(
                        value: automation.active,
                        onChanged: (_) => ref
                            .read(automationsNotifierProvider.notifier)
                            .toggleActive(automation),
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }

  void _showCreateSheet(BuildContext context, WidgetRef ref) {
    final promptController = TextEditingController();
    final cronController = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 24,
          right: 24,
          top: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('New Automation',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            TextField(
              controller: promptController,
              decoration: const InputDecoration(labelText: 'Prompt'),
              maxLines: 3,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: cronController,
              decoration:
                  const InputDecoration(labelText: 'Cron Expression (e.g. 0 9 * * *)'),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                ref.read(automationsNotifierProvider.notifier).createAutomation(
                      promptController.text,
                      cronController.text,
                    );
                Navigator.pop(context);
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }
}

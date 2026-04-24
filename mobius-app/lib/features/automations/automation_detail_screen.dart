import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'automations_provider.dart';
import '../../shared/models/automation.dart';

class AutomationDetailScreen extends ConsumerStatefulWidget {
  final String automationId;
  const AutomationDetailScreen({super.key, required this.automationId});

  @override
  ConsumerState<AutomationDetailScreen> createState() =>
      _AutomationDetailScreenState();
}

class _AutomationDetailScreenState
    extends ConsumerState<AutomationDetailScreen> {
  bool _running = false;
  bool _toggling = false;

  Color _statusColor(String status) {
    switch (status) {
      case 'active':
        return const Color(0xFF4ade80);
      case 'paused':
        return const Color(0xFFfbbf24);
      case 'error':
        return const Color(0xFFf87171);
      default:
        return Colors.grey;
    }
  }

  Future<void> _runNow() async {
    setState(() => _running = true);
    try {
      await ref.read(automationsNotifierProvider.notifier).runAutomationNow(
            widget.automationId,
          );
      ref.invalidate(automationProvider(widget.automationId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Automation executed')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  Future<void> _toggle(String currentStatus) async {
    setState(() => _toggling = true);
    try {
      await ref
          .read(automationsNotifierProvider.notifier)
          .toggleAutomation(widget.automationId, currentStatus);
      ref.invalidate(automationProvider(widget.automationId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _toggling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncAutomation =
        ref.watch(automationProvider(widget.automationId));

    return Scaffold(
      backgroundColor: const Color(0xFF0a0a1a),
      appBar: AppBar(
        backgroundColor: const Color(0xFF111122),
        title: const Text('Automation Details'),
        foregroundColor: Colors.white,
      ),
      body: asyncAutomation.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Text('Error loading automation: $e',
              style: const TextStyle(color: Colors.red)),
        ),
        data: (automation) => _buildContent(automation),
      ),
    );
  }

  Widget _buildContent(Automation automation) {
    final statusColor = _statusColor(automation.status);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Name + status badge
          Row(
            children: [
              Expanded(
                child: Text(
                  automation.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: statusColor, width: 1),
                ),
                child: Text(
                  automation.status.toUpperCase(),
                  style: TextStyle(
                    color: statusColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Description
          if (automation.description.isNotEmpty) ...[
            Text(
              automation.description,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 16),
          ],

          // Cron
          _infoRow('Schedule (cron)', automation.cronExpr.isNotEmpty
              ? automation.cronExpr
              : 'Not set'),

          // Run count
          _infoRow('Run count', automation.runCount.toString()),

          // Last run
          _infoRow(
            'Last run',
            automation.lastRun != null
                ? _formatDate(automation.lastRun!)
                : 'Never',
          ),

          const SizedBox(height: 20),

          // Last result
          if (automation.lastResult != null &&
              automation.lastResult!.isNotEmpty) ...[
            const Text('Last Result',
                style: TextStyle(
                    color: Colors.grey, fontSize: 12, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1a1a2e),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF333355)),
              ),
              child: SelectableText(
                automation.lastResult!,
                style: const TextStyle(
                    color: Color(0xFF4ade80), fontSize: 13, fontFamily: 'monospace'),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Last error
          if (automation.lastError != null &&
              automation.lastError!.isNotEmpty) ...[
            const Text('Last Error',
                style: TextStyle(
                    color: Colors.grey, fontSize: 12, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1a0a0a),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF553333)),
              ),
              child: SelectableText(
                automation.lastError!,
                style: const TextStyle(
                    color: Color(0xFFf87171), fontSize: 13, fontFamily: 'monospace'),
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Script
          const Text('Script',
              style: TextStyle(
                  color: Colors.grey, fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxHeight: 300),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0d0d1a),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF333355)),
            ),
            child: SingleChildScrollView(
              child: SelectableText(
                automation.script.isNotEmpty ? automation.script : '(empty)',
                style: const TextStyle(
                    color: Color(0xFF93c5fd),
                    fontSize: 13,
                    fontFamily: 'monospace'),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Action buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _running ? null : _runNow,
                  icon: _running
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.play_arrow),
                  label: Text(_running ? 'Running...' : 'Run Now'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00B4D8),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed:
                      _toggling ? null : () => _toggle(automation.status),
                  icon: _toggling
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(automation.status == 'active'
                          ? Icons.pause
                          : Icons.play_arrow),
                  label: Text(
                    _toggling
                        ? '...'
                        : (automation.status == 'active' ? 'Pause' : 'Resume'),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: automation.status == 'active'
                        ? const Color(0xFFfbbf24)
                        : const Color(0xFF4ade80),
                    foregroundColor: Colors.black87,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Text('$label: ',
              style: const TextStyle(color: Colors.grey, fontSize: 13)),
          Text(value,
              style: const TextStyle(color: Colors.white70, fontSize: 13)),
        ],
      ),
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.year}-${_pad(dt.month)}-${_pad(dt.day)} '
        '${_pad(dt.hour)}:${_pad(dt.minute)}:${_pad(dt.second)}';
  }

  String _pad(int n) => n.toString().padLeft(2, '0');
}

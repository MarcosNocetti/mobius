class Automation {
  final String id;
  final String name;
  final String description;
  final String triggerType;
  final Map<String, dynamic> triggerConfig;
  final String script;
  final String status;
  final DateTime? lastRun;
  final String? lastResult;
  final String? lastError;
  final int runCount;

  const Automation({
    required this.id,
    required this.name,
    required this.description,
    required this.triggerType,
    required this.triggerConfig,
    required this.script,
    required this.status,
    this.lastRun,
    this.lastResult,
    this.lastError,
    this.runCount = 0,
  });

  /// Convenience getter for cron expression from triggerConfig.
  String get cronExpr {
    final cron = triggerConfig['cron'];
    return cron is String ? cron : '';
  }

  /// Backward-compatible active flag.
  bool get active => status == 'active';

  factory Automation.fromJson(Map<String, dynamic> json) => Automation(
        id: json['id'] as String,
        name: (json['name'] ?? '') as String,
        description: (json['description'] ?? '') as String,
        triggerType: (json['trigger_type'] ?? 'cron') as String,
        triggerConfig: json['trigger_config'] is Map
            ? Map<String, dynamic>.from(json['trigger_config'] as Map)
            : <String, dynamic>{},
        script: (json['script'] ?? '') as String,
        status: (json['status'] ?? 'active') as String,
        lastRun: json['last_run'] != null
            ? DateTime.parse(json['last_run'] as String)
            : null,
        lastResult: json['last_result'] as String?,
        lastError: json['last_error'] as String?,
        runCount: (json['run_count'] ?? 0) as int,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'trigger_type': triggerType,
        'trigger_config': triggerConfig,
        'script': script,
        'status': status,
        'last_run': lastRun?.toIso8601String(),
        'last_result': lastResult,
        'last_error': lastError,
        'run_count': runCount,
      };
}

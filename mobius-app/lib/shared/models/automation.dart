class Automation {
  final String id;
  final String prompt;
  final String cronExpr;
  final bool active;
  final DateTime? lastRun;

  const Automation({
    required this.id,
    required this.prompt,
    required this.cronExpr,
    required this.active,
    this.lastRun,
  });

  factory Automation.fromJson(Map<String, dynamic> json) => Automation(
        id: json['id'] as String,
        prompt: json['prompt'] as String,
        cronExpr: json['cron_expr'] as String,
        active: json['active'] as bool,
        lastRun: json['last_run'] != null
            ? DateTime.parse(json['last_run'] as String)
            : null,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'prompt': prompt,
        'cron_expr': cronExpr,
        'active': active,
        'last_run': lastRun?.toIso8601String(),
      };
}

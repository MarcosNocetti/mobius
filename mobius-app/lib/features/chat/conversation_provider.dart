import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../features/settings/settings_provider.dart';

class ConversationSummary {
  final String id;
  final String title;
  final int messageCount;
  final DateTime updatedAt;

  ConversationSummary({
    required this.id,
    required this.title,
    required this.messageCount,
    required this.updatedAt,
  });

  factory ConversationSummary.fromJson(Map<String, dynamic> json) =>
      ConversationSummary(
        id: json['id'] as String,
        title: json['title'] as String,
        messageCount: json['message_count'] as int? ?? 0,
        updatedAt: DateTime.tryParse(json['updated_at'] ?? '') ?? DateTime.now(),
      );
}

// Currently active conversation ID
final activeConversationIdProvider = StateProvider<String?>((ref) => null);

// List of conversations
final conversationsProvider =
    FutureProvider<List<ConversationSummary>>((ref) async {
  final client = ref.watch(backendClientProvider);
  final response = await client.get('/conversations');
  final list = response.data as List<dynamic>;
  return list
      .map((e) => ConversationSummary.fromJson(e as Map<String, dynamic>))
      .toList();
});

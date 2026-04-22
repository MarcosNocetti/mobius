class Message {
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime timestamp;

  const Message({
    required this.role,
    required this.content,
    required this.timestamp,
  });

  Message copyWith({String? role, String? content, DateTime? timestamp}) {
    return Message(
      role: role ?? this.role,
      content: content ?? this.content,
      timestamp: timestamp ?? this.timestamp,
    );
  }
}

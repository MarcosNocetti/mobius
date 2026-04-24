import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'conversation_provider.dart';
import 'chat_provider.dart';

class MobiusDrawer extends ConsumerWidget {
  const MobiusDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conversationsAsync = ref.watch(conversationsProvider);
    final activeId = ref.watch(activeConversationIdProvider);

    return Drawer(
      backgroundColor: const Color(0xFF111122),
      child: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Text('Mobius',
                      style: TextStyle(
                          color: Color(0xFF00B4D8),
                          fontSize: 20,
                          fontWeight: FontWeight.bold)),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.add, color: Color(0xFF00B4D8)),
                    tooltip: 'New Chat',
                    onPressed: () {
                      ref.read(activeConversationIdProvider.notifier).state =
                          null;
                      ref.invalidate(chatNotifierProvider);
                      Navigator.pop(context);
                      context.go('/chat');
                    },
                  ),
                ],
              ),
            ),
            const Divider(color: Color(0xFF333333), height: 1),
            // Nav buttons
            ListTile(
              leading: const Icon(Icons.link, color: Colors.grey),
              title: const Text('Integrations',
                  style: TextStyle(color: Colors.grey)),
              dense: true,
              onTap: () {
                Navigator.pop(context);
                context.push('/integrations');
              },
            ),
            ListTile(
              leading: const Icon(Icons.settings_outlined, color: Colors.grey),
              title:
                  const Text('Settings', style: TextStyle(color: Colors.grey)),
              dense: true,
              onTap: () {
                Navigator.pop(context);
                context.push('/settings');
              },
            ),
            const Divider(color: Color(0xFF333333), height: 1),
            // Conversation list header
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Conversations',
                    style: TextStyle(color: Colors.grey, fontSize: 12)),
              ),
            ),
            // Conversation list
            Expanded(
              child: conversationsAsync.when(
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (e, _) => const Center(
                    child:
                        Text('Error', style: TextStyle(color: Colors.grey))),
                data: (conversations) => conversations.isEmpty
                    ? const Center(
                        child: Text('No conversations yet',
                            style: TextStyle(color: Colors.grey)))
                    : ListView.builder(
                        itemCount: conversations.length,
                        itemBuilder: (context, index) {
                          final conv = conversations[index];
                          final isActive = conv.id == activeId;
                          return Container(
                            margin: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color:
                                  isActive ? const Color(0xFF1a1a3e) : null,
                              borderRadius: BorderRadius.circular(8),
                              border: isActive
                                  ? Border.all(
                                      color: const Color(0xFF00B4D8),
                                      width: 1)
                                  : null,
                            ),
                            child: ListTile(
                              dense: true,
                              title: Text(
                                conv.title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: isActive
                                      ? const Color(0xFF00B4D8)
                                      : Colors.white70,
                                  fontSize: 13,
                                ),
                              ),
                              subtitle: Text(
                                '${conv.messageCount} msgs',
                                style: const TextStyle(
                                    color: Colors.grey, fontSize: 11),
                              ),
                              onTap: () {
                                ref
                                    .read(activeConversationIdProvider.notifier)
                                    .state = conv.id;
                                Navigator.pop(context);
                                context.go('/chat');
                              },
                            ),
                          );
                        },
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

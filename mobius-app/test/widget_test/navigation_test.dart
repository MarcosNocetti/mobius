import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobius_app/app.dart';
import 'package:mobius_app/features/auth/auth_provider.dart';
import 'package:mobius_app/features/chat/conversation_provider.dart';

void main() {
  testWidgets('Chat screen has drawer with hamburger menu', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authNotifierProvider.overrideWith(
            () => _AlwaysAuthenticatedNotifier(),
          ),
          conversationsProvider.overrideWith(
            (ref) => <ConversationSummary>[],
          ),
        ],
        child: const MobiusApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Should have a hamburger menu icon
    expect(find.byIcon(Icons.menu), findsOneWidget);

    // Open the drawer
    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();

    // Drawer should contain navigation items
    expect(find.text('Mobius'), findsOneWidget);
    expect(find.text('Integrations'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(find.text('Conversations'), findsOneWidget);
  });
}

class _AlwaysAuthenticatedNotifier extends AuthNotifier {
  @override
  Future<AuthState> build() async => AuthState.authenticated;
}

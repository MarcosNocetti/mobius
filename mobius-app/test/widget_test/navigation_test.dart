import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobius_app/app.dart';
import 'package:mobius_app/features/auth/auth_provider.dart';

void main() {
  testWidgets('Bottom nav bar has 4 tabs', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authNotifierProvider.overrideWith(
            () => _AlwaysAuthenticatedNotifier(),
          ),
        ],
        child: const MobiusApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byIcon(Icons.chat_bubble_outline), findsOneWidget);
    expect(find.byIcon(Icons.schedule), findsOneWidget);
    expect(find.byIcon(Icons.link), findsOneWidget);
    expect(find.byIcon(Icons.settings_outlined), findsOneWidget);
  });

  testWidgets('Tapping Settings tab shows SettingsScreen', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authNotifierProvider.overrideWith(
            () => _AlwaysAuthenticatedNotifier(),
          ),
        ],
        child: const MobiusApp(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.settings_outlined));
    await tester.pumpAndSettle();

    expect(find.text('Settings'), findsWidgets);
  });
}

class _AlwaysAuthenticatedNotifier extends AuthNotifier {
  @override
  Future<AuthState> build() async => AuthState.authenticated;
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/theme.dart';
import 'features/auth/auth_provider.dart';
import 'features/auth/login_screen.dart';
import 'features/chat/chat_screen.dart';
import 'features/automations/automations_screen.dart';
import 'features/integrations/integrations_screen.dart';
import 'features/settings/settings_screen.dart';

class _ShellScaffold extends StatelessWidget {
  final StatefulNavigationShell shell;
  const _ShellScaffold({required this.shell});

  static const _destinations = [
    NavigationDestination(icon: Icon(Icons.chat_bubble_outline), label: 'Chat'),
    NavigationDestination(icon: Icon(Icons.schedule), label: 'Automations'),
    NavigationDestination(icon: Icon(Icons.link), label: 'Integrations'),
    NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: shell.currentIndex,
        onDestinationSelected: shell.goBranch,
        destinations: _destinations,
        backgroundColor: const Color(0xFF1A1A2E),
        indicatorColor: const Color(0xFF00B4D8),
      ),
    );
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return GoRouter(
    initialLocation: '/chat',
    redirect: (context, state) {
      final isLoggedIn = authState.valueOrNull == AuthState.authenticated;
      final isGoingToLogin = state.matchedLocation == '/login';
      if (!isLoggedIn && !isGoingToLogin) return '/login';
      if (isLoggedIn && isGoingToLogin) return '/chat';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => _ShellScaffold(shell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/chat', builder: (_, __) => const ChatScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/automations', builder: (_, __) => const AutomationsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/integrations', builder: (_, __) => const IntegrationsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
          ]),
        ],
      ),
    ],
  );
});

class MobiusApp extends ConsumerWidget {
  const MobiusApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Mobius',
      theme: mobiusTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

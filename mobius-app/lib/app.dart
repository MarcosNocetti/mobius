import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/theme.dart';
import 'features/auth/auth_provider.dart';
import 'features/auth/login_screen.dart';
import 'features/chat/chat_screen.dart';
import 'features/integrations/integrations_screen.dart';
import 'features/settings/settings_screen.dart';

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
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/chat', builder: (_, __) => const ChatScreen()),
      GoRoute(path: '/integrations', builder: (_, __) => const IntegrationsScreen()),
      GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
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

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'core/theme.dart';

final _router = GoRouter(
  initialLocation: '/chat',
  routes: [
    GoRoute(
      path: '/chat',
      builder: (context, state) => const Scaffold(
        body: Center(child: Text('Chat placeholder')),
      ),
    ),
  ],
);

class MobiusApp extends StatelessWidget {
  const MobiusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Mobius',
      theme: mobiusTheme,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}

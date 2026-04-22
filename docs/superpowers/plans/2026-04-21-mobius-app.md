# Mobius App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Mobius Flutter app — a thin mobile client with real-time AI chat, device automation, and integration management that connects to the Mobius backend server.

**Architecture:** Thin client — all AI and integration logic runs on the backend. The app handles UI rendering, WebSocket streaming, and local Android Accessibility Services for device automation. State management via Riverpod. Navigation via go_router.

**Tech Stack:** Flutter 3.x, Dart, Riverpod, go_router, web_socket_channel, flutter_secure_storage, android Accessibility Services, flutter_test, mockito

---

## Directory Structure

```
mobius-app/
├── lib/
│   ├── main.dart
│   ├── app.dart                      # MaterialApp + go_router setup
│   ├── core/
│   │   ├── config.dart               # AppConfig (server URL, etc)
│   │   ├── storage.dart              # flutter_secure_storage wrapper
│   │   └── theme.dart                # dark theme definition
│   ├── services/
│   │   ├── backend_client.dart       # HTTP calls (dio or http package)
│   │   ├── websocket_service.dart    # WebSocket connection + stream
│   │   └── auth_service.dart         # login, token storage, logout
│   ├── features/
│   │   ├── chat/
│   │   │   ├── chat_screen.dart
│   │   │   ├── chat_provider.dart    # Riverpod StateNotifier
│   │   │   ├── message_bubble.dart
│   │   │   └── typing_indicator.dart
│   │   ├── settings/
│   │   │   ├── settings_screen.dart
│   │   │   └── settings_provider.dart
│   │   ├── integrations/
│   │   │   ├── integrations_screen.dart
│   │   │   └── integrations_provider.dart
│   │   ├── automations/
│   │   │   ├── automations_screen.dart
│   │   │   └── automations_provider.dart
│   │   └── auth/
│   │       ├── login_screen.dart
│   │       └── auth_provider.dart
│   └── shared/
│       ├── widgets/
│       │   ├── primary_button.dart
│       │   └── loading_overlay.dart
│       └── models/
│           ├── message.dart          # Message model (role, content, timestamp)
│           └── automation.dart      # Automation model
├── android/
│   └── app/src/main/
│       ├── AndroidManifest.xml       # BIND_ACCESSIBILITY_SERVICE permission
│       └── java/.../MobiusAccessibilityService.java
├── test/
│   ├── services/
│   │   ├── backend_client_test.dart
│   │   └── websocket_service_test.dart
│   ├── features/
│   │   ├── chat/
│   │   │   └── chat_provider_test.dart
│   │   └── settings/
│   │       └── settings_provider_test.dart
│   └── widget_test/
│       └── chat_screen_test.dart
└── pubspec.yaml
```

---

## Task 1: Project scaffold

- [ ] Run `flutter create mobius-app --org com.mobius --platforms android,ios` in the workspace root
- [ ] Replace `pubspec.yaml` dependencies section with:
  ```yaml
  dependencies:
    flutter:
      sdk: flutter
    flutter_riverpod: ^2.5.1
    riverpod_annotation: ^2.3.5
    go_router: ^13.2.1
    web_socket_channel: ^2.4.5
    flutter_secure_storage: ^9.0.0
    dio: ^5.4.3+1
    url_launcher: ^6.2.6

  dev_dependencies:
    flutter_test:
      sdk: flutter
    mockito: ^5.4.4
    build_runner: ^2.4.9
    riverpod_generator: ^2.4.0
    flutter_lints: ^3.0.0
  ```
- [ ] Write `lib/core/theme.dart`:
  ```dart
  import 'package:flutter/material.dart';

  const _darkBackground = Color(0xFF1A1A2E);
  const _tealAccent = Color(0xFF00B4D8);

  final mobiusTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: _darkBackground,
    colorScheme: ColorScheme.dark(
      background: _darkBackground,
      primary: _tealAccent,
      secondary: _tealAccent,
      surface: const Color(0xFF16213E),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: _darkBackground,
      foregroundColor: Colors.white,
      elevation: 0,
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: _tealAccent),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: _tealAccent, width: 2),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: _tealAccent,
        foregroundColor: Colors.black,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 24),
      ),
    ),
  );
  ```
- [ ] Write `lib/app.dart` with a placeholder go_router and MaterialApp.router:
  ```dart
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
  ```
- [ ] Write `lib/main.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'app.dart';

  void main() {
    runApp(const ProviderScope(child: MobiusApp()));
  }
  ```
- [ ] Replace `test/widget_test.dart` with a smoke test:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mobius_app/app.dart';

  void main() {
    testWidgets('App smoke test — renders without crashing', (tester) async {
      await tester.pumpWidget(const ProviderScope(child: MobiusApp()));
      await tester.pumpAndSettle();
      expect(find.byType(MaterialApp), findsOneWidget);
    });
  }
  ```
- [ ] Run test and confirm pass:
  ```
  flutter test test/widget_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add pubspec.yaml lib/main.dart lib/app.dart lib/core/theme.dart test/widget_test.dart
  git commit -m "feat: scaffold Mobius Flutter app with theme, app entry, and smoke test"
  ```

---

## Task 2: Storage + Config

- [ ] Write failing test `test/services/storage_test.dart`:
  ```dart
  import 'package:flutter_secure_storage/flutter_secure_storage.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/core/storage.dart';

  import 'storage_test.mocks.dart';

  @GenerateMocks([FlutterSecureStorage])
  void main() {
    late MockFlutterSecureStorage mockSecureStorage;
    late AppStorage appStorage;

    setUp(() {
      mockSecureStorage = MockFlutterSecureStorage();
      appStorage = AppStorage(storage: mockSecureStorage);
    });

    test('saveToken writes token under correct key', () async {
      when(mockSecureStorage.write(key: 'jwt_token', value: 'abc123'))
          .thenAnswer((_) async {});
      await appStorage.saveToken('abc123');
      verify(mockSecureStorage.write(key: 'jwt_token', value: 'abc123')).called(1);
    });

    test('getToken reads token from storage', () async {
      when(mockSecureStorage.read(key: 'jwt_token'))
          .thenAnswer((_) async => 'abc123');
      final token = await appStorage.getToken();
      expect(token, 'abc123');
    });

    test('getServerUrl returns default when not set', () async {
      when(mockSecureStorage.read(key: 'server_url'))
          .thenAnswer((_) async => null);
      final url = await appStorage.getServerUrl();
      expect(url, 'http://localhost:8000');
    });

    test('saveServerUrl and getServerUrl round-trip', () async {
      when(mockSecureStorage.write(key: 'server_url', value: 'http://192.168.1.10:8000'))
          .thenAnswer((_) async {});
      when(mockSecureStorage.read(key: 'server_url'))
          .thenAnswer((_) async => 'http://192.168.1.10:8000');
      await appStorage.saveServerUrl('http://192.168.1.10:8000');
      final url = await appStorage.getServerUrl();
      expect(url, 'http://192.168.1.10:8000');
    });
  }
  ```
- [ ] Run test to confirm failure:
  ```
  flutter test test/services/storage_test.dart
  # Expected: Compilation error — AppStorage not found
  ```
- [ ] Write `lib/core/storage.dart`:
  ```dart
  import 'package:flutter_secure_storage/flutter_secure_storage.dart';

  class AppStorage {
    final FlutterSecureStorage _storage;

    AppStorage({FlutterSecureStorage? storage})
        : _storage = storage ?? const FlutterSecureStorage();

    static const _tokenKey = 'jwt_token';
    static const _serverUrlKey = 'server_url';
    static const _defaultServerUrl = 'http://localhost:8000';

    Future<void> saveToken(String token) =>
        _storage.write(key: _tokenKey, value: token);

    Future<String?> getToken() => _storage.read(key: _tokenKey);

    Future<void> deleteToken() => _storage.delete(key: _tokenKey);

    Future<void> saveServerUrl(String url) =>
        _storage.write(key: _serverUrlKey, value: url);

    Future<String> getServerUrl() async {
      final url = await _storage.read(key: _serverUrlKey);
      return url ?? _defaultServerUrl;
    }
  }
  ```
- [ ] Write `lib/core/config.dart`:
  ```dart
  import 'storage.dart';

  class AppConfig {
    AppConfig._();
    static final AppConfig instance = AppConfig._();

    final AppStorage _storage = AppStorage();

    Future<String> get serverUrl => _storage.getServerUrl();
    Future<String?> get jwtToken => _storage.getToken();

    Future<void> setServerUrl(String url) => _storage.saveServerUrl(url);
    Future<void> setToken(String token) => _storage.saveToken(token);
    Future<void> clearToken() => _storage.deleteToken();
  }
  ```
- [ ] Run code gen then tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/services/storage_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/core/storage.dart lib/core/config.dart test/services/storage_test.dart
  git commit -m "feat: AppStorage and AppConfig with secure storage; test: storage round-trip tests"
  ```

---

## Task 3: Auth service + login screen

- [ ] Write failing test `test/features/auth/auth_provider_test.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/services/auth_service.dart';
  import 'package:mobius_app/features/auth/auth_provider.dart';

  import 'auth_provider_test.mocks.dart';

  @GenerateMocks([AuthService])
  void main() {
    late MockAuthService mockAuthService;

    setUp(() {
      mockAuthService = MockAuthService();
    });

    test('login transitions state from loading to authenticated', () async {
      when(mockAuthService.login('user@test.com', 'password'))
          .thenAnswer((_) async {});
      when(mockAuthService.isLoggedIn()).thenAnswer((_) async => true);

      final container = ProviderContainer(
        overrides: [authServiceProvider.overrideWithValue(mockAuthService)],
      );
      addTearDown(container.dispose);

      await container.read(authNotifierProvider.notifier).login('user@test.com', 'password');

      verify(mockAuthService.login('user@test.com', 'password')).called(1);
      final state = container.read(authNotifierProvider);
      expect(state.value, AuthState.authenticated);
    });

    test('logout transitions state to unauthenticated', () async {
      when(mockAuthService.logout()).thenAnswer((_) async {});
      final container = ProviderContainer(
        overrides: [authServiceProvider.overrideWithValue(mockAuthService)],
      );
      addTearDown(container.dispose);

      await container.read(authNotifierProvider.notifier).logout();

      verify(mockAuthService.logout()).called(1);
      final state = container.read(authNotifierProvider);
      expect(state.value, AuthState.unauthenticated);
    });
  }
  ```
- [ ] Run test to confirm failure:
  ```
  flutter test test/features/auth/auth_provider_test.dart
  # Expected: Compilation error — AuthService, authNotifierProvider not found
  ```
- [ ] Write `lib/services/backend_client.dart`:
  ```dart
  import 'package:dio/dio.dart';
  import '../core/storage.dart';

  class BackendClient {
    final String baseUrl;
    final Dio _dio;
    final AppStorage _storage;

    BackendClient({required this.baseUrl, AppStorage? storage, Dio? dio})
        : _storage = storage ?? AppStorage(),
          _dio = dio ?? Dio() {
      _dio.interceptors.add(InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ));
    }

    Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
        _dio.get('$baseUrl$path', queryParameters: queryParameters);

    Future<Response> post(String path, {dynamic data}) =>
        _dio.post('$baseUrl$path', data: data);

    Future<Response> delete(String path) => _dio.delete('$baseUrl$path');
  }
  ```
- [ ] Write `lib/services/auth_service.dart`:
  ```dart
  import '../core/storage.dart';
  import 'backend_client.dart';

  class AuthService {
    final BackendClient _client;
    final AppStorage _storage;

    AuthService({required BackendClient client, AppStorage? storage})
        : _client = client,
          _storage = storage ?? AppStorage();

    Future<void> login(String email, String password) async {
      final response = await _client.post('/auth/token', data: {
        'email': email,
        'password': password,
      });
      final token = response.data['access_token'] as String;
      await _storage.saveToken(token);
    }

    Future<void> logout() async {
      await _storage.deleteToken();
    }

    Future<bool> isLoggedIn() async {
      final token = await _storage.getToken();
      return token != null && token.isNotEmpty;
    }
  }
  ```
- [ ] Write `lib/features/auth/auth_provider.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../services/auth_service.dart';
  import '../../services/backend_client.dart';
  import '../../core/config.dart';

  enum AuthState { unknown, authenticated, unauthenticated }

  final authServiceProvider = Provider<AuthService>((ref) {
    // baseUrl resolved synchronously using cached value; updated via settings
    return AuthService(client: BackendClient(baseUrl: 'http://localhost:8000'));
  });

  class AuthNotifier extends AsyncNotifier<AuthState> {
    @override
    Future<AuthState> build() async {
      final service = ref.read(authServiceProvider);
      final loggedIn = await service.isLoggedIn();
      return loggedIn ? AuthState.authenticated : AuthState.unauthenticated;
    }

    Future<void> login(String email, String password) async {
      state = const AsyncValue.loading();
      state = await AsyncValue.guard(() async {
        await ref.read(authServiceProvider).login(email, password);
        return AuthState.authenticated;
      });
    }

    Future<void> logout() async {
      state = const AsyncValue.loading();
      state = await AsyncValue.guard(() async {
        await ref.read(authServiceProvider).logout();
        return AuthState.unauthenticated;
      });
    }
  }

  final authNotifierProvider =
      AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
  ```
- [ ] Write `lib/features/auth/login_screen.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:go_router/go_router.dart';
  import 'auth_provider.dart';

  class LoginScreen extends ConsumerStatefulWidget {
    const LoginScreen({super.key});

    @override
    ConsumerState<LoginScreen> createState() => _LoginScreenState();
  }

  class _LoginScreenState extends ConsumerState<LoginScreen> {
    final _emailController = TextEditingController();
    final _passwordController = TextEditingController();
    String? _error;

    @override
    void dispose() {
      _emailController.dispose();
      _passwordController.dispose();
      super.dispose();
    }

    Future<void> _submit() async {
      setState(() => _error = null);
      try {
        await ref.read(authNotifierProvider.notifier).login(
              _emailController.text.trim(),
              _passwordController.text,
            );
        if (mounted) context.go('/chat');
      } catch (e) {
        setState(() => _error = e.toString());
      }
    }

    @override
    Widget build(BuildContext context) {
      final authState = ref.watch(authNotifierProvider);
      final isLoading = authState.isLoading;

      return Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Mobius',
                  style: TextStyle(fontSize: 36, fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 48),
                TextField(
                  controller: _emailController,
                  decoration: const InputDecoration(labelText: 'Email'),
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordController,
                  decoration: const InputDecoration(labelText: 'Password'),
                  obscureText: true,
                  onSubmitted: (_) => _submit(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                ],
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: isLoading ? null : _submit,
                  child: isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Sign In'),
                ),
              ],
            ),
          ),
        ),
      );
    }
  }
  ```
- [ ] Update `lib/app.dart` to add go_router redirect based on auth state:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:go_router/go_router.dart';
  import 'core/theme.dart';
  import 'features/auth/auth_provider.dart';
  import 'features/auth/login_screen.dart';

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
        GoRoute(
          path: '/chat',
          builder: (context, state) => const Scaffold(
            body: Center(child: Text('Chat placeholder')),
          ),
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
  ```
- [ ] Run codegen and tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/features/auth/auth_provider_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/services/ lib/features/auth/ lib/app.dart test/features/auth/
  git commit -m "feat: auth service, login screen, go_router redirect; test: auth provider login/logout"
  ```

---

## Task 4: WebSocket service

- [ ] Write failing test `test/services/websocket_service_test.dart`:
  ```dart
  import 'dart:async';
  import 'dart:convert';

  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:web_socket_channel/web_socket_channel.dart';
  import 'package:mobius_app/services/websocket_service.dart';

  import 'websocket_service_test.mocks.dart';

  @GenerateMocks([WebSocketChannel, WebSocketSink])
  void main() {
    late StreamController<dynamic> incomingController;
    late MockWebSocketChannel mockChannel;
    late MockWebSocketSink mockSink;

    setUp(() {
      incomingController = StreamController<dynamic>.broadcast();
      mockChannel = MockWebSocketChannel();
      mockSink = MockWebSocketSink();
      when(mockChannel.stream).thenAnswer((_) => incomingController.stream);
      when(mockChannel.sink).thenReturn(mockSink);
    });

    tearDown(() => incomingController.close());

    test('stream emits TokenEvent and DoneEvent from raw WS messages', () async {
      final service = WebSocketService(channelFactory: (uri) => mockChannel);
      service.connect('localhost:8000', 'test-token');

      final events = <WsEvent>[];
      final sub = service.stream.listen(events.add);

      incomingController.add(jsonEncode({'type': 'token', 'content': 'Hello'}));
      incomingController.add(jsonEncode({'type': 'token', 'content': ' world'}));
      incomingController.add(jsonEncode({'type': 'done'}));

      await Future.delayed(const Duration(milliseconds: 50));
      await sub.cancel();

      expect(events[0], isA<TokenEvent>());
      expect((events[0] as TokenEvent).content, 'Hello');
      expect(events[1], isA<TokenEvent>());
      expect((events[1] as TokenEvent).content, ' world');
      expect(events[2], isA<DoneEvent>());
    });

    test('sendMessage sends JSON payload over sink', () async {
      final service = WebSocketService(channelFactory: (uri) => mockChannel);
      service.connect('localhost:8000', 'test-token');

      service.sendMessage('Hello AI', 'gemini-flash');

      verify(mockSink.add(argThat(contains('"message":"Hello AI"')))).called(1);
      verify(mockSink.add(argThat(contains('"model":"gemini-flash"')))).called(1);
    });
  }
  ```
- [ ] Run test to confirm failure:
  ```
  flutter test test/services/websocket_service_test.dart
  # Expected: Compilation error — WebSocketService not found
  ```
- [ ] Write `lib/shared/models/message.dart`:
  ```dart
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
  ```
- [ ] Write `lib/services/websocket_service.dart`:
  ```dart
  import 'dart:async';
  import 'dart:convert';

  import 'package:web_socket_channel/web_socket_channel.dart';

  sealed class WsEvent {}

  class TokenEvent extends WsEvent {
    final String content;
    TokenEvent(this.content);
  }

  class DoneEvent extends WsEvent {}

  typedef ChannelFactory = WebSocketChannel Function(Uri uri);

  class WebSocketService {
    WebSocketChannel? _channel;
    final _controller = StreamController<WsEvent>.broadcast();
    final ChannelFactory? channelFactory;
    StreamSubscription? _subscription;

    WebSocketService({this.channelFactory});

    Stream<WsEvent> get stream => _controller.stream;

    void connect(String serverHost, String token) {
      final uri = Uri.parse('ws://$serverHost/ws/chat?token=$token');
      _channel = channelFactory != null
          ? channelFactory!(uri)
          : WebSocketChannel.connect(uri);

      _subscription = _channel!.stream.listen(
        _onData,
        onError: _onError,
        onDone: _onDone,
      );
    }

    void _onData(dynamic raw) {
      try {
        final json = jsonDecode(raw as String) as Map<String, dynamic>;
        if (json['type'] == 'token') {
          _controller.add(TokenEvent(json['content'] as String));
        } else if (json['type'] == 'done') {
          _controller.add(DoneEvent());
        }
      } catch (_) {}
    }

    void _onError(Object error) {
      // Reconnect logic can be added here (e.g., exponential backoff)
    }

    void _onDone() {
      // Channel closed — could trigger reconnect
    }

    void sendMessage(String message, String model) {
      final payload = jsonEncode({'message': message, 'model': model});
      _channel?.sink.add(payload);
    }

    Future<void> disconnect() async {
      await _subscription?.cancel();
      await _channel?.sink.close();
    }

    void dispose() {
      disconnect();
      _controller.close();
    }
  }
  ```
- [ ] Run codegen and tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/services/websocket_service_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/services/websocket_service.dart lib/shared/models/message.dart test/services/websocket_service_test.dart
  git commit -m "feat: WebSocket service with typed stream events; test: token and done event emission"
  ```

---

## Task 5: Chat screen

- [ ] Write failing test `test/features/chat/chat_provider_test.dart`:
  ```dart
  import 'dart:async';

  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/features/chat/chat_provider.dart';
  import 'package:mobius_app/services/websocket_service.dart';
  import 'package:mobius_app/shared/models/message.dart';

  import 'chat_provider_test.mocks.dart';

  @GenerateMocks([WebSocketService])
  void main() {
    late MockWebSocketService mockWs;
    late StreamController<WsEvent> wsController;

    setUp(() {
      wsController = StreamController<WsEvent>.broadcast();
      mockWs = MockWebSocketService();
      when(mockWs.stream).thenAnswer((_) => wsController.stream);
    });

    tearDown(() => wsController.close());

    test('sendMessage appends user message then builds assistant message token by token', () async {
      final container = ProviderContainer(
        overrides: [webSocketServiceProvider.overrideWithValue(mockWs)],
      );
      addTearDown(container.dispose);

      final notifier = container.read(chatNotifierProvider.notifier);
      unawaited(notifier.sendMessage('Hello', 'gemini-flash'));

      // verify user message added immediately
      await Future.delayed(Duration.zero);
      final msgs1 = container.read(chatNotifierProvider).value ?? [];
      expect(msgs1.any((m) => m.role == 'user' && m.content == 'Hello'), isTrue);

      // stream tokens
      wsController.add(TokenEvent('Hi'));
      wsController.add(TokenEvent(' there'));
      wsController.add(DoneEvent());

      await Future.delayed(const Duration(milliseconds: 50));

      final msgs2 = container.read(chatNotifierProvider).value ?? [];
      final assistant = msgs2.firstWhere((m) => m.role == 'assistant');
      expect(assistant.content, 'Hi there');
    });
  }
  ```
- [ ] Run test to confirm failure:
  ```
  flutter test test/features/chat/chat_provider_test.dart
  # Expected: Compilation error — chatNotifierProvider not found
  ```
- [ ] Write `lib/features/chat/chat_provider.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../services/websocket_service.dart';
  import '../../shared/models/message.dart';

  final webSocketServiceProvider = Provider<WebSocketService>((ref) {
    final service = WebSocketService();
    ref.onDispose(service.dispose);
    return service;
  });

  final isStreamingProvider = StateProvider<bool>((ref) => false);

  class ChatNotifier extends AsyncNotifier<List<Message>> {
    @override
    Future<List<Message>> build() async => [];

    Future<void> sendMessage(String text, String model) async {
      final ws = ref.read(webSocketServiceProvider);
      final current = state.value ?? [];

      // Add user message
      final userMsg = Message(role: 'user', content: text, timestamp: DateTime.now());
      state = AsyncValue.data([...current, userMsg]);

      ref.read(isStreamingProvider.notifier).state = true;

      // Placeholder assistant message
      var assistantContent = '';
      final assistantMsg = Message(role: 'assistant', content: '', timestamp: DateTime.now());
      state = AsyncValue.data([...(state.value ?? []), assistantMsg]);

      ws.sendMessage(text, model);

      await for (final event in ws.stream) {
        if (event is TokenEvent) {
          assistantContent += event.content;
          final messages = List<Message>.from(state.value ?? []);
          final lastIndex = messages.length - 1;
          messages[lastIndex] = messages[lastIndex].copyWith(content: assistantContent);
          state = AsyncValue.data(messages);
        } else if (event is DoneEvent) {
          break;
        }
      }

      ref.read(isStreamingProvider.notifier).state = false;
    }
  }

  final chatNotifierProvider =
      AsyncNotifierProvider<ChatNotifier, List<Message>>(ChatNotifier.new);
  ```
- [ ] Write `lib/features/chat/message_bubble.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import '../../shared/models/message.dart';

  class MessageBubble extends StatelessWidget {
    final Message message;
    const MessageBubble({super.key, required this.message});

    bool get _isUser => message.role == 'user';

    @override
    Widget build(BuildContext context) {
      final theme = Theme.of(context);
      return Align(
        alignment: _isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75,
          ),
          decoration: BoxDecoration(
            color: _isUser
                ? theme.colorScheme.primary
                : const Color(0xFF16213E),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(16),
              topRight: const Radius.circular(16),
              bottomLeft: Radius.circular(_isUser ? 16 : 4),
              bottomRight: Radius.circular(_isUser ? 4 : 16),
            ),
          ),
          child: Text(
            message.content,
            style: TextStyle(
              color: _isUser ? Colors.black : Colors.white,
              fontSize: 15,
            ),
          ),
        ),
      );
    }
  }
  ```
- [ ] Write `lib/features/chat/typing_indicator.dart`:
  ```dart
  import 'package:flutter/material.dart';

  class TypingIndicator extends StatefulWidget {
    const TypingIndicator({super.key});

    @override
    State<TypingIndicator> createState() => _TypingIndicatorState();
  }

  class _TypingIndicatorState extends State<TypingIndicator>
      with SingleTickerProviderStateMixin {
    late final AnimationController _controller;

    @override
    void initState() {
      super.initState();
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 900),
      )..repeat();
    }

    @override
    void dispose() {
      _controller.dispose();
      super.dispose();
    }

    @override
    Widget build(BuildContext context) {
      return Padding(
        padding: const EdgeInsets.only(left: 16, bottom: 8),
        child: Row(
          children: List.generate(3, (index) {
            return AnimatedBuilder(
              animation: _controller,
              builder: (_, __) {
                final phase = (_controller.value + index / 3) % 1.0;
                final opacity = (phase < 0.5 ? phase * 2 : (1 - phase) * 2).clamp(0.3, 1.0);
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Opacity(
                    opacity: opacity,
                    child: const CircleAvatar(
                      radius: 4,
                      backgroundColor: Color(0xFF00B4D8),
                    ),
                  ),
                );
              },
            );
          }),
        ),
      );
    }
  }
  ```
- [ ] Write `lib/features/chat/chat_screen.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'chat_provider.dart';
  import 'message_bubble.dart';
  import 'typing_indicator.dart';

  class ChatScreen extends ConsumerStatefulWidget {
    const ChatScreen({super.key});

    @override
    ConsumerState<ChatScreen> createState() => _ChatScreenState();
  }

  class _ChatScreenState extends ConsumerState<ChatScreen> {
    final _textController = TextEditingController();
    final _scrollController = ScrollController();
    String _selectedModel = 'gemini-flash';

    @override
    void dispose() {
      _textController.dispose();
      _scrollController.dispose();
      super.dispose();
    }

    void _send() {
      final text = _textController.text.trim();
      if (text.isEmpty) return;
      _textController.clear();
      ref.read(chatNotifierProvider.notifier).sendMessage(text, _selectedModel);
      Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
    }

    void _scrollToBottom() {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    }

    @override
    Widget build(BuildContext context) {
      final messagesAsync = ref.watch(chatNotifierProvider);
      final isStreaming = ref.watch(isStreamingProvider);

      return Scaffold(
        appBar: AppBar(title: const Text('Mobius Chat')),
        body: Column(
          children: [
            Expanded(
              child: messagesAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('Error: $e')),
                data: (messages) => ListView.builder(
                  controller: _scrollController,
                  itemCount: messages.length + (isStreaming ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == messages.length && isStreaming) {
                      return const TypingIndicator();
                    }
                    return MessageBubble(message: messages[index]);
                  },
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: const InputDecoration(
                        hintText: 'Ask Mobius...',
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: isStreaming ? null : _send,
                    color: const Color(0xFF00B4D8),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }
  }
  ```
- [ ] Write `test/widget_test/chat_screen_test.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/features/chat/chat_screen.dart';
  import 'package:mobius_app/features/chat/chat_provider.dart';
  import 'package:mobius_app/shared/models/message.dart';
  import 'package:mobius_app/services/websocket_service.dart';

  import 'chat_screen_test.mocks.dart';

  @GenerateMocks([WebSocketService])
  void main() {
    testWidgets('ChatScreen renders message list and send button', (tester) async {
      final messages = [
        Message(role: 'user', content: 'Hello', timestamp: DateTime.now()),
        Message(role: 'assistant', content: 'Hi there!', timestamp: DateTime.now()),
      ];

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            chatNotifierProvider.overrideWith(() => _FakeChatNotifier(messages)),
          ],
          child: const MaterialApp(home: ChatScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Hello'), findsOneWidget);
      expect(find.text('Hi there!'), findsOneWidget);
      expect(find.byIcon(Icons.send), findsOneWidget);
    });
  }

  class _FakeChatNotifier extends ChatNotifier {
    final List<Message> _messages;
    _FakeChatNotifier(this._messages);

    @override
    Future<List<Message>> build() async => _messages;
  }
  ```
- [ ] Run codegen and tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/features/chat/chat_provider_test.dart
  flutter test test/widget_test/chat_screen_test.dart
  # Expected: All tests passed.
  ```
- [ ] Update `lib/app.dart` to route `/chat` to `ChatScreen` and add the import
- [ ] Commit:
  ```
  git add lib/features/chat/ test/features/chat/ test/widget_test/chat_screen_test.dart
  git commit -m "feat: chat screen with streaming messages, typing indicator; test: provider and widget"
  ```

---

## Task 6: Settings screen

- [ ] Write failing test `test/features/settings/settings_provider_test.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:dio/dio.dart';
  import 'package:mobius_app/features/settings/settings_provider.dart';
  import 'package:mobius_app/services/backend_client.dart';

  import 'settings_provider_test.mocks.dart';

  @GenerateMocks([BackendClient])
  void main() {
    late MockBackendClient mockClient;

    setUp(() {
      mockClient = MockBackendClient();
    });

    test('testConnection returns true when GET /health returns 200', () async {
      when(mockClient.get('/health')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/health'),
          statusCode: 200,
        ),
      );

      final container = ProviderContainer(
        overrides: [backendClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final result =
          await container.read(settingsNotifierProvider.notifier).testConnection();
      expect(result, isTrue);
    });

    test('testConnection returns false when GET /health throws', () async {
      when(mockClient.get('/health')).thenThrow(Exception('unreachable'));

      final container = ProviderContainer(
        overrides: [backendClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final result =
          await container.read(settingsNotifierProvider.notifier).testConnection();
      expect(result, isFalse);
    });
  }
  ```
- [ ] Run test to confirm failure:
  ```
  flutter test test/features/settings/settings_provider_test.dart
  # Expected: Compilation error
  ```
- [ ] Write `lib/features/settings/settings_provider.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../core/storage.dart';
  import '../../services/backend_client.dart';

  enum AiModel { geminiFlash, claudeSonnet, gpt4o }

  extension AiModelLabel on AiModel {
    String get label => switch (this) {
          AiModel.geminiFlash => 'gemini-flash',
          AiModel.claudeSonnet => 'claude-sonnet',
          AiModel.gpt4o => 'gpt-4o',
        };
  }

  class SettingsState {
    final String serverUrl;
    final AiModel selectedModel;
    final Map<AiModel, String> apiKeys;

    const SettingsState({
      this.serverUrl = 'http://localhost:8000',
      this.selectedModel = AiModel.geminiFlash,
      this.apiKeys = const {},
    });

    SettingsState copyWith({
      String? serverUrl,
      AiModel? selectedModel,
      Map<AiModel, String>? apiKeys,
    }) =>
        SettingsState(
          serverUrl: serverUrl ?? this.serverUrl,
          selectedModel: selectedModel ?? this.selectedModel,
          apiKeys: apiKeys ?? this.apiKeys,
        );
  }

  final backendClientProvider = Provider<BackendClient>((ref) {
    return BackendClient(baseUrl: 'http://localhost:8000');
  });

  class SettingsNotifier extends Notifier<SettingsState> {
    @override
    SettingsState build() => const SettingsState();

    Future<void> setServerUrl(String url) async {
      await AppStorage().saveServerUrl(url);
      state = state.copyWith(serverUrl: url);
    }

    void setModel(AiModel model) {
      state = state.copyWith(selectedModel: model);
    }

    void setApiKey(AiModel model, String key) {
      final updated = Map<AiModel, String>.from(state.apiKeys);
      updated[model] = key;
      state = state.copyWith(apiKeys: updated);
    }

    bool hasApiKey(AiModel model) => state.apiKeys.containsKey(model) &&
        state.apiKeys[model]!.isNotEmpty;

    Future<bool> testConnection() async {
      try {
        final client = ref.read(backendClientProvider);
        final response = await client.get('/health');
        return response.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
  }

  final settingsNotifierProvider =
      NotifierProvider<SettingsNotifier, SettingsState>(SettingsNotifier.new);
  ```
- [ ] Write `lib/features/settings/settings_screen.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'settings_provider.dart';

  class SettingsScreen extends ConsumerStatefulWidget {
    const SettingsScreen({super.key});

    @override
    ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
  }

  class _SettingsScreenState extends ConsumerState<SettingsScreen> {
    late final TextEditingController _serverUrlController;

    @override
    void initState() {
      super.initState();
      final url = ref.read(settingsNotifierProvider).serverUrl;
      _serverUrlController = TextEditingController(text: url);
    }

    @override
    void dispose() {
      _serverUrlController.dispose();
      super.dispose();
    }

    Future<void> _testConnection() async {
      final ok = await ref.read(settingsNotifierProvider.notifier).testConnection();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? 'Connected' : 'Connection failed'),
          backgroundColor: ok ? Colors.green : Colors.red,
        ),
      );
    }

    @override
    Widget build(BuildContext context) {
      final settings = ref.watch(settingsNotifierProvider);
      final notifier = ref.read(settingsNotifierProvider.notifier);

      return Scaffold(
        appBar: AppBar(title: const Text('Settings')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text('Server', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            TextField(
              controller: _serverUrlController,
              decoration: const InputDecoration(labelText: 'Server URL'),
              onChanged: notifier.setServerUrl,
            ),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _testConnection,
              child: const Text('Test Connection'),
            ),
            const Divider(height: 32),
            const Text('AI Model', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            DropdownButtonFormField<AiModel>(
              value: settings.selectedModel,
              decoration: const InputDecoration(labelText: 'Default Model'),
              items: AiModel.values
                  .map((m) => DropdownMenuItem(value: m, child: Text(m.label)))
                  .toList(),
              onChanged: (m) => m != null ? notifier.setModel(m) : null,
            ),
            const Divider(height: 32),
            const Text('API Keys', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            ...AiModel.values.map((model) => Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: TextField(
                    decoration: InputDecoration(
                      labelText: '${model.label} API Key',
                    ),
                    obscureText: true,
                    onChanged: (key) => notifier.setApiKey(model, key),
                  ),
                )),
            const SizedBox(height: 24),
            const Divider(height: 32),
            const Text('Accessibility', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () {
                // Opens Android accessibility settings; handled by device_agent
              },
              child: const Text('Enable Accessibility Service'),
            ),
          ],
        ),
      );
    }
  }
  ```
- [ ] Run codegen and tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/features/settings/settings_provider_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/features/settings/ test/features/settings/
  git commit -m "feat: settings screen with server URL, model selector, API keys; test: health check"
  ```

---

## Task 7: Integrations screen

- [ ] Write failing test `test/features/integrations/integrations_provider_test.dart`:
  ```dart
  import 'package:dio/dio.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/features/integrations/integrations_provider.dart';
  import 'package:mobius_app/features/settings/settings_provider.dart';
  import 'package:mobius_app/services/backend_client.dart';

  import 'integrations_provider_test.mocks.dart';

  @GenerateMocks([BackendClient])
  void main() {
    late MockBackendClient mockClient;

    setUp(() {
      mockClient = MockBackendClient();
    });

    test('fetches integration status and maps to IntegrationStatus list', () async {
      when(mockClient.get('/integrations/status')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/integrations/status'),
          statusCode: 200,
          data: {
            'google': true,
            'notion': false,
            'instagram': false,
            'twitter': true,
            'linkedin': false,
          },
        ),
      );

      final container = ProviderContainer(
        overrides: [backendClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final result = await container.read(integrationsProvider.future);
      expect(result.where((i) => i.connected).length, 2);
      expect(result.where((i) => !i.connected).length, 3);
    });
  }
  ```
- [ ] Run to confirm failure:
  ```
  flutter test test/features/integrations/integrations_provider_test.dart
  # Expected: Compilation error
  ```
- [ ] Write `lib/features/integrations/integrations_provider.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../features/settings/settings_provider.dart';

  class IntegrationStatus {
    final String name;
    final String displayName;
    final bool connected;
    final String oauthPath;

    const IntegrationStatus({
      required this.name,
      required this.displayName,
      required this.connected,
      required this.oauthPath,
    });
  }

  const _integrationMeta = {
    'google': ('Google', '/oauth/google'),
    'notion': ('Notion', '/oauth/notion'),
    'instagram': ('Instagram', '/oauth/instagram'),
    'twitter': ('Twitter / X', '/oauth/twitter'),
    'linkedin': ('LinkedIn', '/oauth/linkedin'),
  };

  final integrationsProvider = FutureProvider<List<IntegrationStatus>>((ref) async {
    final client = ref.watch(backendClientProvider);
    final response = await client.get('/integrations/status');
    final data = response.data as Map<String, dynamic>;

    return _integrationMeta.entries.map((entry) {
      final (displayName, oauthPath) = entry.value;
      return IntegrationStatus(
        name: entry.key,
        displayName: displayName,
        connected: (data[entry.key] as bool?) ?? false,
        oauthPath: oauthPath,
      );
    }).toList();
  });
  ```
- [ ] Write `lib/features/integrations/integrations_screen.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:url_launcher/url_launcher.dart';
  import '../../features/settings/settings_provider.dart';
  import 'integrations_provider.dart';

  class IntegrationsScreen extends ConsumerWidget {
    const IntegrationsScreen({super.key});

    @override
    Widget build(BuildContext context, WidgetRef ref) {
      final integrationsAsync = ref.watch(integrationsProvider);
      final settings = ref.watch(settingsNotifierProvider);

      return Scaffold(
        appBar: AppBar(title: const Text('Integrations')),
        body: integrationsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Error: $e')),
          data: (integrations) => ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: integrations.length,
            separatorBuilder: (_, __) => const Divider(),
            itemBuilder: (context, index) {
              final integration = integrations[index];
              return ListTile(
                title: Text(integration.displayName),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Chip(
                      label: Text(
                        integration.connected ? 'Connected' : 'Disconnected',
                        style: TextStyle(
                          color: integration.connected ? Colors.green : Colors.grey,
                          fontSize: 12,
                        ),
                      ),
                      backgroundColor: integration.connected
                          ? Colors.green.withOpacity(0.15)
                          : Colors.grey.withOpacity(0.15),
                    ),
                    const SizedBox(width: 8),
                    TextButton(
                      onPressed: () async {
                        final url = Uri.parse(
                            '${settings.serverUrl}${integration.oauthPath}');
                        if (await canLaunchUrl(url)) {
                          await launchUrl(url, mode: LaunchMode.externalApplication);
                        }
                      },
                      child: Text(integration.connected ? 'Disconnect' : 'Connect'),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      );
    }
  }
  ```
- [ ] Run tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/features/integrations/integrations_provider_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/features/integrations/ test/features/integrations/
  git commit -m "feat: integrations screen with status chips and OAuth URL launcher; test: status mapping"
  ```

---

## Task 8: Automations screen

- [ ] Write failing test `test/features/automations/automations_provider_test.dart`:
  ```dart
  import 'package:dio/dio.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mockito/annotations.dart';
  import 'package:mockito/mockito.dart';
  import 'package:mobius_app/features/automations/automations_provider.dart';
  import 'package:mobius_app/features/settings/settings_provider.dart';
  import 'package:mobius_app/services/backend_client.dart';
  import 'package:mobius_app/shared/models/automation.dart';

  import 'automations_provider_test.mocks.dart';

  @GenerateMocks([BackendClient])
  void main() {
    late MockBackendClient mockClient;

    setUp(() {
      mockClient = MockBackendClient();
    });

    test('loads automations from GET /automations', () async {
      when(mockClient.get('/automations')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/automations'),
          statusCode: 200,
          data: [
            {
              'id': '1',
              'prompt': 'Post daily summary',
              'cron_expr': '0 9 * * *',
              'active': true,
              'last_run': null,
            },
            {
              'id': '2',
              'prompt': 'Check emails',
              'cron_expr': '0 * * * *',
              'active': false,
              'last_run': '2026-04-20T09:00:00Z',
            },
          ],
        ),
      );

      final container = ProviderContainer(
        overrides: [backendClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final automations = await container.read(automationsProvider.future);
      expect(automations.length, 2);
      expect(automations[0].prompt, 'Post daily summary');
      expect(automations[1].active, isFalse);
    });
  }
  ```
- [ ] Run to confirm failure:
  ```
  flutter test test/features/automations/automations_provider_test.dart
  # Expected: Compilation error
  ```
- [ ] Write `lib/shared/models/automation.dart`:
  ```dart
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
  ```
- [ ] Write `lib/features/automations/automations_provider.dart`:
  ```dart
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../features/settings/settings_provider.dart';
  import '../../shared/models/automation.dart';

  final automationsProvider =
      FutureProvider<List<Automation>>((ref) async {
    final client = ref.watch(backendClientProvider);
    final response = await client.get('/automations');
    final data = response.data as List<dynamic>;
    return data.map((e) => Automation.fromJson(e as Map<String, dynamic>)).toList();
  });

  final automationsNotifierProvider =
      AsyncNotifierProvider<AutomationsNotifier, List<Automation>>(
          AutomationsNotifier.new);

  class AutomationsNotifier extends AsyncNotifier<List<Automation>> {
    @override
    Future<List<Automation>> build() async {
      final client = ref.read(backendClientProvider);
      final response = await client.get('/automations');
      final data = response.data as List<dynamic>;
      return data.map((e) => Automation.fromJson(e as Map<String, dynamic>)).toList();
    }

    Future<void> createAutomation(String prompt, String cronExpr) async {
      final client = ref.read(backendClientProvider);
      await client.post('/automations', data: {'prompt': prompt, 'cron_expr': cronExpr});
      ref.invalidateSelf();
    }

    Future<void> deleteAutomation(String id) async {
      final client = ref.read(backendClientProvider);
      await client.delete('/automations/$id');
      ref.invalidateSelf();
    }

    Future<void> toggleActive(Automation automation) async {
      final client = ref.read(backendClientProvider);
      await client.post('/automations/${automation.id}/toggle', data: {});
      ref.invalidateSelf();
    }
  }
  ```
- [ ] Write `lib/features/automations/automations_screen.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import '../../shared/models/automation.dart';
  import 'automations_provider.dart';

  class AutomationsScreen extends ConsumerWidget {
    const AutomationsScreen({super.key});

    @override
    Widget build(BuildContext context, WidgetRef ref) {
      final automationsAsync = ref.watch(automationsNotifierProvider);

      return Scaffold(
        appBar: AppBar(title: const Text('Automations')),
        floatingActionButton: FloatingActionButton(
          onPressed: () => _showCreateSheet(context, ref),
          child: const Icon(Icons.add),
        ),
        body: automationsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Error: $e')),
          data: (automations) => automations.isEmpty
              ? const Center(child: Text('No automations yet. Tap + to add one.'))
              : ListView.builder(
                  itemCount: automations.length,
                  itemBuilder: (context, index) {
                    final automation = automations[index];
                    return Dismissible(
                      key: Key(automation.id),
                      direction: DismissDirection.endToStart,
                      background: Container(
                        color: Colors.red,
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 16),
                        child: const Icon(Icons.delete, color: Colors.white),
                      ),
                      onDismissed: (_) => ref
                          .read(automationsNotifierProvider.notifier)
                          .deleteAutomation(automation.id),
                      child: ListTile(
                        title: Text(
                          automation.prompt,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(automation.cronExpr),
                        trailing: Switch(
                          value: automation.active,
                          onChanged: (_) => ref
                              .read(automationsNotifierProvider.notifier)
                              .toggleActive(automation),
                        ),
                      ),
                    );
                  },
                ),
        ),
      );
    }

    void _showCreateSheet(BuildContext context, WidgetRef ref) {
      final promptController = TextEditingController();
      final cronController = TextEditingController();

      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (context) => Padding(
          padding: EdgeInsets.only(
            left: 24,
            right: 24,
            top: 24,
            bottom: MediaQuery.of(context).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('New Automation',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              TextField(
                controller: promptController,
                decoration: const InputDecoration(labelText: 'Prompt'),
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: cronController,
                decoration:
                    const InputDecoration(labelText: 'Cron Expression (e.g. 0 9 * * *)'),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  ref.read(automationsNotifierProvider.notifier).createAutomation(
                        promptController.text,
                        cronController.text,
                      );
                  Navigator.pop(context);
                },
                child: const Text('Create'),
              ),
            ],
          ),
        ),
      );
    }
  }
  ```
- [ ] Run tests:
  ```
  flutter pub run build_runner build --delete-conflicting-outputs
  flutter test test/features/automations/automations_provider_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/shared/models/automation.dart lib/features/automations/ test/features/automations/
  git commit -m "feat: automations screen with create/delete/toggle; test: GET /automations mapping"
  ```

---

## Task 9: Bottom navigation

- [ ] Write failing widget test `test/widget_test/navigation_test.dart`:
  ```dart
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
  ```
- [ ] Run to confirm failure:
  ```
  flutter test test/widget_test/navigation_test.dart
  # Expected: Test failure — NavigationBar not found
  ```
- [ ] Rewrite `lib/app.dart` to use go_router `ShellRoute` with `NavigationBar`:
  ```dart
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
  ```
- [ ] Run tests:
  ```
  flutter test test/widget_test/navigation_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/app.dart test/widget_test/navigation_test.dart
  git commit -m "feat: bottom NavigationBar with 4 tabs via go_router ShellRoute; test: tab rendering"
  ```

---

## Task 10: Android Accessibility Service

- [ ] Write failing test `test/services/device_agent_test.dart`:
  ```dart
  import 'package:flutter/services.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mobius_app/services/device_agent.dart';

  void main() {
    TestWidgetsFlutterBinding.ensureInitialized();

    late List<MethodCall> log;

    setUp(() {
      log = [];
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('com.mobius/device'),
        (call) async {
          log.add(call);
          return switch (call.method) {
            'openApp' => true,
            'readScreen' => 'Sample screen text',
            'tapElement' => true,
            _ => null,
          };
        },
      );
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('com.mobius/device'),
        null,
      );
    });

    test('openApp calls correct MethodChannel method with package name', () async {
      final agent = DeviceAgent();
      final result = await agent.openApp('com.whatsapp');
      expect(result, isTrue);
      expect(log.length, 1);
      expect(log[0].method, 'openApp');
      expect(log[0].arguments['packageName'], 'com.whatsapp');
    });

    test('readScreen returns string from MethodChannel', () async {
      final agent = DeviceAgent();
      final text = await agent.readScreen();
      expect(text, 'Sample screen text');
    });

    test('tapElement calls correct method with content description', () async {
      final agent = DeviceAgent();
      final result = await agent.tapElement('Submit button');
      expect(result, isTrue);
      expect(log[0].arguments['contentDesc'], 'Submit button');
    });
  }
  ```
- [ ] Run to confirm failure:
  ```
  flutter test test/services/device_agent_test.dart
  # Expected: Compilation error — DeviceAgent not found
  ```
- [ ] Write `lib/services/device_agent.dart`:
  ```dart
  import 'package:flutter/services.dart';

  class DeviceAgent {
    static const _channel = MethodChannel('com.mobius/device');

    Future<bool> openApp(String packageName) async {
      final result = await _channel.invokeMethod<bool>(
        'openApp',
        {'packageName': packageName},
      );
      return result ?? false;
    }

    Future<String> readScreen() async {
      final result = await _channel.invokeMethod<String>('readScreen');
      return result ?? '';
    }

    Future<bool> tapElement(String contentDesc) async {
      final result = await _channel.invokeMethod<bool>(
        'tapElement',
        {'contentDesc': contentDesc},
      );
      return result ?? false;
    }
  }
  ```
- [ ] Write `android/app/src/main/java/com/mobius/app/MobiusAccessibilityService.java`:
  ```java
  package com.mobius.app;

  import android.accessibilityservice.AccessibilityService;
  import android.accessibilityservice.AccessibilityServiceInfo;
  import android.content.Intent;
  import android.view.accessibility.AccessibilityEvent;
  import android.view.accessibility.AccessibilityNodeInfo;

  import io.flutter.embedding.engine.FlutterEngine;
  import io.flutter.plugin.common.MethodChannel;

  import java.util.ArrayList;
  import java.util.List;

  public class MobiusAccessibilityService extends AccessibilityService {

      private static final String CHANNEL = "com.mobius/device";
      private static MobiusAccessibilityService instance;

      public static MobiusAccessibilityService getInstance() {
          return instance;
      }

      @Override
      public void onServiceConnected() {
          instance = this;
          AccessibilityServiceInfo info = new AccessibilityServiceInfo();
          info.eventTypes = AccessibilityEvent.TYPES_ALL_MASK;
          info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
          info.flags = AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
          setServiceInfo(info);
      }

      @Override
      public void onAccessibilityEvent(AccessibilityEvent event) {
          // Forward accessibility events to Flutter if needed
      }

      @Override
      public void onInterrupt() {}

      /**
       * Returns all text visible in the current window's accessibility nodes.
       */
      public String readScreen() {
          AccessibilityNodeInfo root = getRootInActiveWindow();
          if (root == null) return "";
          List<String> texts = new ArrayList<>();
          collectText(root, texts);
          return String.join("\n", texts);
      }

      private void collectText(AccessibilityNodeInfo node, List<String> out) {
          if (node == null) return;
          if (node.getText() != null) out.add(node.getText().toString());
          for (int i = 0; i < node.getChildCount(); i++) {
              collectText(node.getChild(i), out);
          }
      }

      /**
       * Finds a node by content description and performs a click action.
       */
      public boolean tapElement(String contentDesc) {
          AccessibilityNodeInfo root = getRootInActiveWindow();
          if (root == null) return false;
          List<AccessibilityNodeInfo> nodes =
              root.findAccessibilityNodeInfosByText(contentDesc);
          if (!nodes.isEmpty()) {
              return nodes.get(0).performAction(AccessibilityNodeInfo.ACTION_CLICK);
          }
          return false;
      }

      /**
       * Launches an app by package name.
       */
      public boolean openApp(String packageName) {
          Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
          if (intent == null) return false;
          intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
          startActivity(intent);
          return true;
      }
  }
  ```
- [ ] Update `android/app/src/main/AndroidManifest.xml` — add inside `<application>`:
  ```xml
  <service
      android:name=".MobiusAccessibilityService"
      android:exported="true"
      android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
      android:label="@string/app_name">
      <intent-filter>
          <action android:name="android.accessibilityservice.AccessibilityService" />
      </intent-filter>
      <meta-data
          android:name="android.accessibilityservice"
          android:resource="@xml/accessibility_service_config" />
  </service>
  ```
- [ ] Create `android/app/src/main/res/xml/accessibility_service_config.xml`:
  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <accessibility-service
      xmlns:android="http://schemas.android.com/apk/res/android"
      android:accessibilityEventTypes="typeAllMask"
      android:accessibilityFeedbackType="feedbackGeneric"
      android:accessibilityFlags="flagRetrieveInteractiveWindows"
      android:canRetrieveWindowContent="true"
      android:description="@string/accessibility_service_description" />
  ```
- [ ] Add string to `android/app/src/main/res/values/strings.xml`:
  ```xml
  <string name="accessibility_service_description">Mobius uses accessibility to automate tasks on your device.</string>
  ```
- [ ] Update `android/app/src/main/java/com/mobius/app/MainActivity.java` (or `MainActivity.kt`) to register the MethodChannel and delegate to `MobiusAccessibilityService`:
  ```java
  // In configureFlutterEngine:
  new MethodChannel(flutterEngine.getDartExecutor().getBinaryMessenger(), "com.mobius/device")
      .setMethodCallHandler((call, result) -> {
          MobiusAccessibilityService svc = MobiusAccessibilityService.getInstance();
          if (svc == null) {
              result.error("SERVICE_UNAVAILABLE", "Enable Accessibility Service first", null);
              return;
          }
          switch (call.method) {
              case "openApp":
                  result.success(svc.openApp(call.argument("packageName")));
                  break;
              case "readScreen":
                  result.success(svc.readScreen());
                  break;
              case "tapElement":
                  result.success(svc.tapElement(call.argument("contentDesc")));
                  break;
              default:
                  result.notImplemented();
          }
      });
  ```
- [ ] Run test:
  ```
  flutter test test/services/device_agent_test.dart
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/services/device_agent.dart android/ test/services/device_agent_test.dart
  git commit -m "feat: Android Accessibility Service + DeviceAgent MethodChannel; test: openApp/readScreen/tapElement"
  ```

---

## Task 11: Model selector in chat

- [ ] Write failing test `test/features/chat/model_selector_test.dart`:
  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_riverpod/flutter_riverpod.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:mobius_app/features/chat/chat_screen.dart';
  import 'package:mobius_app/features/chat/chat_provider.dart';
  import 'package:mobius_app/features/settings/settings_provider.dart';
  import 'package:mobius_app/shared/models/message.dart';

  void main() {
    testWidgets('Claude chip is disabled when no Claude API key is set', (tester) async {
      // Settings with no claude key
      final container = ProviderContainer(
        overrides: [
          settingsNotifierProvider.overrideWith(() => _NoClaudeKeySettings()),
          chatNotifierProvider.overrideWith(() => _EmptyChatNotifier()),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: ChatScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // Find the Claude chip — should be rendered but shown as disabled/locked
      final claudeChip = find.widgetWithText(FilterChip, 'claude-sonnet');
      expect(claudeChip, findsOneWidget);
      final chip = tester.widget<FilterChip>(claudeChip);
      expect(chip.onSelected, isNull); // disabled
    });

    testWidgets('Gemini chip is enabled when selected model', (tester) async {
      final container = ProviderContainer(
        overrides: [
          settingsNotifierProvider.overrideWith(() => _NoClaudeKeySettings()),
          chatNotifierProvider.overrideWith(() => _EmptyChatNotifier()),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: ChatScreen()),
        ),
      );
      await tester.pumpAndSettle();

      final geminiChip = find.widgetWithText(FilterChip, 'gemini-flash');
      expect(geminiChip, findsOneWidget);
      final chip = tester.widget<FilterChip>(geminiChip);
      expect(chip.onSelected, isNotNull); // enabled
    });
  }

  class _NoClaudeKeySettings extends SettingsNotifier {
    @override
    SettingsState build() => const SettingsState(
          apiKeys: {AiModel.geminiFlash: 'some-key'},
        );
  }

  class _EmptyChatNotifier extends ChatNotifier {
    @override
    Future<List<Message>> build() async => [];
  }
  ```
- [ ] Run to confirm failure:
  ```
  flutter test test/features/chat/model_selector_test.dart
  # Expected: FilterChip not found (not yet in ChatScreen)
  ```
- [ ] Update `lib/features/chat/chat_screen.dart` — add model selector chip row above the text field:
  ```dart
  // Add to the Column in build(), above the Padding with TextField:
  Consumer(
    builder: (context, ref, _) {
      final settings = ref.watch(settingsNotifierProvider);
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Row(
          children: AiModel.values.map((model) {
            final hasKey = settings.hasApiKey(model);
            final isSelected = _selectedModel == model.label;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Text(model.label),
                selected: isSelected,
                onSelected: hasKey
                    ? (selected) {
                        if (selected) {
                          setState(() => _selectedModel = model.label);
                        }
                      }
                    : null,
                avatar: hasKey ? null : const Icon(Icons.lock, size: 14),
                selectedColor: const Color(0xFF00B4D8),
              ),
            );
          }).toList(),
        ),
      );
    },
  ),
  ```
- [ ] Add `import '../settings/settings_provider.dart';` to `chat_screen.dart`
- [ ] Run tests:
  ```
  flutter test test/features/chat/model_selector_test.dart
  # Expected: All tests passed.
  ```
- [ ] Run full test suite:
  ```
  flutter test
  # Expected: All tests passed.
  ```
- [ ] Commit:
  ```
  git add lib/features/chat/chat_screen.dart test/features/chat/model_selector_test.dart
  git commit -m "feat: model selector chips in chat screen with lock for missing API keys; test: disabled state"
  ```

---

## Shared widgets (implement alongside tasks as needed)

### `lib/shared/widgets/primary_button.dart`
```dart
import 'package:flutter/material.dart';

class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;

  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Text(label),
    );
  }
}
```

### `lib/shared/widgets/loading_overlay.dart`
```dart
import 'package:flutter/material.dart';

class LoadingOverlay extends StatelessWidget {
  final bool isLoading;
  final Widget child;

  const LoadingOverlay({super.key, required this.isLoading, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isLoading)
          const ColoredBox(
            color: Colors.black45,
            child: Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }
}
```

---

## Final verification checklist

- [ ] `flutter test` — all tests green
- [ ] `flutter analyze` — no errors or warnings
- [ ] `flutter build apk --debug` — APK builds successfully
- [ ] Manual smoke test on Android emulator:
  - [ ] App launches on Android emulator
  - [ ] Login screen appears when not authenticated
  - [ ] Successful login navigates to Chat screen
  - [ ] Chat screen sends message to backend and streams response
  - [ ] Bottom nav tabs all navigate correctly
  - [ ] Settings: server URL, model, API keys save
  - [ ] Settings: "Test Connection" shows snackbar
  - [ ] Integrations: list loads and Connect button opens browser
  - [ ] Automations: list loads, FAB opens sheet, swipe deletes
  - [ ] Accessibility: "Enable Accessibility Service" opens Android settings

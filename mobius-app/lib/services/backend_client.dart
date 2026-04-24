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
        // Skip ngrok browser warning page
        options.headers['ngrok-skip-browser-warning'] = 'true';
        handler.next(options);
      },
    ));
  }

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _dio.get('$baseUrl$path', queryParameters: queryParameters);

  Future<Response> post(String path, {dynamic data}) =>
      _dio.post('$baseUrl$path', data: data);

  Future<Response> put(String path, {dynamic data}) =>
      _dio.put('$baseUrl$path', data: data);

  Future<Response> patch(String path, {dynamic data}) =>
      _dio.patch('$baseUrl$path', data: data);

  Future<Response> delete(String path) => _dio.delete('$baseUrl$path');
}

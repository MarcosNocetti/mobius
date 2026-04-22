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

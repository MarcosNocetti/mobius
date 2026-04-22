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

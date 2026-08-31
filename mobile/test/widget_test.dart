import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/app.dart';

void main() {
  testWidgets('App starts at the splash screen, then routes to onboarding for fresh launch', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: App()));

    expect(find.text('Verifying session...'), findsOneWidget);

    // Session restore and onboarding flag read from storage
    await tester.runAsync(() async {
      await Future.delayed(const Duration(milliseconds: 300));
    });
    await tester.pump();
    await tester.pump();
    await tester.pump();

    // On fresh launch without prior completion, routes to intro onboarding walkthrough
    expect(find.byType(PageView), findsOneWidget);
  });
}

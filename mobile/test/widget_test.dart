import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/app.dart';
import 'package:mobile/features/splash/presentation/splash_controller.dart';
import 'package:mobile/features/splash/presentation/splash_screen.dart';

void main() {
  testWidgets(
    'App starts at the animated splash screen, then routes to onboarding for fresh launch',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            splashControllerProvider.overrideWith(
              (ref) => SplashController(autoCompleteInTest: false),
            ),
          ],
          child: const App(),
        ),
      );

      // Splash Screen is actively rendering
      expect(find.byType(SplashScreen), findsOneWidget);
      expect(find.text('SEVO'), findsOneWidget);
      expect(find.text('WORKFORCE'), findsOneWidget);

      // Session restore and onboarding flag read from storage
      await tester.runAsync(() async {
        await Future.delayed(const Duration(milliseconds: 300));
      });

      // Pump through the 7500ms splash animation duration
      await tester.pump(const Duration(milliseconds: 7600));
      await tester.pumpAndSettle();

      // On fresh launch without prior completion, routes to intro onboarding walkthrough
      expect(find.byType(PageView), findsOneWidget);
    },
  );
}

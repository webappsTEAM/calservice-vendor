import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/theme/app_motion.dart';
import 'package:mobile/features/splash/presentation/splash_controller.dart';
import 'package:mobile/features/splash/presentation/splash_screen.dart';

void main() {
  testWidgets('SplashScreen renders branding and completes animation', (
    WidgetTester tester,
  ) async {
    final container = ProviderContainer(
      overrides: [
        splashControllerProvider.overrideWith(
          (ref) => SplashController(autoCompleteInTest: false),
        ),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: SplashScreen(),
        ),
      ),
    );

    // Initial render
    expect(find.byType(SplashScreen), findsOneWidget);
    expect(find.text('SEVO'), findsOneWidget);
    expect(find.text('WORKFORCE'), findsOneWidget);
    expect(find.byType(Image), findsOneWidget);
    expect(container.read(splashControllerProvider), isFalse);

    // Advance halfway through animation (3700ms)
    await tester.pump(const Duration(milliseconds: 3700));
    expect(container.read(splashControllerProvider), isFalse);

    // Advance to completion (another 3900ms)
    await tester.pump(const Duration(milliseconds: 3900));
    await tester.pumpAndSettle();
    expect(container.read(splashControllerProvider), isTrue);
  });

  testWidgets('SplashScreen completes immediately when reduced motion is enabled', (
    WidgetTester tester,
  ) async {
    AppMotion.configure(reducedMotion: true);
    addTearDown(() => AppMotion.configure(reducedMotion: false));

    final container = ProviderContainer(
      overrides: [
        splashControllerProvider.overrideWith(
          (ref) => SplashController(autoCompleteInTest: false),
        ),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: SplashScreen(),
        ),
      ),
    );

    await tester.pump();
    expect(container.read(splashControllerProvider), isTrue);
  });
}

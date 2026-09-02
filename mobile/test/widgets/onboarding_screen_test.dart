import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/features/onboarding/data/onboarding_storage.dart';
import 'package:mobile/features/onboarding/presentation/onboarding_screen.dart';
import 'package:mobile/routing/app_routes.dart';

class InMemoryOnboardingStorage extends OnboardingStorage {
  String? _value;

  @override
  Future<bool> hasCompletedOnboarding() async => _value == 'true';

  @override
  Future<void> setOnboardingCompleted() async => _value = 'true';

  @override
  Future<void> clear() async => _value = null;
}

void main() {
  Widget buildTestableOnboarding({
    Size size = const Size(390, 844),
    OnboardingStorage? storage,
    GoRouter? customRouter,
  }) {
    final effectiveStorage = storage ?? InMemoryOnboardingStorage();
    final effectiveRouter = customRouter ??
        GoRouter(
          initialLocation: AppRoutes.onboarding,
          routes: [
            GoRoute(
              path: AppRoutes.onboarding,
              builder: (context, state) => MediaQuery(
                data: MediaQueryData(size: size),
                child: const OnboardingScreen(),
              ),
            ),
            GoRoute(
              path: AppRoutes.login,
              builder: (context, state) => const Scaffold(
                body: Text('Mock Login Screen'),
              ),
            ),
          ],
        );

    return ProviderScope(
      overrides: [
        onboardingStorageProvider.overrideWithValue(effectiveStorage),
      ],
      child: MaterialApp.router(
        routerConfig: effectiveRouter,
      ),
    );
  }

  group('OnboardingScreen Behavior Tests (SKIP on All Pages & Swipe Disabled)', () {
    testWidgets('1. Page 1 displays visible SKIP option', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      expect(find.text('SKIP'), findsOneWidget);
      expect(find.byKey(const Key('onboarding_skip_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);
    });

    testWidgets('2. Page 2 displays visible SKIP option', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // Navigate to Page 2 via NEXT button
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      expect(find.text('SKIP'), findsOneWidget);
      expect(find.byKey(const Key('onboarding_skip_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
    });

    testWidgets('3. Page 3 displays visible SKIP option', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // Navigate to Page 3 via NEXT button twice
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      expect(find.text('SKIP'), findsOneWidget);
      expect(find.byKey(const Key('onboarding_skip_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_get_started_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_view_job_button')), findsOneWidget);
    });

    testWidgets('4. Tapping SKIP from Page 1 completes onboarding and navigates to login', (tester) async {
      final storage = InMemoryOnboardingStorage();
      await tester.pumpWidget(buildTestableOnboarding(storage: storage));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isFalse);

      await tester.tap(find.byKey(const Key('onboarding_skip_button')));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isTrue);
      expect(find.text('Mock Login Screen'), findsOneWidget);
    });

    testWidgets('5. Tapping SKIP from Page 2 completes onboarding and navigates to login', (tester) async {
      final storage = InMemoryOnboardingStorage();
      await tester.pumpWidget(buildTestableOnboarding(storage: storage));
      await tester.pumpAndSettle();

      // Go to Page 2
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('onboarding_skip_button')));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isTrue);
      expect(find.text('Mock Login Screen'), findsOneWidget);
    });

    testWidgets('6. Tapping SKIP from Page 3 completes onboarding and navigates to login', (tester) async {
      final storage = InMemoryOnboardingStorage();
      await tester.pumpWidget(buildTestableOnboarding(storage: storage));
      await tester.pumpAndSettle();

      // Go to Page 3
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('onboarding_skip_button')));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isTrue);
      expect(find.text('Mock Login Screen'), findsOneWidget);
    });

    testWidgets('7. Tapping NEXT moves Page 1 -> Page 2 and Page 2 -> Page 3', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // Page 1: only next exists, no back
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);

      // Tap NEXT to Page 2
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);

      // Tap NEXT to Page 3
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('onboarding_get_started_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_view_job_button')), findsOneWidget);

      // Tap Back to Page 2
      await tester.tap(find.byKey(const Key('onboarding_back_button')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_get_started_button')), findsNothing);
    });

    testWidgets('8. Horizontal swipe/drag is COMPLETELY DISABLED and does NOT change page', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // On Page 1
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);

      // Try swiping left (attempting to go forward to Page 2)
      await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
      await tester.pumpAndSettle();

      // Page must NOT have changed: still on Page 1 (no back button)
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);

      // Try dragging left slowly
      await tester.drag(find.byType(PageView), const Offset(-300, 0));
      await tester.pumpAndSettle();

      // Still on Page 1
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);

      // Move to Page 2 using NEXT button
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);

      // Try swiping right (attempting to go backward to Page 1)
      await tester.fling(find.byType(PageView), const Offset(400, 0), 1000);
      await tester.pumpAndSettle();

      // Still on Page 2
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);

      // Try swiping left (attempting to go forward to Page 3)
      await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
      await tester.pumpAndSettle();

      // Still on Page 2 (get_started should NOT appear)
      expect(find.byKey(const Key('onboarding_get_started_button')), findsNothing);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
    });

    testWidgets('9. Page 3 View Job button completes onboarding and routes to login', (tester) async {
      final storage = InMemoryOnboardingStorage();
      await tester.pumpWidget(buildTestableOnboarding(storage: storage));
      await tester.pumpAndSettle();

      // Navigate to Page 3
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      // Tap View Job button
      await tester.tap(find.byKey(const Key('onboarding_view_job_button')));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isTrue);
      expect(find.text('Mock Login Screen'), findsOneWidget);
    });

    testWidgets('10. Page 3 Get Started button completes onboarding and routes to login', (tester) async {
      final storage = InMemoryOnboardingStorage();
      await tester.pumpWidget(buildTestableOnboarding(storage: storage));
      await tester.pumpAndSettle();

      // Navigate to Page 3
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      // Tap Get Started button
      await tester.tap(find.byKey(const Key('onboarding_get_started_button')));
      await tester.pumpAndSettle();

      expect(await storage.hasCompletedOnboarding(), isTrue);
      expect(find.text('Mock Login Screen'), findsOneWidget);
    });
  });

  group('OnboardingScreen Responsive Layout Tests', () {
    const testSizes = [
      Size(320, 568), // Compact / Small Android
      Size(360, 640), // Classic Android 16:9
      Size(390, 844), // Modern Standard
      Size(412, 915), // Large Android
      Size(480, 800), // Wide Android
    ];

    for (final size in testSizes) {
      testWidgets('renders all 3 pages cleanly at ${size.width}x${size.height} with 0 overflow', (tester) async {
        await tester.pumpWidget(buildTestableOnboarding(size: size));
        await tester.pumpAndSettle();

        // Page 1
        expect(tester.takeException(), isNull);
        expect(find.text('SKIP'), findsOneWidget);

        // Page 2
        await tester.tap(find.byKey(const Key('onboarding_next_button')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('SKIP'), findsOneWidget);

        // Page 3
        await tester.tap(find.byKey(const Key('onboarding_next_button')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('SKIP'), findsOneWidget);
      });
    }
  });
}


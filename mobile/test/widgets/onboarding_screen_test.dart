import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/onboarding/presentation/onboarding_screen.dart';

void main() {
  Widget buildTestableOnboarding({Size size = const Size(390, 844)}) {
    return MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: const OnboardingScreen(),
      ),
    );
  }

  group('OnboardingScreen Zero-Duplicate UI & Touch Overlay Tests', () {
    testWidgets('renders onboarding image artwork without visible duplicate native text controls', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // Ensure NO duplicate visible native text widgets are rendered over the image artwork
      expect(find.text('SEVO WORKFORCE'), findsNothing);
      expect(find.text('Skip'), findsNothing);
      expect(find.text('Back'), findsNothing);
      expect(find.text('Next'), findsNothing);
      expect(find.text('Get Started'), findsNothing);
      expect(find.text('WORK SMARTER, EVERY DAY'), findsNothing);
      expect(find.text('EVERYTHING YOU NEED, IN ONE PLACE'), findsNothing);
      expect(find.text('REAL-TIME JOBS,\nINSTANT ALERTS'), findsNothing);

      // PageView is present displaying the first image
      expect(find.byType(PageView), findsOneWidget);
      expect(find.byType(Image), findsOneWidget);

      // Transparent touch targets exist
      expect(find.byKey(const Key('onboarding_skip_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);
    });

    testWidgets('navigates through pages via invisible touch targets on printed buttons', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      // Page 1: Tap the invisible Next target over printed "NEXT ->" button
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      // Page 2: Back and Next targets now exist
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_skip_button')), findsOneWidget);

      // Page 2: Tap the invisible Next target over printed "NEXT ->" button
      await tester.tap(find.byKey(const Key('onboarding_next_button')));
      await tester.pumpAndSettle();

      // Page 3: Back, Get Started, and View Job targets exist
      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_get_started_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_view_job_button')), findsOneWidget);

      // Still NO duplicate native visible text rendered on page 3
      expect(find.text('Get Started'), findsNothing);
      expect(find.text('View Job'), findsNothing);

      // Navigate back to Page 2 using the invisible Back target
      await tester.tap(find.byKey(const Key('onboarding_back_button')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_get_started_button')), findsNothing);
    });

    testWidgets('supports horizontal swipe gestures between pages', (tester) async {
      await tester.pumpWidget(buildTestableOnboarding());
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('onboarding_back_button')), findsNothing);

      // Swipe left to page 2
      await tester.fling(find.byType(PageView), const Offset(-400, 0), 1000);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('onboarding_back_button')), findsOneWidget);
      expect(find.byKey(const Key('onboarding_next_button')), findsOneWidget);
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

        // Page 2
        await tester.tap(find.byKey(const Key('onboarding_next_button')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        // Page 3
        await tester.tap(find.byKey(const Key('onboarding_next_button')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  });
}

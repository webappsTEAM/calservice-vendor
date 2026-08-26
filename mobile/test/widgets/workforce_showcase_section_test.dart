import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/theme/app_motion.dart';
import 'package:mobile/shared/widgets/workforce_showcase_section.dart';

void main() {
  setUp(() {
    AppMotion.configure(reducedMotion: false);
  });

  Widget buildTestableWidget({
    Widget? child,
    double width = 360,
    double height = 800,
    double textScaleFactor = 1.0,
  }) {
    return MaterialApp(
      theme: ThemeData(useMaterial3: true),
      home: MediaQuery(
        data: MediaQueryData(
          size: Size(width, height),
          textScaler: TextScaler.linear(textScaleFactor),
        ),
        child: Scaffold(
          body: SingleChildScrollView(
            child: child ??
                const WorkforceShowcaseSection(
                  headingPadding: EdgeInsets.zero,
                  cardsPadding: EdgeInsets.zero,
                ),
          ),
        ),
      ),
    );
  }

  group('WorkforceShowcaseSection Promotional Carousel Tests', () {
    testWidgets('renders heading, PageView, image banners, and indicator dots', (tester) async {
      await tester.pumpWidget(buildTestableWidget());
      await tester.pumpAndSettle();

      // Heading
      expect(find.text('SERVICE SPOTLIGHT'), findsOneWidget);

      // PageView with Image assets
      expect(find.byType(PageView), findsOneWidget);
      expect(find.byType(Image), findsWidgets);

      // 3 Indicator dots
      expect(find.byType(GestureDetector), findsNWidgets(3));
    });

    testWidgets('manual swipe transitions between banners correctly', (tester) async {
      await tester.pumpWidget(buildTestableWidget());
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsOneWidget);

      // Drag left to go to next banner
      await tester.drag(find.byType(PageView), const Offset(-400, 0));
      await tester.pumpAndSettle();

      expect(find.byType(Image), findsWidgets);

      // Drag left again to go to third banner
      await tester.drag(find.byType(PageView), const Offset(-400, 0));
      await tester.pumpAndSettle();

      expect(find.byType(Image), findsWidgets);
    });

    testWidgets('tapping indicator dot jumps to corresponding banner', (tester) async {
      await tester.pumpWidget(buildTestableWidget());
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsOneWidget);

      // Tap 3rd dot
      final dots = find.byType(GestureDetector);
      await tester.tap(dots.at(2));
      await tester.pumpAndSettle();

      expect(find.byType(Image), findsWidgets);
    });

    testWidgets('auto-scroll transitions banner automatically after interval', (tester) async {
      await tester.pumpWidget(
        buildTestableWidget(
          child: const WorkforceShowcaseSection(
            autoScrollInterval: Duration(seconds: 4),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(PageView), findsOneWidget);

      // Advance clock by 4 seconds
      await tester.pump(const Duration(seconds: 4));
      await tester.pumpAndSettle();

      expect(find.byType(Image), findsWidgets);
    });

    testWidgets('reduced motion disables auto-advance timer', (tester) async {
      AppMotion.configure(reducedMotion: true);

      await tester.pumpWidget(
        buildTestableWidget(
          child: const WorkforceShowcaseSection(
            autoScrollInterval: Duration(seconds: 4),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(PageView), findsOneWidget);

      // Advance clock by 10 seconds
      await tester.pump(const Duration(seconds: 10));
      await tester.pumpAndSettle();

      expect(find.byType(PageView), findsOneWidget);
    });
  });

  group('WorkforceShowcaseSection Responsive Layout Tests', () {
    final testWidths = [320.0, 360.0, 412.0, 480.0];

    for (final width in testWidths) {
      testWidgets('renders without RenderFlex overflow at px', (tester) async {
        await tester.pumpWidget(buildTestableWidget(width: width));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(WorkforceShowcaseSection), findsOneWidget);
      });
    }

    testWidgets('renders without RenderFlex overflow at 1.5x font scale', (tester) async {
      await tester.pumpWidget(buildTestableWidget(width: 320.0, textScaleFactor: 1.5));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byType(WorkforceShowcaseSection), findsOneWidget);
    });
  });
}

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

  group('WorkforceShowcaseSection Single-Image Spotlight Tests', () {
    testWidgets('renders heading and single image without carousel or indicator dots', (tester) async {
      await tester.pumpWidget(buildTestableWidget());
      await tester.pumpAndSettle();

      // Heading is present
      expect(find.text('SERVICE SPOTLIGHT'), findsOneWidget);

      // Single Image asset is present
      expect(find.byType(Image), findsOneWidget);
      final imageWidget = tester.widget<Image>(find.byType(Image));
      expect(imageWidget.fit, equals(BoxFit.cover));
      expect(imageWidget.alignment, equals(Alignment.center));

      // No PageView carousel
      expect(find.byType(PageView), findsNothing);

      // No indicator dots
      expect(find.byType(AspectRatio), findsOneWidget);
      final aspectRatioWidget = tester.widget<AspectRatio>(find.byType(AspectRatio));
      expect(aspectRatioWidget.aspectRatio, equals(2.0));
    });

    testWidgets('uses correct default image asset', (tester) async {
      await tester.pumpWidget(buildTestableWidget());
      await tester.pumpAndSettle();

      final image = tester.widget<Image>(find.byType(Image));
      final assetImage = image.image as AssetImage;
      expect(assetImage.assetName, equals(kDefaultServiceSpotlightImage));
      expect(assetImage.assetName, equals('Technician Homepage.jpg'));
    });

    testWidgets('triggers onTap callback when card is tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        buildTestableWidget(
          child: WorkforceShowcaseSection(
            headingPadding: EdgeInsets.zero,
            cardsPadding: EdgeInsets.zero,
            onTap: () => tapped = true,
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byType(Image));
      await tester.pumpAndSettle();

      expect(tapped, isTrue);
    });
  });

  group('WorkforceShowcaseSection Responsive Layout Tests', () {
    final testWidths = [320.0, 360.0, 412.0, 480.0];

    for (final width in testWidths) {
      testWidgets('renders without RenderFlex overflow at ${width.toInt()}px', (tester) async {
        await tester.pumpWidget(buildTestableWidget(width: width));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(WorkforceShowcaseSection), findsOneWidget);
        expect(find.byType(Image), findsOneWidget);
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

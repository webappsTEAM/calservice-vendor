import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_scorecard.dart';
import 'package:mobile/features/admin/presentation/scorecards/admin_scorecards_providers.dart';
import 'package:mobile/features/admin/presentation/scorecards/admin_scorecards_screen.dart';

void main() {
  final sampleScorecards = [
    AdminScorecardItem(
      employeeId: 1,
      employeeName: 'Ramesh Kumar',
      tier: 'GOLD',
      averageRating: 4.8,
      csatAverage: 4.9,
      slaScore: 98.5,
      ratingCount: 24,
      slaMetCount: 23,
      slaBreachCount: 1,
      lastRecalculatedAt: DateTime(2026, 9, 8),
    ),
    AdminScorecardItem(
      employeeId: 2,
      employeeName: 'Suresh Raina',
      tier: 'SILVER',
      averageRating: 4.2,
      csatAverage: 4.1,
      slaScore: 89.0,
      ratingCount: 15,
      slaMetCount: 13,
      slaBreachCount: 2,
      lastRecalculatedAt: DateTime(2026, 9, 7),
    ),
  ];

  Widget buildTestWidget({
    List<AdminScorecardItem>? scorecards,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null)
          adminScorecardsListProvider
              .overrideWith((ref) => Future.error(error))
        else
          adminScorecardsListProvider
              .overrideWith((ref) => Future.value(scorecards ?? sampleScorecards)),
      ],
      child: const MaterialApp(
        home: AdminScorecardsScreen(),
      ),
    );
  }

  group('AdminScorecardsScreen Widget Tests', () {
    testWidgets('renders screen header, count, tier chips, and cards', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Header
      expect(find.text('Scorecards'), findsOneWidget);
      expect(
        find.text(
          'Rating, CSAT, and SLA compliance metrics across the technician workforce.',
        ),
        findsOneWidget,
      );
      expect(find.text('Refresh'), findsOneWidget);

      // Main Section Header
      expect(find.text('Worker & Provider Scorecards (2)'), findsOneWidget);

      // Filter chips
      expect(find.text('All Tiers'), findsOneWidget);
      expect(find.text('Gold'), findsOneWidget);
      expect(find.text('Silver'), findsOneWidget);
      expect(find.text('Bronze'), findsOneWidget);
      expect(find.text('Unrated'), findsOneWidget);

      // Cards
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Worker ID: #1'), findsOneWidget);
      expect(find.text('GOLD'), findsOneWidget);
      expect(find.text('4.8'), findsOneWidget);
      expect(find.text('(24)'), findsOneWidget);
      expect(find.text('98.5%'), findsOneWidget);

      expect(find.text('Suresh Raina'), findsOneWidget);
      expect(find.text('Worker ID: #2'), findsOneWidget);
      expect(find.text('SILVER'), findsOneWidget);
      expect(find.text('89.0%'), findsOneWidget);
    });

    testWidgets('tier chip filter filters scorecards list', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Gold'));
      await tester.pumpAndSettle();

      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Raina'), findsNothing);
    });

    testWidgets('shows exact empty state when no employees/scorecards exist', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget(scorecards: []));
      await tester.pumpAndSettle();

      expect(find.text('Worker & Provider Scorecards (0)'), findsOneWidget);
      expect(
        find.text('No employees found for this company yet.'),
        findsOneWidget,
      );
    });

    testWidgets('shows error state with retry on failure', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        buildTestWidget(error: Exception('Scorecards fetch failure')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load scorecards'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Admin Scorecards Responsive Layout Tests', () {
    for (final width in [320.0, 360.0, 390.0, 412.0]) {
      testWidgets('renders without overflow at ${width}px width', (
        WidgetTester tester,
      ) async {
        tester.view.physicalSize = Size(width, 1000);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(buildTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Scorecards'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

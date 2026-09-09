import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/estimates/domain/quote_estimate.dart';
import 'package:mobile/features/estimates/presentation/estimates_providers.dart';
import 'package:mobile/features/estimates/presentation/estimates_screen.dart';

void main() {
  final sampleQuotes = [
    QuoteEstimate(
      id: 1,
      quoteNumber: 'QT-2026-0001',
      jobId: 42,
      serviceName: 'AC Copper Pipe Replacement',
      customerName: 'Rohit Sharma',
      brand: 'Daikin',
      status: 'SENT_TO_CUSTOMER',
      grandTotal: 4500.0,
      laborCost: 1500.0,
      materialsCost: 3000.0,
      taxAmount: 0.0,
      discountAmount: 0.0,
      notes: 'Includes 10ft copper pipe and gas charge.',
      createdAt: DateTime.parse('2026-08-25T10:00:00Z'),
      itemsCount: 2,
    ),
    QuoteEstimate(
      id: 2,
      quoteNumber: 'QT-2026-0002',
      jobId: 43,
      serviceName: 'Compressor Overhaul',
      customerName: 'Ananya Roy',
      brand: 'Voltas',
      status: 'CUSTOMER_ACCEPTED',
      grandTotal: 12000.0,
      laborCost: 4000.0,
      materialsCost: 8000.0,
      taxAmount: 0.0,
      discountAmount: 0.0,
      notes: 'Replacement of rotary compressor unit.',
      createdAt: DateTime.parse('2026-08-26T14:30:00Z'),
      itemsCount: 3,
    ),
  ];

  group('EstimatesScreen Widget Tests', () {
    testWidgets('renders screen title, context badge, refresh action, metrics, search, date, and quotes list', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            quotesListProvider.overrideWith((ref) => Future.value(sampleQuotes)),
          ],
          child: const MaterialApp(
            home: EstimatesScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Screen Header & Titles
      expect(find.text('AC Estimations'), findsOneWidget);
      expect(find.text('Vendor Portal'), findsOneWidget);
      expect(find.text('Refresh'), findsOneWidget);
      expect(find.text('AC Inspection & Quotation Manager'), findsOneWidget);
      expect(
        find.text('Manage AC diagnostic leads, on-site technician inspections, and formal versioned quotations.'),
        findsOneWidget,
      );

      // Metrics strip
      expect(find.text('Total Leads'), findsOneWidget);
      expect(find.text('New Requests'), findsWidgets);
      expect(find.text('Quotation Sent'), findsWidgets);
      expect(find.text('Completed'), findsWidgets);

      // Filter chips in exact required order
      expect(find.text('All Leads'), findsOneWidget);
      expect(find.text('New Requests'), findsWidgets);
      expect(find.text('Assigned'), findsOneWidget);
      expect(find.text('In Progress'), findsOneWidget);
      expect(find.text('Quotation Sent'), findsWidgets);
      expect(find.text('Completed'), findsWidgets);

      // Search & Date Placeholders
      expect(find.text('Search customer, ID, brand ...'), findsOneWidget);
      expect(find.text('dd/mm/yyyy'), findsOneWidget);

      // Quote Cards
      expect(find.text('QT-2026-0001'), findsOneWidget);
      expect(find.text('AC Copper Pipe Replacement'), findsOneWidget);
      expect(find.text('Rohit Sharma'), findsOneWidget);
      expect(find.text('₹4500.00'), findsOneWidget);

      expect(find.text('QT-2026-0002'), findsOneWidget);
      expect(find.text('Compressor Overhaul'), findsOneWidget);
      expect(find.text('Ananya Roy'), findsOneWidget);
      expect(find.text('₹12000.00'), findsOneWidget);
    });

    testWidgets('renders contextual empty state when no quotations exist', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            quotesListProvider.overrideWith((ref) => Future.value(<QuoteEstimate>[])),
          ],
          child: const MaterialApp(
            home: EstimatesScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No Estimation Leads Found'), findsOneWidget);
      expect(
        find.text('No matching AC inspection requests found for current filter criteria.'),
        findsOneWidget,
      );
    });

    testWidgets('renders error state and retry button on fetch failure', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            quotesListProvider.overrideWith((ref) => throw Exception('Network timeout')),
          ],
          child: const MaterialApp(
            home: EstimatesScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Request failed'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('tapping refresh button reloads data', (tester) async {
      int fetchCount = 0;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            quotesListProvider.overrideWith((ref) {
              fetchCount++;
              return Future.value(sampleQuotes);
            }),
          ],
          child: const MaterialApp(
            home: EstimatesScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(fetchCount, 1);

      await tester.tap(find.text('Refresh'));
      await tester.pumpAndSettle();

      expect(fetchCount, greaterThanOrEqualTo(2));
    });

    const phoneWidths = [
      ('Small Phone (320px)', 320.0, 640.0),
      ('Standard Phone (360px)', 360.0, 780.0),
      ('Modern Phone (390px)', 390.0, 844.0),
      ('Large Phone (412px)', 412.0, 915.0),
    ];

    for (final (name, width, height) in phoneWidths) {
      testWidgets('$name renders EstimatesScreen without overflow', (tester) async {
        tester.view.physicalSize = Size(width * 2, height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());

        FlutterErrorDetails? caughtDetails;
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (details) => caughtDetails = details;

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              quotesListProvider.overrideWith((ref) => Future.value(sampleQuotes)),
            ],
            child: const MaterialApp(
              home: EstimatesScreen(),
            ),
          ),
        );
        await tester.pumpAndSettle();

        FlutterError.onError = originalOnError;
        expect(caughtDetails, isNull, reason: caughtDetails?.summary.toString());
        expect(find.text('AC Inspection & Quotation Manager'), findsOneWidget);
        expect(find.text('Vendor Portal'), findsOneWidget);
        expect(find.text('Refresh'), findsOneWidget);
      });
    }
  });
}

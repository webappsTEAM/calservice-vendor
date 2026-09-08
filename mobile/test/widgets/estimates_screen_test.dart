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
    testWidgets('renders screen title, metrics, search, and quotes list', (tester) async {
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

      // Screen Header
      expect(find.text('Estimates & Quotes'), findsOneWidget);
      expect(find.text('Estimates & Quotations'), findsOneWidget);

      // Metrics strip & Filter chips
      expect(find.text('Total Quotes'), findsAtLeastNWidgets(1));
      expect(find.text('Drafts'), findsAtLeastNWidgets(1));
      expect(find.text('Sent'), findsAtLeastNWidgets(1));
      expect(find.text('Accepted'), findsAtLeastNWidgets(1));

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

    testWidgets('renders empty state when no quotations exist', (tester) async {
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

      expect(find.text('No Quotations Found'), findsOneWidget);
    });
  });
}

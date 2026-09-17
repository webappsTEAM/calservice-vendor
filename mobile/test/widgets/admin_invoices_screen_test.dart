import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_invoice.dart';
import 'package:mobile/features/admin/presentation/invoices/admin_invoices_providers.dart';
import 'package:mobile/features/admin/presentation/invoices/admin_invoices_screen.dart';

void main() {
  final sampleInvoices = [
    AdminInvoice(
      id: 201,
      invoiceNumber: 'INV-20260908-0001',
      status: 'PARTIALLY_PAID',
      statusDisplay: 'Partially Paid',
      billToName: 'Priya Rajan',
      serviceName: 'AC Compressor & Gas Charge',
      serviceCategory: 'AC Service',
      totalAmount: 3650.0,
      amountPaid: 500.0,
      balanceDue: 3150.0,
      advancePercent: 20.0,
      advanceAmount: 730.0,
      balanceAmount: 2920.0,
      issuedAt: DateTime(2026, 9, 8),
      items: const [
        AdminInvoiceItem(
          id: 1,
          name: 'AC Compressor 1.5 Ton',
          quantity: 1.0,
          unit: 'unit',
          unitPrice: 3000.0,
          totalAmount: 3000.0,
        ),
        AdminInvoiceItem(
          id: 2,
          name: 'R32 Gas Charging',
          quantity: 1.0,
          unit: 'can',
          unitPrice: 650.0,
          totalAmount: 650.0,
        ),
      ],
      payments: [
        AdminInvoicePayment(
          id: 1,
          amount: 500.0,
          method: 'UPI',
          reference: 'UPI-78945612',
          recordedAt: DateTime(2026, 9, 8),
        ),
      ],
    ),
    AdminInvoice(
      id: 202,
      invoiceNumber: 'INV-20260908-0002',
      status: 'PAID',
      statusDisplay: 'Paid',
      billToName: 'Karthik S',
      serviceName: 'Water Purifier Filter Replacement',
      serviceCategory: 'Water Purifier',
      totalAmount: 1850.0,
      amountPaid: 1850.0,
      balanceDue: 0.0,
      issuedAt: DateTime(2026, 9, 7),
    ),
  ];

  Widget buildTestWidget({
    List<AdminInvoice>? invoices,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null)
          adminInvoicesListProvider.overrideWith((ref) => Future.error(error))
        else ...[
          adminInvoicesListProvider.overrideWith(
            (ref) => Future.value(invoices ?? sampleInvoices),
          ),
          adminInvoiceDetailProvider(201).overrideWith(
            (ref) => Future.value(sampleInvoices.first),
          ),
        ],
      ],
      child: const MaterialApp(
        home: AdminInvoicesScreen(),
      ),
    );
  }

  group('AdminInvoicesScreen Widget Tests', () {
    testWidgets(
      'renders screen header, description, refresh, search, and status chips',
      (WidgetTester tester) async {
        await tester.pumpWidget(buildTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Invoices'), findsOneWidget);
        expect(
          find.text('Raised automatically when SEVO approves a quotation.'),
          findsOneWidget,
        );
        expect(find.text('Refresh'), findsOneWidget);
        expect(find.text('Invoice number, customer, phone'), findsOneWidget);

        // Status chips
        expect(find.widgetWithText(ChoiceChip, 'All Statuses'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Issued'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Partially Paid'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Paid'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Cancelled'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Refunded'), findsOneWidget);
        expect(find.widgetWithText(ChoiceChip, 'Draft'), findsOneWidget);

        // Cards
        expect(find.text('INV-20260908-0001'), findsOneWidget);
        expect(
          find.text('Priya Rajan · AC Compressor & Gas Charge'),
          findsOneWidget,
        );
        expect(find.text('₹3650.00'), findsOneWidget);
        expect(find.text('₹3150.00 outstanding'), findsOneWidget);
      },
    );

    testWidgets('tapping invoice card opens detail sheet', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(800, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('INV-20260908-0001'));
      await tester.pumpAndSettle();

      expect(find.text('LINE ITEMS'), findsOneWidget);
      expect(find.text('AC Compressor 1.5 Ton × 1.0 unit'), findsOneWidget);
      expect(find.text('PAYMENTS HISTORY'), findsOneWidget);
      expect(find.text('UPI'), findsOneWidget);
      expect(find.text('Ref: UPI-78945612'), findsOneWidget);
      expect(find.text('Record a payment'), findsOneWidget);
      expect(find.text('Record ₹3150.00'), findsOneWidget);
    });

    testWidgets('renders empty state when no invoices match', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget(invoices: []));
      await tester.pumpAndSettle();

      expect(find.text('No invoices yet.'), findsOneWidget);
      expect(
        find.text('No invoices match the selected filter criteria.'),
        findsOneWidget,
      );
    });

    testWidgets('renders error state on fetch failure', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        buildTestWidget(error: Exception('Failed to connect to backend')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load invoices'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Admin Invoices Responsive Layout Tests', () {
    for (final width in [320.0, 360.0, 390.0, 412.0]) {
      testWidgets('renders without overflow at ${width}px width', (
        WidgetTester tester,
      ) async {
        tester.view.physicalSize = Size(width, 800);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(buildTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Invoices'), findsOneWidget);
        expect(find.text('INV-20260908-0001'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

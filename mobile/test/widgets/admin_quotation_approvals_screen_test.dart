import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_quotation.dart';
import 'package:mobile/features/admin/presentation/quotations/admin_quotation_approvals_screen.dart';
import 'package:mobile/features/admin/presentation/quotations/admin_quotation_providers.dart';

void main() {
  final sampleQuotes = [
    const AdminQuotation(
      id: 101,
      quoteNumber: 'QT-20260908-0001',
      quoteVersion: 2,
      title: 'AC Compressor & Gas Charge',
      serviceName: 'AC Compressor & Gas Charge',
      serviceCategory: 'AC Service',
      customerName: 'Priya Rajan',
      jobId: 5259,
      totalAmount: 3650.0,
      taxAmount: 657.0,
      netPayable: 3650.0,
      status: 'CUSTOMER_ACCEPTED',
      statusDisplay: 'Accepted',
      requiresStructuralClearance: true,
      isStructurallyCleared: false,
    ),
    const AdminQuotation(
      id: 102,
      quoteNumber: 'QT-20260908-0002',
      quoteVersion: 1,
      title: 'Water Purifier Filter Replacement',
      serviceName: 'Water Purifier Filter Replacement',
      serviceCategory: 'Water Purifier',
      customerName: 'Karthik S',
      jobId: 5260,
      totalAmount: 1850.0,
      taxAmount: 333.0,
      netPayable: 1850.0,
      status: 'CUSTOMER_ACCEPTED',
      statusDisplay: 'Accepted',
    ),
  ];

  Widget buildTestWidget({
    List<AdminQuotation>? pendingApproval,
    List<AdminQuotation>? pendingReview,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null) ...[
          adminQuotesPendingApprovalProvider.overrideWith(
            (ref) => Future.error(error),
          ),
          adminQuotesPendingReviewProvider.overrideWith(
            (ref) => Future.error(error),
          ),
        ] else ...[
          adminQuotesPendingApprovalProvider.overrideWith(
            (ref) => Future.value(pendingApproval ?? sampleQuotes),
          ),
          adminQuotesPendingReviewProvider.overrideWith(
            (ref) => Future.value(pendingReview ?? []),
          ),
        ],
      ],
      child: const MaterialApp(
        home: AdminQuotationApprovalsScreen(),
      ),
    );
  }

  group('AdminQuotationApprovalsScreen Widget Tests', () {
    testWidgets('renders screen header, description, refresh, and tabs', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Quotation Approvals'), findsOneWidget);
      expect(
        find.text(
          'The customer has accepted. Approving creates the work booking and issues the invoice.',
        ),
        findsOneWidget,
      );
      expect(find.text('Refresh'), findsOneWidget);
      expect(find.text('Awaiting SEVO Approval'), findsOneWidget);
      expect(find.text('Held before sending'), findsOneWidget);

      // Verify cards render
      expect(find.text('QT-20260908-0001'), findsOneWidget);
      expect(find.text('v2'), findsOneWidget);
      expect(find.text('Structural clearance needed'), findsOneWidget);
      expect(
        find.text('AC Compressor & Gas Charge · Priya Rajan'),
        findsOneWidget,
      );
      expect(find.text('₹3650'), findsOneWidget);
      expect(find.text('incl. GST ₹657'), findsOneWidget);
      expect(find.text('Approve'), findsNWidgets(2));
      expect(find.text('Reject'), findsNWidgets(2));
    });

    testWidgets('switching tab updates description and shows empty state', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget(pendingReview: []));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Held before sending'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Above the category review threshold, or needing structural clearance. Releasing sends the quote to the customer.',
        ),
        findsOneWidget,
      );
      expect(find.text('Nothing waiting in this queue.'), findsOneWidget);
    });

    testWidgets('tapping approve opens confirmation dialog', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Approve').first);
      await tester.pumpAndSettle();

      expect(find.text('Approve QT-20260908-0001?'), findsOneWidget);
      expect(
        find.text(
          'Approving this quotation will create the work booking and issue the invoice.',
        ),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
    });

    testWidgets('tapping reject opens reason input dialog', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Reject').first);
      await tester.pumpAndSettle();

      expect(find.text('Reject QT-20260908-0001'), findsOneWidget);
      expect(
        find.text('Enter rejection reason (recorded in audit trail):'),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
    });

    testWidgets('renders error state on API failure', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        buildTestWidget(error: Exception('Network connection timed out')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load approval queue'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Quotation Approvals Responsive Layout Tests', () {
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

        expect(find.text('Quotation Approvals'), findsOneWidget);
        expect(find.text('QT-20260908-0001'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

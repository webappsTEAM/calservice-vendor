import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/admin_transactions_screen.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_detail_sheet.dart';

void main() {
  final sampleWallets = [
    AdminWallet(
      id: 1,
      employeeId: 101,
      employeeName: 'Ramesh Kumar',
      currency: 'INR',
      status: 'ACTIVE',
      availableBalance: 12500.0,
      pendingBalance: 3400.0,
      lifetimeEarnings: 45000.0,
      totalWithdrawn: 29100.0,
      outstandingRecovery: 0.0,
      nextSettlementDate: DateTime(2026, 9, 2),
    ),
    AdminWallet(
      id: 2,
      employeeId: 102,
      employeeName: 'Suresh Patel',
      currency: 'INR',
      status: 'LOCKED',
      availableBalance: 8200.0,
      pendingBalance: 1200.0,
      lifetimeEarnings: 28000.0,
      totalWithdrawn: 18600.0,
      outstandingRecovery: 500.0,
    ),
  ];

  final sampleTransactions = [
    WalletTransaction(
      id: 1001,
      referenceType: 'SERVICE_REQUEST',
      referenceId: 'REQ-2026-001',
      transactionType: 'SERVICE_EARNING',
      direction: 'CREDIT',
      status: 'COMPLETED',
      amount: 3650.0,
      grossAmount: 5000.0,
      earnRateSnapshot: 0.73,
      platformDeductionAmount: 1350.0,
      balanceBefore: 8850.0,
      balanceAfter: 12500.0,
      balanceType: 'AVAILABLE',
      description: 'Completed AC Master Service',
      createdAt: DateTime(2026, 8, 26, 14, 30),
    ),
    WalletTransaction(
      id: 1002,
      referenceType: 'COMMISSION_DEDUCTION',
      referenceId: 'COMM-2026-002',
      transactionType: 'PLATFORM_COMMISSION',
      direction: 'DEBIT',
      status: 'COMPLETED',
      amount: 1350.0,
      balanceBefore: 10200.0,
      balanceAfter: 8850.0,
      balanceType: 'AVAILABLE',
      description: 'Platform commission share deduction',
      createdAt: DateTime(2026, 8, 26, 14, 31),
    ),
    WalletTransaction(
      id: 1003,
      referenceType: 'SETTLEMENT',
      referenceId: 'SETTLE-2026-003',
      transactionType: 'SETTLEMENT_RELEASE',
      direction: 'CREDIT',
      status: 'PENDING_SETTLEMENT',
      amount: 3400.0,
      balanceBefore: 0.0,
      balanceAfter: 3400.0,
      balanceType: 'PENDING',
      description: 'T+7 Hold release pending verification',
      createdAt: DateTime(2026, 8, 25, 10, 0),
    ),
    WalletTransaction(
      id: 1004,
      referenceType: 'WITHDRAWAL',
      referenceId: 'WDL-2026-004',
      transactionType: 'WITHDRAWAL',
      direction: 'DEBIT',
      status: 'COMPLETED',
      amount: 1200.0,
      balanceBefore: 9400.0,
      balanceAfter: 8200.0,
      balanceType: 'AVAILABLE',
      description: 'Bank account payout withdrawal',
      createdAt: DateTime(2026, 8, 24, 16, 45),
    ),
    WalletTransaction(
      id: 1005,
      referenceType: 'REFUND',
      referenceId: 'REF-2026-005',
      transactionType: 'REFUND',
      direction: 'DEBIT',
      status: 'REVERSED',
      amount: 500.0,
      balanceBefore: 8200.0,
      balanceAfter: 7700.0,
      balanceType: 'AVAILABLE',
      description: 'Customer refund cancellation reversal',
      createdAt: DateTime(2026, 8, 23, 11, 20),
    ),
    WalletTransaction(
      id: 1006,
      referenceType: 'ADJUSTMENT',
      referenceId: 'ADJ-2026-006',
      transactionType: 'ADJUSTMENT_CREDIT',
      direction: 'CREDIT',
      status: 'COMPLETED',
      amount: 250.0,
      balanceBefore: 7700.0,
      balanceAfter: 7950.0,
      balanceType: 'AVAILABLE',
      description: 'Manual credit incentive adjustment',
      createdAt: DateTime(2026, 8, 22, 9, 15),
    ),
    WalletTransaction(
      id: 1007,
      referenceType: 'ADJUSTMENT',
      referenceId: 'ADJ-2026-007',
      transactionType: 'ADJUSTMENT_DEBIT',
      direction: 'DEBIT',
      status: 'FAILED',
      amount: 100.0,
      balanceBefore: 7950.0,
      balanceAfter: 7950.0,
      balanceType: 'AVAILABLE',
      description: 'Failed manual penalty debit',
      createdAt: DateTime(2026, 8, 21, 14, 0),
    ),
    WalletTransaction(
      id: 1008,
      referenceType: 'RECOVERY',
      referenceId: 'REC-2026-008',
      transactionType: 'RECOVERY_DEBIT',
      direction: 'DEBIT',
      status: 'COMPLETED',
      amount: 450.0,
      balanceBefore: 7950.0,
      balanceAfter: 7500.0,
      balanceType: 'AVAILABLE',
      description: 'Part defect warranty recovery debit',
      createdAt: DateTime(2026, 8, 20, 15, 30),
    ),
  ];

  final sampleTransactionsResponse = WalletTransactionListResponse(
    count: 8,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    results: sampleTransactions,
  );

  Widget buildTestWidget({
    List<AdminWallet>? wallets,
    WalletTransactionListResponse? transactionsResponse,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        adminWalletsProvider
            .overrideWith((ref) => Future.value(wallets ?? sampleWallets)),
        if (error != null)
          adminTechnicianTransactionsProvider((employeeId: 101, page: 1))
              .overrideWith((ref) => Future.error(error))
        else
          adminTechnicianTransactionsProvider((employeeId: 101, page: 1))
              .overrideWith(
            (ref) => Future.value(
              transactionsResponse ?? sampleTransactionsResponse,
            ),
          ),
      ],
      child: const MaterialApp(
        home: AdminTransactionsScreen(),
      ),
    );
  }

  group('AdminTransactionsScreen / Transaction Ledger Widget Tests', () {
    testWidgets(
        'renders header context badge, title, dynamic total count, immutable audit text and refresh button',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Navigation context badge
      expect(find.text('Workforce → Home → Wallets → Ledger'), findsOneWidget);

      // Title & Subtitle
      expect(find.text('Transaction Ledger'), findsOneWidget);
      expect(
        find.text('8 total records · immutable financial audit trail'),
        findsOneWidget,
      );

      // Refresh button
      expect(find.text('Refresh'), findsOneWidget);
    });

    testWidgets('renders technician selector and switches active technician',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Technician: '), findsOneWidget);
      expect(find.textContaining('Ramesh Kumar'), findsWidgets);
    });

    testWidgets(
        'renders filter controls and applies Type filter with Apply button',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('All Types'), findsOneWidget);
      expect(find.text('All Directions'), findsOneWidget);
      expect(find.text('All Statuses'), findsOneWidget);
      expect(find.text('Apply'), findsOneWidget);

      // Initially all 8 transactions are rendered
      expect(find.text('8 Filtered (8 Total)'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsOneWidget);
      expect(find.text('Platform commission share deduction'), findsOneWidget);
      expect(find.text('Bank account payout withdrawal'), findsOneWidget);

      // Select 'Withdrawal' type from dropdown
      final typeFinder = find.text('All Types');
      await tester.ensureVisible(typeFinder);
      await tester.tap(typeFinder);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Withdrawal').last);
      await tester.pumpAndSettle();

      // Tap Apply button
      final applyFinder = find.text('Apply');
      await tester.ensureVisible(applyFinder);
      await tester.tap(applyFinder);
      await tester.pumpAndSettle();

      expect(find.text('1 Filtered (8 Total)'), findsOneWidget);
      expect(find.text('Bank account payout withdrawal'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsNothing);
    });

    testWidgets('applies Direction filter (Credit/Debit) with Apply button',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Select 'Debit' from Direction dropdown
      final dirFinder = find.text('All Directions');
      await tester.ensureVisible(dirFinder);
      await tester.tap(dirFinder);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Debit').last);
      await tester.pumpAndSettle();

      // Tap Apply button
      final applyFinder = find.text('Apply');
      await tester.ensureVisible(applyFinder);
      await tester.tap(applyFinder);
      await tester.pumpAndSettle();

      // 5 debits in sampleTransactions
      expect(find.text('5 Filtered (8 Total)'), findsOneWidget);
      expect(find.text('Platform commission share deduction'), findsOneWidget);
      expect(find.text('Bank account payout withdrawal'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsNothing);
    });

    testWidgets('applies Status filter with Apply button', (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Select 'Pending Settlement' from Status dropdown
      final statusFinder = find.text('All Statuses');
      await tester.ensureVisible(statusFinder);
      await tester.tap(statusFinder);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Pending Settlement').last);
      await tester.pumpAndSettle();

      // Tap Apply button
      final applyFinder = find.text('Apply');
      await tester.ensureVisible(applyFinder);
      await tester.tap(applyFinder);
      await tester.pumpAndSettle();

      expect(find.text('1 Filtered (8 Total)'), findsOneWidget);
      expect(
          find.text('T+7 Hold release pending verification'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsNothing);
    });

    testWidgets('filters transactions by search query in real time',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Search by reference 'REQ-2026-001'
      await tester.enterText(
        find.byType(TextField),
        'REQ-2026-001',
      );
      await tester.pumpAndSettle();

      expect(find.text('1 Filtered (8 Total)'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsOneWidget);
      expect(find.text('Bank account payout withdrawal'), findsNothing);

      // Search non-existent query
      await tester.enterText(
        find.byType(TextField),
        'NonExistentTransaction',
      );
      await tester.pumpAndSettle();

      expect(find.text('No transactions found'), findsOneWidget);
      expect(
        find.text(
            'No financial transactions match the current filter criteria.'),
        findsOneWidget,
      );
    });

    testWidgets('renders transaction cards with badges, amounts, and metadata',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Card 1
      expect(find.text('Service Earning'), findsOneWidget);
      expect(find.text('+₹3650.00'), findsOneWidget);
      expect(find.text('Ref: REQ-2026-001'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsOneWidget);
      expect(find.text('CREDIT'), findsWidgets);
      expect(find.text('Completed'), findsWidgets);

      // Card 2
      expect(find.text('Platform Commission'), findsOneWidget);
      expect(find.text('−₹1350.00'), findsOneWidget);
      expect(find.text('DEBIT'), findsWidgets);
    });

    testWidgets(
        'tapping transaction card opens read-only TransactionDetailSheet modal',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Tap first transaction card
      await tester.tap(find.text('Service Earning').first);
      await tester.pumpAndSettle();

      // Verify TransactionDetailSheet is displayed
      expect(find.byType(TransactionDetailSheet), findsOneWidget);
      expect(find.text('Transaction Details'), findsOneWidget);
      expect(find.text('ID: TXN#1001'), findsOneWidget);
      expect(find.text('+ ₹3650.00'), findsOneWidget);
      expect(find.text('TRANSACTION BREAKDOWN'), findsOneWidget);
      expect(find.text('Reference ID'), findsOneWidget);
      expect(find.text('REQ-2026-001'), findsOneWidget);
      expect(find.text('Job Gross Value'), findsOneWidget);
      expect(find.text('₹5000.00'), findsOneWidget);
      expect(find.text('Technician Share'), findsOneWidget);
      expect(find.text('73.0%'), findsOneWidget);
      expect(find.text('Platform Deduction'), findsOneWidget);
      expect(find.text('₹1350.00'), findsOneWidget);
      expect(find.text('Balance Before'), findsOneWidget);
      expect(find.text('₹8850.00'), findsOneWidget);
      expect(find.text('Balance After'), findsOneWidget);
      expect(find.text('₹12500.00'), findsOneWidget);
      expect(find.text('TIMESTAMPS & TIMELINE'), findsOneWidget);
      expect(find.text('DESCRIPTION & NOTES'), findsOneWidget);
      expect(find.text('Completed AC Master Service'), findsWidgets);

      // Verify read-only: no edit or delete buttons
      expect(find.text('Edit'), findsNothing);
      expect(find.text('Delete'), findsNothing);
      expect(find.text('Modify'), findsNothing);

      // Close modal using close button icon in header
      await tester.tap(find.byIcon(Icons.close_rounded));
      await tester.pumpAndSettle();

      expect(find.byType(TransactionDetailSheet), findsNothing);
    });

    testWidgets('shows exact error text and retry button on failure',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        error: Exception('Network timeout from treasury server'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Failed to load transactions.'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('shows empty state when no transactions exist',
        (tester) async {
      final emptyResponse = const WalletTransactionListResponse(
        count: 0,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        results: [],
      );

      await tester.pumpWidget(buildTestWidget(
        transactionsResponse: emptyResponse,
      ));
      await tester.pumpAndSettle();

      expect(
        find.text('0 total records · immutable financial audit trail'),
        findsOneWidget,
      );
      expect(find.text('No transactions found'), findsOneWidget);
      expect(
        find.text(
            'No financial transactions match the current filter criteria.'),
        findsOneWidget,
      );
    });
  });

  group('AdminTransactionsScreen Responsive Layout Tests', () {
    for (final width in [320.0, 360.0, 390.0, 412.0]) {
      testWidgets('renders without overflow at ${width}px width',
          (tester) async {
        tester.view.physicalSize = Size(width, 900);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(buildTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Transaction Ledger'), findsOneWidget);
        expect(
            find.text('Workforce → Home → Wallets → Ledger'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

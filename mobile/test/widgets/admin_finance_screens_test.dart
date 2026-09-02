import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_bank_accounts_screen.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/admin_transactions_screen.dart';
import 'package:mobile/features/admin/presentation/finance/admin_wallets_screen.dart';
import 'package:mobile/features/admin/presentation/finance/admin_withdrawals_screen.dart';
import 'package:mobile/features/admin/presentation/finance/widgets/admin_add_bank_account_sheet.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';

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
      outstandingRecovery: 0.0,
    ),
  ];

  final sampleWithdrawals = [
    AdminWithdrawal(
      id: 701,
      amount: 6500.0,
      currency: 'INR',
      status: 'REQUESTED',
      employeeId: 101,
      employeeName: 'Ramesh Kumar',
      payoutAccountId: 11,
      payoutAccountDisplay: const PayoutAccountSummary(
        id: 11,
        bankName: 'HDFC Bank',
        accountNumberLast4: '4321',
        accountHolderName: 'Ramesh Kumar',
      ),
      requestedAt: DateTime(2026, 8, 25),
    ),
    AdminWithdrawal(
      id: 702,
      amount: 8000.0,
      currency: 'INR',
      status: 'PROCESSING',
      employeeId: 102,
      employeeName: 'Suresh Patel',
      payoutAccountId: 12,
      payoutAccountDisplay: const PayoutAccountSummary(
        id: 12,
        bankName: 'ICICI Bank',
        accountNumberLast4: '8765',
        accountHolderName: 'Suresh Patel',
      ),
      requestedAt: DateTime(2026, 8, 24),
    ),
  ];

  final sampleBankAccounts = [
    AdminBankAccount(
      id: 11,
      employeeId: 101,
      employeeName: 'Ramesh Kumar',
      bankName: 'HDFC Bank',
      accountHolderName: 'Ramesh Kumar',
      accountNumberLast4: '4321',
      ifscCode: 'HDFC0001234',
      accountType: 'SAVINGS',
      verificationStatus: 'PENDING_REVIEW',
      isPrimary: true,
      isActive: true,
    ),
  ];

  final sampleTransactionsResponse = WalletTransactionListResponse(
    count: 1,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    results: [
      WalletTransaction(
        id: 1,
        referenceType: 'SERVICE_REQUEST',
        referenceId: 'REQ-2026-001',
        transactionType: 'SERVICE_EARNING',
        direction: 'CREDIT',
        status: 'COMPLETED',
        amount: 1500.0,
        balanceBefore: 11000.0,
        balanceAfter: 12500.0,
        balanceType: 'AVAILABLE',
        description: 'Completed Plumbing Service',
        createdAt: DateTime(2026, 8, 26, 14, 30),
      ),
    ],
  );

  Widget createTestWidget(Widget child, {List<Override> overrides = const []}) {
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        home: child,
      ),
    );
  }

  testWidgets('AdminWalletsScreen renders metrics and technician cards', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminWalletsScreen(),
        overrides: [
          adminWalletsProvider.overrideWith((ref) async => sampleWallets),
          adminWithdrawalsProvider.overrideWith((ref) async => sampleWithdrawals),
        ],
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Technician Wallets & Financial Oversight'), findsOneWidget);
    expect(find.text('Technicians with Wallets'), findsOneWidget);
    expect(find.text('Total Available Balances'), findsOneWidget);
    expect(find.text('Ramesh Kumar'), findsOneWidget);
    expect(find.text('Suresh Patel'), findsOneWidget);
    expect(find.text('Active'), findsWidgets);
    expect(find.text('Locked'), findsWidgets);
  });

  testWidgets('AdminWithdrawalsScreen renders payout requests and action buttons', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminWithdrawalsScreen(),
        overrides: [
          adminWithdrawalsProvider.overrideWith((ref) async => sampleWithdrawals),
        ],
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Technician Payout Requests'), findsOneWidget);
    expect(find.text('REQ #701'), findsOneWidget);
    expect(find.text('REQ #702'), findsOneWidget);
    expect(find.text('Start Processing'), findsOneWidget);
    expect(find.text('Complete Payout (UTR)'), findsOneWidget);
  });

  testWidgets('AdminBankAccountsScreen renders masked account number, Add Account buttons, and verify button', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminBankAccountsScreen(),
        overrides: [
          adminBankAccountsProvider.overrideWith((ref) async => sampleBankAccounts),
        ],
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Bank Accounts'), findsOneWidget);
    expect(find.text('Payout accounts for withdrawal disbursement'), findsOneWidget);
    expect(find.text('+ Add Account'), findsOneWidget); // Single common button
    expect(find.text('HDFC Bank'), findsOneWidget);
    expect(find.text('•••• 4321'), findsOneWidget);
    expect(find.text('Verify Account'), findsOneWidget);
    expect(find.text('Reject'), findsOneWidget);
  });

  testWidgets('AdminBankAccountsScreen renders empty state with prominent Add Account button and security note', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminBankAccountsScreen(),
        overrides: [
          adminBankAccountsProvider.overrideWith((ref) async => []),
        ],
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('No bank accounts added'), findsOneWidget);
    expect(find.text('Add a bank account to enable withdrawal disbursement.'), findsOneWidget);
    expect(find.text('+ Add Account'), findsOneWidget); // Single common button
    expect(find.text('Security'), findsOneWidget);
    expect(find.byIcon(Icons.account_balance_outlined), findsOneWidget);
  });

  testWidgets('Tapping Add Account opens AdminAddBankAccountSheet and validates fields', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminBankAccountsScreen(),
        overrides: [
          adminBankAccountsProvider.overrideWith((ref) async => []),
        ],
      ),
    );

    await tester.pumpAndSettle();

    // Tap the single "+ Add Account" button
    await tester.tap(find.text('+ Add Account'));
    await tester.pumpAndSettle();

    // Verify modal sheet is open
    expect(find.byType(AdminAddBankAccountSheet), findsOneWidget);
    expect(find.text('Add Bank Account'), findsOneWidget);
    expect(find.text('Only the last 4 digits of your account number are stored. The full number is never retained.'), findsOneWidget);
    expect(find.text('Account Holder Name *'), findsOneWidget);
    expect(find.text('Bank Name'), findsOneWidget);
    expect(find.text('Account Number *'), findsOneWidget);
    expect(find.text('IFSC Code'), findsOneWidget);
    expect(find.text('Savings'), findsOneWidget);
    expect(find.text('Current'), findsOneWidget);

    // Scroll and tap "Add Account" inside sheet without filling fields
    final submitButtonFinder = find.widgetWithText(FilledButton, 'Add Account');
    await tester.ensureVisible(submitButtonFinder);
    await tester.tap(submitButtonFinder);
    await tester.pumpAndSettle();

    // Validation errors should appear
    expect(find.text('Account holder name is required.'), findsOneWidget);
    expect(find.text('Account number is required.'), findsOneWidget);

    // Scroll and tap Cancel
    final cancelButtonFinder = find.text('Cancel');
    await tester.ensureVisible(cancelButtonFinder);
    await tester.tap(cancelButtonFinder);
    await tester.pumpAndSettle();

    // Sheet should be dismissed
    expect(find.byType(AdminAddBankAccountSheet), findsNothing);
  });

  testWidgets('AdminTransactionsScreen renders transaction audit rows', (tester) async {
    await tester.pumpWidget(
      createTestWidget(
        const AdminTransactionsScreen(),
        overrides: [
          adminWalletsProvider.overrideWith((ref) async => sampleWallets),
          adminTechnicianTransactionsProvider((employeeId: 101, page: 1))
              .overrideWith((ref) async => sampleTransactionsResponse),
        ],
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Transaction Ledger'), findsOneWidget);
    expect(find.text('Technician: '), findsOneWidget);
    expect(find.text('Service Earning'), findsOneWidget);
    expect(find.text('+₹1500.00'), findsOneWidget);
  });
}

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/auth_events.dart';
import 'package:mobile/core/storage/token_storage.dart';
import 'package:mobile/features/auth/data/auth_api.dart';
import 'package:mobile/features/auth/data/auth_repository.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/finance/domain/employee_wallet.dart';
import 'package:mobile/features/finance/domain/payout_account.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';
import 'package:mobile/features/finance/presentation/bank_accounts_screen.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/transactions_screen.dart';
import 'package:mobile/features/finance/presentation/wallet_screen.dart';
import 'package:mobile/features/finance/presentation/widgets/add_bank_account_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/request_withdrawal_sheet.dart';
import 'package:mobile/features/finance/presentation/widgets/transaction_list_tile.dart';
import 'package:mobile/features/finance/presentation/withdrawals_screen.dart';

class _FakeTokenStorage extends TokenStorage {
  @override
  Future<String?> readAccessToken() async => null;
  @override
  Future<String?> readRefreshToken() async => null;
  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {}
  @override
  Future<void> clear() async {}
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(
          authApi: AuthApi(Dio()),
          tokenStorage: _FakeTokenStorage(),
        );

  @override
  Future<AuthUser?> restoreSession() async => null;
}

class _MockAuthController extends AuthController {
  _MockAuthController(AuthUser user)
      : super(_FakeAuthRepository(), AuthEvents()) {
    state = AuthState.authenticated(user);
  }
}

void main() {
  const sampleUser = AuthUser(
    id: 42,
    username: 'preethi_g',
    email: 'preethi@caldimservices.com',
    role: 'employee',
    registrationStatus: 'approved',
    firstName: 'Preethi',
    lastName: 'G',
    companyId: 1,
    companyName: 'CalServices',
    isSuperuser: false,
    employeeId: 'EMP-042',
  );

  final sampleWallet = EmployeeWallet(
    id: 1,
    employeeId: 42,
    employeeName: 'Preethi G',
    currency: 'INR',
    status: 'ACTIVE',
    availableBalance: 8500.0,
    pendingBalance: 3200.0,
    lifetimeEarnings: 45000.0,
    totalWithdrawn: 20000.0,
    outstandingRecovery: 0.0,
    nextSettlementDate: DateTime.parse('2026-08-30T10:00:00Z'),
    createdAt: DateTime.parse('2026-08-01T00:00:00Z'),
  );

  final sampleTransactions = WalletTransactionListResponse(
    count: 2,
    page: 1,
    pageSize: 25,
    totalPages: 1,
    results: [
      WalletTransaction(
        id: 101,
        referenceId: 'SR-2026-8801',
        transactionType: 'SERVICE_EARNING',
        direction: 'CREDIT',
        status: 'COMPLETED',
        amount: 2400.0,
        grossAmount: 4000.0,
        earnRateSnapshot: 0.60,
        platformDeductionAmount: 1600.0,
        balanceBefore: 6100.0,
        balanceAfter: 8500.0,
        balanceType: 'AVAILABLE',
        description: 'AC Servicing Earning',
        createdAt: DateTime.parse('2026-08-26T10:00:00Z'),
      ),
      WalletTransaction(
        id: 102,
        referenceId: 'WITHDRAW-501',
        transactionType: 'WITHDRAWAL',
        direction: 'DEBIT',
        status: 'COMPLETED',
        amount: 5000.0,
        balanceBefore: 11100.0,
        balanceAfter: 6100.0,
        balanceType: 'AVAILABLE',
        description: 'Payout Transfer to SBI',
        createdAt: DateTime.parse('2026-08-24T14:30:00Z'),
      ),
    ],
  );

  final sampleWithdrawals = [
    WalletWithdrawal(
      id: 501,
      amount: 5000.0,
      currency: 'INR',
      status: 'COMPLETED',
      bankTransactionId: 'UTR9876543210',
      payoutAccountId: 1,
      payoutAccountDisplay: const PayoutAccountSummary(
        id: 1,
        bankName: 'State Bank of India',
        accountNumberLast4: '1234',
        accountHolderName: 'Preethi G',
      ),
      requestedAt: DateTime.parse('2026-08-24T14:30:00Z'),
      completedAt: DateTime.parse('2026-08-25T10:00:00Z'),
    ),
    WalletWithdrawal(
      id: 502,
      amount: 6000.0,
      currency: 'INR',
      status: 'REQUESTED',
      payoutAccountId: 1,
      payoutAccountDisplay: const PayoutAccountSummary(
        id: 1,
        bankName: 'State Bank of India',
        accountNumberLast4: '1234',
        accountHolderName: 'Preethi G',
      ),
      requestedAt: DateTime.parse('2026-08-26T12:00:00Z'),
    ),
  ];

  final sampleAccounts = [
    PayoutAccount(
      id: 1,
      accountHolderName: 'Preethi G',
      bankName: 'State Bank of India',
      accountNumberLast4: '1234',
      ifscCode: 'SBIN0001234',
      accountType: 'SAVINGS',
      verificationStatus: 'VERIFIED',
      isPrimary: true,
      isActive: true,
      createdAt: DateTime.parse('2026-08-10T10:00:00Z'),
    ),
  ];

  group('Finance Module Widget Tests', () {
    testWidgets('WalletScreen renders hero balance, metrics, eligibility, and quick links', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => _MockAuthController(sampleUser)),
            employeeWalletProvider.overrideWith((ref) => Future.value(sampleWallet)),
            walletTransactionsProvider.overrideWith((ref) => Future.value(sampleTransactions)),
            payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
          ],
          child: const MaterialApp(
            home: WalletScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Screen title
      expect(find.text('Technician Earnings & Wallet'), findsOneWidget);

      // Top Actions
      expect(find.text('Refresh'), findsOneWidget);
      expect(find.text('Withdraw Funds'), findsOneWidget);

      // Summary Cards & Supporting Text
      expect(find.text('Available Balance'), findsOneWidget);
      expect(find.text('₹8500.00'), findsOneWidget);
      expect(find.text('Ready for withdrawal (min ₹5,000)'), findsOneWidget);

      expect(find.text('Pending Settlement'), findsOneWidget);
      expect(find.text('₹3200.00'), findsOneWidget);
      expect(find.text('T+7 settlement hold'), findsOneWidget);

      expect(find.text('Lifetime Commission'), findsOneWidget);
      expect(find.text('₹45000.00'), findsOneWidget);
      expect(find.text('Cumulative 60% earnings'), findsOneWidget);

      expect(find.text('Total Withdrawn'), findsOneWidget);
      expect(find.text('₹20000.00'), findsOneWidget);
      expect(find.text('Disbursed to bank accounts'), findsOneWidget);

      // Eligibility card
      expect(find.text('Eligible for Payout'), findsOneWidget);
      expect(find.text('Request Payout (₹8500.00)'), findsOneWidget);

      // Recent Ledger Entries
      expect(find.text('Recent Ledger Entries'), findsOneWidget);
      expect(find.text('Full Ledger →'), findsOneWidget);
      expect(find.text('Service Earning'), findsOneWidget);

      // Bank Accounts preview
      expect(find.text('Bank Accounts'), findsOneWidget);
      expect(find.text('State Bank of India'), findsOneWidget);
      expect(find.text('Preethi G • •••• 1234'), findsOneWidget);

      // Commission & Payout Policy card
      expect(find.text('Commission & Payout Policy'), findsOneWidget);
      expect(find.text('Technicians receive 60% of gross payment on completed jobs.'), findsOneWidget);
      expect(find.text('Company retains 40% covering platform & GST obligations.'), findsOneWidget);
      expect(find.text('Settlements move from Pending to Available in 7 days (T+7).'), findsOneWidget);
      expect(find.text('Minimum payout threshold: ₹5,000 INR.'), findsOneWidget);
    });

    testWidgets('TransactionsScreen renders list and opens detail sheet on tap', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            walletTransactionsProvider.overrideWith((ref) => Future.value(sampleTransactions)),
          ],
          child: const MaterialApp(
            home: TransactionsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Financial Ledger & Transactions'), findsWidgets);
      expect(find.text('Back to Wallet'), findsOneWidget);
      expect(find.text('Service Earning'), findsOneWidget);
      expect(find.text('Payout Withdrawal'), findsOneWidget);

      // Tap first transaction card
      await tester.tap(find.widgetWithText(TransactionListTile, 'Service Earning'));
      await tester.pumpAndSettle();

      // Verify transaction detail sheet opens
      expect(find.text('Transaction Details'), findsOneWidget);
      expect(find.text('ID: TXN#101'), findsOneWidget);
      expect(find.text('SR-2026-8801'), findsWidgets);
      expect(find.text('Job Gross Value'), findsOneWidget);
      expect(find.text('₹4000.00'), findsOneWidget);
      expect(find.text('Technician Share'), findsOneWidget);
      expect(find.text('60.0%'), findsOneWidget);
    });

    testWidgets('WithdrawalsScreen renders requests and displays cancellation action', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeWalletProvider.overrideWith((ref) => Future.value(sampleWallet)),
            walletWithdrawalsProvider.overrideWith((ref) => Future.value(sampleWithdrawals)),
            payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
          ],
          child: const MaterialApp(
            home: WithdrawalsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Payouts & Withdrawals'), findsWidgets);
      expect(find.text('Back to Wallet'), findsOneWidget);
      expect(find.text('Available for Payout'), findsOneWidget);
      expect(find.text('New Payout Request'), findsOneWidget);
      expect(find.text('₹5000.00'), findsOneWidget);
      expect(find.text('₹6000.00'), findsOneWidget);
      expect(find.text('UTR / Bank Ref: UTR9876543210'), findsOneWidget);
      expect(find.text('Cancel Request'), findsOneWidget);
    });

    testWidgets('BankAccountsScreen renders masked accounts and security banner', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
          ],
          child: const MaterialApp(
            home: BankAccountsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Payout Bank Accounts'), findsWidgets);
      expect(find.text('Back to Wallet'), findsOneWidget);
      expect(find.text('Secure Account Masking'), findsOneWidget);
      expect(find.text('Add Bank Account'), findsWidgets);
      expect(find.text('State Bank of India'), findsOneWidget);
      expect(find.text('•••• 1234'), findsOneWidget);
      expect(find.text('SBIN0001234'), findsOneWidget);
      expect(find.text('Verified'), findsOneWidget);
      expect(find.text('PRIMARY'), findsOneWidget);
    });

    testWidgets('AddBankAccountSheet renders all fields and validates inputs', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: AddBankAccountSheet(),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Link Bank Account'), findsOneWidget);
      expect(find.text('Account Holder Name *'), findsOneWidget);
      expect(find.text('Bank Name'), findsOneWidget);
      expect(find.text('Account Number *'), findsOneWidget);
      expect(find.text('Securely masked; only last 4 digits are retained for display.'), findsOneWidget);
      expect(find.text('IFSC Code'), findsOneWidget);
      expect(find.text('Savings'), findsOneWidget);
      expect(find.text('Current'), findsOneWidget);

      // Tap submit with empty fields
      await tester.tap(find.text('SAVE ACCOUNT'));
      await tester.pumpAndSettle();

      expect(find.text('Account holder name is required.'), findsOneWidget);
      expect(find.text('Account number is required.'), findsOneWidget);
    });

    testWidgets('RequestWithdrawalSheet enforces ₹5,000 threshold', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeWalletProvider.overrideWith((ref) => Future.value(sampleWallet)),
            payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: RequestWithdrawalSheet(),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Request Withdrawal'), findsOneWidget);
      expect(find.text('Available for Payout'), findsOneWidget);
      expect(find.text('Min ₹5K'), findsOneWidget);

      // Enter amount below threshold (e.g. ₹2000)
      final amountField = find.byType(TextFormField);
      await tester.enterText(amountField, '2000');
      await tester.pumpAndSettle();

      await tester.tap(find.text('REQUEST WITHDRAWAL'));
      await tester.pumpAndSettle();

      expect(find.text('Amount must be at least ₹5,000.00.'), findsOneWidget);
    });

    testWidgets('Finance screens render without RenderFlex overflow on narrow 320px width', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(320 * 2, 640 * 2);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final commonOverrides = [
        authControllerProvider.overrideWith((ref) => _MockAuthController(sampleUser)),
        employeeWalletProvider.overrideWith((ref) => Future.value(sampleWallet)),
        walletTransactionsProvider.overrideWith((ref) => Future.value(sampleTransactions)),
        walletWithdrawalsProvider.overrideWith((ref) => Future.value(sampleWithdrawals)),
        payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
      ];

      // 1. WalletScreen on 320px
      await tester.pumpWidget(
        ProviderScope(
          overrides: commonOverrides,
          child: const MaterialApp(
            home: WalletScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);

      // 2. TransactionsScreen on 320px
      await tester.pumpWidget(
        ProviderScope(
          overrides: commonOverrides,
          child: const MaterialApp(
            home: TransactionsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);

      // 3. WithdrawalsScreen on 320px
      await tester.pumpWidget(
        ProviderScope(
          overrides: commonOverrides,
          child: const MaterialApp(
            home: WithdrawalsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);

      // 4. BankAccountsScreen on 320px
      await tester.pumpWidget(
        ProviderScope(
          overrides: commonOverrides,
          child: const MaterialApp(
            home: BankAccountsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    testWidgets('Empty states display exact required titles and messages', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final emptyWallet = EmployeeWallet(
        id: 1,
        employeeId: 42,
        employeeName: 'Preethi G',
        currency: 'INR',
        status: 'ACTIVE',
        availableBalance: 0.0,
        pendingBalance: 0.0,
        lifetimeEarnings: 0.0,
        totalWithdrawn: 0.0,
        outstandingRecovery: 0.0,
        createdAt: DateTime.parse('2026-08-26T12:00:00Z'),
      );

      final emptyTransactions = const WalletTransactionListResponse(
        count: 0,
        page: 1,
        pageSize: 20,
        totalPages: 0,
        results: [],
      );

      // 1. Empty WalletScreen
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [
            authControllerProvider.overrideWith((ref) => _MockAuthController(sampleUser)),
            employeeWalletProvider.overrideWith((ref) => Future.value(emptyWallet)),
            walletTransactionsProvider.overrideWith((ref) => Future.value(emptyTransactions)),
            walletWithdrawalsProvider.overrideWith((ref) => Future.value([])),
            payoutAccountsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: WalletScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('No transactions recorded yet. Complete customer jobs to earn commission.'),
        findsOneWidget,
      );
      expect(find.text('No bank accounts linked'), findsOneWidget);
      expect(find.text('Add Bank Account'), findsWidgets);

      // 2. Empty WithdrawalsScreen
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [
            employeeWalletProvider.overrideWith((ref) => Future.value(emptyWallet)),
            walletWithdrawalsProvider.overrideWith((ref) => Future.value([])),
            payoutAccountsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: WithdrawalsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No withdrawal requests recorded'), findsOneWidget);
      expect(
        find.text('When your balance reaches ₹5,000, you can request payouts directly here.'),
        findsOneWidget,
      );

      // 3. Empty BankAccountsScreen
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [
            payoutAccountsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: BankAccountsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No Bank Accounts Linked'), findsOneWidget);
      expect(
        find.text('Add a verified bank account to enable self-service payouts.'),
        findsOneWidget,
      );
      expect(find.text('Add Bank Account'), findsWidgets);

      // 4. TransactionsScreen with filter empty state
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [
            transactionFilterProvider.overrideWith(
              (ref) => const TransactionFilterState(type: 'SERVICE_EARNING'),
            ),
            walletTransactionsProvider.overrideWith((ref) => Future.value(emptyTransactions)),
          ],
          child: const MaterialApp(
            home: TransactionsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No ledger records found matching your filters.'), findsOneWidget);
    });

    testWidgets('TransactionsScreen filter modal opens and allows selecting type and status', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            walletTransactionsProvider.overrideWith((ref) => Future.value(sampleTransactions)),
          ],
          child: const MaterialApp(
            home: TransactionsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap filter icon in top bar
      await tester.tap(find.byIcon(Icons.tune_rounded));
      await tester.pumpAndSettle();

      // Verify filter modal content
      expect(find.text('Filter Transactions'), findsOneWidget);
      expect(find.text('All Transaction Types'), findsOneWidget);
      expect(find.text('Service Earnings (60%)'), findsOneWidget);
      expect(find.text('Settlement Release (T+7)'), findsOneWidget);
      expect(find.text('Withdrawals'), findsOneWidget);
      expect(find.text('Withdrawal Reversals'), findsOneWidget);
      expect(find.text('Admin Credits'), findsOneWidget);
      expect(find.text('Admin Debits'), findsOneWidget);
      expect(find.text('All Statuses'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('Pending Settlement'), findsOneWidget);
      expect(find.text('Reversed'), findsOneWidget);

      // Select 'Settlement Release (T+7)'
      await tester.tap(find.text('Settlement Release (T+7)'));
      await tester.pumpAndSettle();

      // Tap Apply Filters
      await tester.tap(find.text('Apply Filters'));
      await tester.pumpAndSettle();

      // Bottom sheet is closed
      expect(find.text('Filter Transactions'), findsNothing);
    });
  });
}

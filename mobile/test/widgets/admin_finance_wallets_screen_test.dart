import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_wallet.dart';
import 'package:mobile/features/admin/presentation/finance/admin_finance_providers.dart';
import 'package:mobile/features/admin/presentation/finance/admin_wallets_screen.dart';
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
      outstandingRecovery: 500.0,
    ),
    AdminWallet(
      id: 3,
      employeeId: 103,
      employeeName: 'Anil Sharma',
      currency: 'INR',
      status: 'SUSPENDED',
      availableBalance: 0.0,
      pendingBalance: 0.0,
      lifetimeEarnings: 15000.0,
      totalWithdrawn: 15000.0,
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

  Widget buildTestWidget({
    List<AdminWallet>? wallets,
    List<AdminWithdrawal>? withdrawals,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null)
          adminWalletsProvider.overrideWith((ref) => Future.error(error))
        else
          adminWalletsProvider
              .overrideWith((ref) => Future.value(wallets ?? sampleWallets)),
        adminWithdrawalsProvider.overrideWith(
            (ref) => Future.value(withdrawals ?? sampleWithdrawals)),
      ],
      child: const MaterialApp(
        home: AdminWalletsScreen(),
      ),
    );
  }

  group('AdminWalletsScreen / Platform Treasury Widget Tests', () {
    testWidgets(
        'renders header context badge, title, subtitle, refresh, and dynamic Manage Payouts count',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Context Badge
      expect(find.text('Wallets & Finance'), findsOneWidget);

      // Main Title & Subtitle
      expect(find.text('Technician Wallets & Financial Oversight'),
          findsOneWidget);
      expect(
        find.text(
            'Monitor technician earnings (60% commission share), pending T+7 settlements, and payout disbursements.'),
        findsOneWidget,
      );

      // Actions
      expect(find.text('Refresh'), findsOneWidget);
      expect(find.text('Manage Payouts (2)'), findsOneWidget);
    });

    testWidgets('renders all 4 financial metric cards with correct live values',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Card 1: Technicians
      expect(find.text('Technicians'), findsOneWidget);
      expect(find.text('Total active technician wallets'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);

      // Card 2: Total Available
      expect(find.text('Total Available'), findsOneWidget);
      expect(find.text('Withdrawable technician balances'), findsOneWidget);
      expect(find.text('₹20700.00'), findsOneWidget);

      // Card 3: In T+7 Hold
      expect(find.text('In T+7 Hold'), findsOneWidget);
      expect(find.text('Pending settlement release'), findsOneWidget);
      expect(find.text('₹4600.00'), findsOneWidget);

      // Card 4: Total Disbursed
      expect(find.text('Total Disbursed'), findsOneWidget);
      expect(find.text('Lifetime payouts to technicians'), findsOneWidget);
      expect(find.text('₹62700.00'), findsOneWidget);
    });

    testWidgets(
        'renders main section title with dynamic count and transactions link',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (3)'), findsOneWidget);
      expect(find.text('View All Transactions →'), findsOneWidget);
    });

    testWidgets('renders status filter chips and filters wallet list on select',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Verify all 4 chips exist
      expect(find.text('All Statuses'), findsOneWidget);
      expect(find.text('Active'), findsWidgets);
      expect(find.text('Locked'), findsWidgets);
      expect(find.text('Suspended'), findsWidgets);

      // Initial state: all 3 technicians displayed
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Patel'), findsOneWidget);
      expect(find.text('Anil Sharma'), findsOneWidget);

      // Select 'Active' filter chip
      await tester.tap(find.widgetWithText(ChoiceChip, 'Active'));
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (1)'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Patel'), findsNothing);
      expect(find.text('Anil Sharma'), findsNothing);

      // Select 'Locked' filter chip
      await tester.tap(find.widgetWithText(ChoiceChip, 'Locked'));
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (1)'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsNothing);
      expect(find.text('Suresh Patel'), findsOneWidget);
      expect(find.text('Anil Sharma'), findsNothing);

      // Select 'All Statuses' filter chip
      await tester.tap(find.widgetWithText(ChoiceChip, 'All Statuses'));
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (3)'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Patel'), findsOneWidget);
      expect(find.text('Anil Sharma'), findsOneWidget);
    });

    testWidgets('filters wallet list by search query (name & technician ID)',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Search by name 'Suresh'
      await tester.enterText(
        find.byType(TextField),
        'Suresh',
      );
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (1)'), findsOneWidget);
      expect(find.text('Suresh Patel'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsNothing);

      // Search by ID '101'
      await tester.enterText(
        find.byType(TextField),
        '101',
      );
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (1)'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Patel'), findsNothing);

      // Search non-existent query
      await tester.enterText(
        find.byType(TextField),
        'NonExistentTechnician',
      );
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (0)'), findsOneWidget);
      expect(
        find.text('No technician wallets matched current search criteria.'),
        findsOneWidget,
      );
      expect(
        find.text('Try clearing search or changing status filter.'),
        findsOneWidget,
      );
    });

    testWidgets(
        'renders wallet cards with correct details, balances, and action buttons',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Ramesh Kumar card
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('EMP-101  •  INR'), findsOneWidget);
      expect(find.text('₹12500.00'), findsWidgets);
      expect(find.text('₹3400.00'), findsWidgets);
      expect(find.text('₹45000.00'), findsOneWidget);
      expect(find.text('₹29100.00'), findsOneWidget);

      // Action buttons
      expect(find.text('View Details'), findsWidgets);
      expect(find.text('Lock'), findsWidgets); // for active wallet
      expect(find.text('Unlock'), findsWidgets); // for locked wallet
      expect(find.text('Ledger'), findsWidgets);
    });

    testWidgets(
        'tapping View Details opens wallet detail modal bottom sheet with financial breakdown',
        (tester) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Scroll until 'View Details' button is visible and tap
      final viewDetailsFinder = find.text('View Details').first;
      await tester.scrollUntilVisible(
        viewDetailsFinder,
        100,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      await tester.tap(viewDetailsFinder);
      await tester.pumpAndSettle();

      // Detail sheet contents
      expect(find.text('Technician ID: #101 · INR'), findsOneWidget);
      expect(find.text('Financial Summary'), findsOneWidget);
      expect(find.text('Available Balance'), findsWidgets);
      expect(find.text('T+7 Pending Hold'), findsOneWidget);
      expect(find.text('Total Earned (Lifetime)'), findsOneWidget);
      expect(find.text('Total Withdrawn'), findsWidgets);
      expect(find.text('Next Settlement Date'), findsOneWidget);
      expect(find.text('02/09/2026'), findsOneWidget);

      // Quick Actions
      expect(find.text('Quick Actions'), findsOneWidget);
      expect(find.text('Transactions'), findsOneWidget);
      expect(find.text('Withdrawals'), findsOneWidget);
      expect(find.text('Adjust Balance'), findsOneWidget);
      expect(find.text('Lock Wallet'), findsOneWidget);
    });

    testWidgets(
        'shows exact empty state when wallet list is empty from backend',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(wallets: []));
      await tester.pumpAndSettle();

      expect(find.text('Active Technician Wallets (0)'), findsOneWidget);
      expect(
        find.text('No technician wallets matched current search criteria.'),
        findsOneWidget,
      );
      expect(
        find.text('Try clearing search or changing status filter.'),
        findsOneWidget,
      );
    });

    testWidgets('shows error state with retry button on failure',
        (tester) async {
      await tester.pumpWidget(buildTestWidget(
        error: Exception('Failed to connect to Treasury API'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Failed to load technician wallet data'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  group('AdminWalletsScreen Responsive Layout Tests', () {
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

        expect(find.text('Technician Wallets & Financial Oversight'),
            findsOneWidget);
        expect(find.text('Wallets & Finance'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

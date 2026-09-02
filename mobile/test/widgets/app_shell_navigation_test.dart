import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/finance/domain/employee_wallet.dart';
import 'package:mobile/features/finance/domain/payout_account.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/finance/presentation/wallet_screen.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/notifications/domain/app_notification.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';
import 'package:mobile/features/notifications/presentation/notifications_screen.dart';
import 'package:mobile/features/onboarding/data/onboarding_storage.dart';
import 'package:mobile/features/profile/domain/shift_status.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/routing/app_router.dart';

class _FakeOnboardingStorage extends OnboardingStorage {
  @override
  Future<bool> hasCompletedOnboarding() async => true;
  @override
  Future<void> setOnboardingCompleted() async {}
  @override
  Future<void> clear() async {}
}

class _FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  _FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeNotificationsNotifier extends NotificationsNotifier {
  @override
  Future<NotificationsResult> build() async {
    return const NotificationsResult(
      unreadCount: 3,
      items: [
        AppNotification(
          id: 1,
          title: 'System Update',
          message: 'Maintenance scheduled',
          isRead: false,
        ),
      ],
    );
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
    count: 0,
    page: 1,
    pageSize: 25,
    totalPages: 1,
    results: [],
  );

  final sampleWithdrawals = <WalletWithdrawal>[];
  final sampleAccounts = <PayoutAccount>[];

  final mockProfile = EmployeeProfile(
    employeeId: 'EMP-042',
    firstName: 'Preethi',
    lastName: 'G',
    email: 'preethi@caldimservices.com',
    mobileNumber: '+91 98765 43210',
    title: 'Senior Technician',
    companyName: 'CalServices',
    registrationStatus: 'approved',
    isOnline: true,
    approvedServices: const [],
    allRequestedServices: const [],
    documents: const [],
    controlledFields: const ControlledFieldsConfig(
      isLocked: false,
      lockedFields: [],
    ),
  );

  List<Override> buildOverrides() {
    return [
      onboardingStorageProvider.overrideWithValue(_FakeOnboardingStorage()),
      authControllerProvider.overrideWith((ref) => _FakeAuthController(sampleUser)),
      employeeProfileProvider.overrideWith((ref) => Future.value(mockProfile)),
      shiftStatusProvider.overrideWith((ref) => Future.value(const ShiftStatus(
            isClockedIn: true,
            shiftStatus: 'clocked_in',
            hasActiveJob: false,
          ))),
      activeJobsProvider.overrideWith((ref) => Future.value(<Job>[])),
      completedJobsProvider.overrideWith((ref) => Future.value(<Job>[])),
      employeeWalletProvider.overrideWith((ref) => Future.value(sampleWallet)),
      walletTransactionsProvider.overrideWith((ref) => Future.value(sampleTransactions)),
      walletWithdrawalsProvider.overrideWith((ref) => Future.value(sampleWithdrawals)),
      payoutAccountsProvider.overrideWith((ref) => Future.value(sampleAccounts)),
      notificationsProvider.overrideWith(() => _FakeNotificationsNotifier()),
    ];
  }

  group('AppShellScaffold Navigation & Tabs', () {
    testWidgets('renders exactly 4 navigation destinations: Home, Jobs, Wallet, More', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: Consumer(
            builder: (context, ref, _) {
              final router = ref.watch(appRouterProvider);
              return MaterialApp.router(
                routerConfig: router,
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Navigation destinations exist
      expect(find.byType(NavigationBar), findsOneWidget);
      expect(find.byType(NavigationDestination), findsNWidgets(4));

      // Required destinations are present
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Jobs'), findsOneWidget);
      expect(find.text('Wallet'), findsOneWidget);
      expect(find.text('More'), findsOneWidget);

      // Verify Wallet destination icon
      expect(find.byIcon(Icons.account_balance_wallet_outlined), findsOneWidget);

      // Verify Notifications is REMOVED from bottom navigation bar
      final navBarFinder = find.byType(NavigationBar);
      expect(
        find.descendant(of: navBarFinder, matching: find.text('Notifications')),
        findsNothing,
      );
      expect(
        find.descendant(of: navBarFinder, matching: find.byIcon(Icons.notifications_outlined)),
        findsNothing,
      );

      // Header notification bell is still present with unread badge count
      expect(find.byTooltip('Notifications'), findsOneWidget);
    });

    testWidgets('tapping Wallet tab navigates to WalletScreen', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: Consumer(
            builder: (context, ref, _) {
              final router = ref.watch(appRouterProvider);
              return MaterialApp.router(
                routerConfig: router,
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Initially on Home tab
      expect(find.byType(WalletScreen), findsNothing);

      // Tap Wallet destination
      await tester.tap(find.text('Wallet'));
      await tester.pumpAndSettle();

      // Verify WalletScreen is displayed
      expect(find.byType(WalletScreen), findsOneWidget);
      expect(find.text('Technician Earnings & Wallet'), findsOneWidget);
    });

    testWidgets('tapping header bell navigates to NotificationsScreen and back returns to previous screen', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: Consumer(
            builder: (context, ref, _) {
              final router = ref.watch(appRouterProvider);
              return MaterialApp.router(
                routerConfig: router,
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap header notification bell
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();

      // Verify NotificationsScreen is displayed
      expect(find.byType(NotificationsScreen), findsOneWidget);
      expect(find.text('Notifications'), findsWidgets);

      // Press Android Back / pop
      final popped = await tester.binding.handlePopRoute();
      expect(popped, isTrue);
      await tester.pumpAndSettle();

      // Verify returned to previous screen
      expect(find.byType(NotificationsScreen), findsNothing);
      expect(find.byTooltip('Notifications'), findsOneWidget);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/domain/admin_dashboard_metrics.dart';
import 'package:mobile/features/admin/domain/fleet_member.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/admin_home_screen.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/dashboard/presentation/home_screen.dart';
import 'package:mobile/features/finance/domain/employee_wallet.dart';
import 'package:mobile/features/finance/domain/payout_account.dart';
import 'package:mobile/features/finance/domain/wallet_transaction.dart';
import 'package:mobile/features/finance/domain/wallet_withdrawal.dart';
import 'package:mobile/features/finance/presentation/finance_providers.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/jobs/presentation/jobs_screen.dart';
import 'package:mobile/features/notifications/domain/app_notification.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';
import 'package:mobile/features/notifications/presentation/notifications_screen.dart';
import 'package:mobile/features/onboarding/data/onboarding_storage.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/domain/shift_status.dart';
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
      unreadCount: 2,
      items: [
        AppNotification(
          id: 101,
          title: 'New Dispatch Offer',
          message: 'AC Repair booking available',
          isRead: false,
        ),
      ],
    );
  }
}

void main() {
  const sampleEmployee = AuthUser(
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

  const sampleAdmin = AuthUser(
    id: 100,
    username: 'ops_admin',
    email: 'admin@calservices.com',
    firstName: 'Operations',
    lastName: 'Director',
    role: 'admin',
    companyId: 1,
    companyName: 'CalServices Enterprise Solutions Group Ltd',
    isSuperuser: true,
    employeeId: null,
    registrationStatus: 'approved',
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

  final mockAdminDashboard = AdminDashboardData(
    applications: const <AdminApplication>[],
    jobs: const <Job>[],
    fleet: const <FleetMember>[],
  );

  List<Override> buildEmployeeOverrides() {
    return [
      onboardingStorageProvider.overrideWithValue(_FakeOnboardingStorage()),
      authControllerProvider.overrideWith((ref) => _FakeAuthController(sampleEmployee)),
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
      walletWithdrawalsProvider.overrideWith((ref) => Future.value(<WalletWithdrawal>[])),
      payoutAccountsProvider.overrideWith((ref) => Future.value(<PayoutAccount>[])),
      notificationsProvider.overrideWith(() => _FakeNotificationsNotifier()),
    ];
  }

  List<Override> buildAdminOverrides() {
    return [
      onboardingStorageProvider.overrideWithValue(_FakeOnboardingStorage()),
      authControllerProvider.overrideWith((ref) => _FakeAuthController(sampleAdmin)),
      employeeProfileProvider.overrideWith((ref) => Future.value(mockProfile)),
      adminDashboardDataProvider.overrideWith((ref) => mockAdminDashboard),
      notificationsProvider.overrideWith(() => _FakeNotificationsNotifier()),
    ];
  }

  group('Notification Navigation & Android Back Stack Tests', () {
    testWidgets('EMPLOYEE: Home -> Notification -> Android Back -> Home (single and repeated)',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildEmployeeOverrides(),
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

      // 1. Initial State: Employee Home Screen is shown
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);

      // 2. Tap Notification Bell in Header
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();

      // 3. NotificationsScreen is displayed
      expect(find.byType(NotificationsScreen), findsOneWidget);
      expect(find.text('Notifications'), findsWidgets);

      // 4. User presses Android system Back button
      final didPop1 = await tester.binding.handlePopRoute();
      expect(didPop1, isTrue);
      await tester.pumpAndSettle();

      // 5. App returns to Employee Home Screen (did not exit, no blank screen)
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);

      // 6. Repeat flow: Tap Notification bell again
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();
      expect(find.byType(NotificationsScreen), findsOneWidget);

      // 7. Press Android Back button again
      final didPop2 = await tester.binding.handlePopRoute();
      expect(didPop2, isTrue);
      await tester.pumpAndSettle();

      // 8. App returns to Employee Home Screen again
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);
    });

    testWidgets('EMPLOYEE: Jobs Screen -> Notification -> Android Back -> Jobs Screen',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildEmployeeOverrides(),
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

      // Switch to Jobs tab
      await tester.tap(find.text('Jobs'));
      await tester.pumpAndSettle();
      expect(find.byType(JobsScreen), findsOneWidget);

      // Tap Notification Bell
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();
      expect(find.byType(NotificationsScreen), findsOneWidget);

      // Press Android Back
      final didPop = await tester.binding.handlePopRoute();
      expect(didPop, isTrue);
      await tester.pumpAndSettle();

      // Returns to Jobs Screen
      expect(find.byType(JobsScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);
    });

    testWidgets('ADMIN: Admin Dashboard -> Notification -> Android Back -> Admin Dashboard (single and repeated)',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildAdminOverrides(),
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

      // 1. Initial State: Admin Dashboard / Home is shown
      expect(find.byType(AdminHomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);

      // 2. Tap Notification Bell in Admin Header
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();

      // 3. NotificationsScreen is displayed
      expect(find.byType(NotificationsScreen), findsOneWidget);
      expect(find.text('Notifications'), findsWidgets);

      // 4. User presses Android system Back button
      final didPop1 = await tester.binding.handlePopRoute();
      expect(didPop1, isTrue);
      await tester.pumpAndSettle();

      // 5. App returns to Admin Home Screen
      expect(find.byType(AdminHomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);

      // 6. Repeat flow: Tap Notification bell again
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();
      expect(find.byType(NotificationsScreen), findsOneWidget);

      // 7. Press Android Back button again
      final didPop2 = await tester.binding.handlePopRoute();
      expect(didPop2, isTrue);
      await tester.pumpAndSettle();

      // 8. App returns to Admin Home Screen again
      expect(find.byType(AdminHomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);
    });

    testWidgets('AppBar Back button also pops Notifications back to previous screen',
        (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildEmployeeOverrides(),
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

      // Tap Notification Bell
      await tester.tap(find.byTooltip('Notifications'));
      await tester.pumpAndSettle();
      expect(find.byType(NotificationsScreen), findsOneWidget);

      // Tap the AppBar back button
      final backButton = find.byType(BackButton);
      expect(backButton, findsOneWidget);
      await tester.tap(backButton);
      await tester.pumpAndSettle();

      // Returns to Employee Home Screen
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(NotificationsScreen), findsNothing);
    });
  });
}

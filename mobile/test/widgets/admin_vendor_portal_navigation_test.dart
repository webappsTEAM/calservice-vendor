import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/domain/admin_dashboard_metrics.dart';
import 'package:mobile/features/admin/domain/fleet_member.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/admin_home_screen.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/routing/app_routes.dart';

class FakeAuthController extends StateNotifier<AuthState>
    implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const mockVendorAdminUser = AuthUser(
    id: 50,
    username: 'vendor_admin',
    email: 'admin@coolcare.com',
    firstName: 'Vendor',
    lastName: 'Administrator',
    role: 'admin',
    companyId: 10,
    companyName: 'CoolCare Services Ltd',
    isSuperuser: false,
    isPlatformAdmin: false,
    isVendorAdmin: true,
    employeeId: null,
    registrationStatus: 'approved',
  );

  const mockSuperAdminUser = AuthUser(
    id: 1,
    username: 'superadmin',
    email: 'superadmin@calservices.com',
    firstName: 'Platform',
    lastName: 'Superadmin',
    role: 'superadmin',
    companyId: 1,
    companyName: 'SEVO Platform Operations',
    isSuperuser: true,
    isPlatformAdmin: true,
    userType: 'platform_admin',
    employeeId: null,
    registrationStatus: 'approved',
  );

  final mockApplications = [
    const AdminApplication(
      id: 1,
      name: 'Ravi Kumar',
      employeeId: 'EMP-201',
      registrationStatus: 'submitted',
      documentsStatus: {
        'aadhaar': {'status': 'pending'},
      },
    ),
    const AdminApplication(
      id: 2,
      name: 'Anand Singh',
      employeeId: 'EMP-202',
      registrationStatus: 'under_review',
    ),
    const AdminApplication(
      id: 3,
      name: 'Sunil Rao',
      employeeId: 'EMP-203',
      registrationStatus: 'approved',
    ),
    const AdminApplication(
      id: 4,
      name: 'Vikas Sharma',
      employeeId: 'EMP-204',
      registrationStatus: 'approved',
    ),
    const AdminApplication(
      id: 5,
      name: 'Manoj Tiwari',
      employeeId: 'EMP-205',
      registrationStatus: 'correction_required',
    ),
  ];

  final mockJobs = [
    const Job(
      id: 801,
      requestId: 'SR-801',
      customerName: 'Aarav Patel',
      serviceCategory: 'HVAC',
      serviceTitle: 'Split AC Deep Cleaning & Gas Refill',
      status: 'new_request',
      address: '100 Feet Rd, Indiranagar, Bengaluru',
      preferredDate: '2026-09-10',
      preferredTime: '10:00 AM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: false,
    ),
    const Job(
      id: 802,
      requestId: 'SR-802',
      customerName: 'Pooja Hegde',
      serviceCategory: 'Appliance',
      serviceTitle: 'Washing Machine Drum Inspection',
      status: 'accepted',
      address: 'Koramangala 4th Block, Bengaluru',
      preferredDate: '2026-09-10',
      preferredTime: '02:00 PM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: false,
    ),
  ];

  final mockFleet = [
    const FleetMember(
      id: 201,
      employeeId: 'EMP-201',
      name: 'Sunil Rao',
      phone: '+91 9876500001',
      isOnline: true,
      currentAvailability: 'available',
      registrationStatus: 'approved',
      hasLocation: true,
      latitude: 12.9716,
      longitude: 77.5946,
      activeJob: null,
    ),
    const FleetMember(
      id: 202,
      employeeId: 'EMP-202',
      name: 'Vikas Sharma',
      phone: '+91 9876500002',
      isOnline: true,
      currentAvailability: 'busy',
      registrationStatus: 'approved',
      hasLocation: true,
      latitude: 12.9718,
      longitude: 77.5950,
      activeJob: 'SR-802',
    ),
  ];

  final testDashboardData = AdminDashboardData(
    applications: mockApplications,
    jobs: mockJobs,
    fleet: mockFleet,
  );

  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  group('Admin / Service Provider Navigation Drawer Tests', () {
    testWidgets('1. Displays Company header, portal badge, and all required sections', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.adminHome,
        routes: [
          GoRoute(
            path: AppRoutes.adminHome,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Company Home Content'),
            ),
          ),
          GoRoute(path: AppRoutes.adminTiedTechnicians, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminVendorInvitations, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminEmployees, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminApplications, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminJobs, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminDispatch, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminProviderProfile, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminFinanceWallets, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminFinanceTransactions, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminFinanceWithdrawals, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminFinanceBankAccounts, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminMonitoringDatabaseEgress, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminReports, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminSettings, builder: (c, s) => const Scaffold()),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open drawer
      final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      // 1. Company Header
      expect(find.text('CoolCare Services Ltd'), findsOneWidget);
      expect(find.text('Company Portal'), findsOneWidget);
      expect(find.text('Vendor Administrator'), findsOneWidget);
      expect(find.text('ADMIN'), findsOneWidget);

      // 2. Company Home
      expect(find.text('Company Home'), findsOneWidget);

      // 3. MY WORKFORCE
      expect(find.text('MY WORKFORCE'), findsOneWidget);
      expect(find.text('Tied Technicians'), findsOneWidget);
      expect(find.text('Send Invitations'), findsOneWidget);
      expect(find.text('Employee Roster'), findsOneWidget);
      expect(find.text('Applications'), findsOneWidget);

      // 4. OPERATIONS
      expect(find.text('OPERATIONS'), findsOneWidget);
      expect(find.text('Field Jobs'), findsOneWidget);
      expect(find.text('Dispatch Radar'), findsOneWidget);
      expect(find.text('Company Profile'), findsOneWidget);

      // 5. FINANCE & LEDGER
      expect(find.text('FINANCE & LEDGER'), findsOneWidget);
      expect(find.text('Company Wallet'), findsOneWidget);
      expect(find.text('Transactions'), findsOneWidget);
      expect(find.text('Withdrawals'), findsOneWidget);
      expect(find.text('Payout Accounts'), findsOneWidget);

      // 6. TELEMETRY
      expect(find.text('TELEMETRY'), findsOneWidget);
      expect(find.text('Database & Egress'), findsOneWidget);
      expect(find.text('Reports & Audits'), findsOneWidget);

      // 7. Pinned Bottom
      expect(find.text('System Settings'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);
    });

    testWidgets('2. Navigation to new Admin modules from drawer works', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.adminHome,
        routes: [
          GoRoute(
            path: AppRoutes.adminHome,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Home View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminTiedTechnicians,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Tied Technicians View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminVendorInvitations,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Vendor Invitations View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminProviderProfile,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Provider Profile View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminSettings,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('System Settings View'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Tied Technicians
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Tied Technicians'));
      await tester.pumpAndSettle();
      expect(find.text('Tied Technicians View'), findsOneWidget);

      // Tap Send Invitations
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Send Invitations'));
      await tester.pumpAndSettle();
      expect(find.text('Vendor Invitations View'), findsOneWidget);

      // Tap Company Profile
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Company Profile'));
      await tester.pumpAndSettle();
      expect(find.text('Provider Profile View'), findsOneWidget);

      // Tap System Settings -> opens Admin Home / Workforce Operations Center
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();
      await tester.tap(find.text('System Settings'));
      await tester.pumpAndSettle();
      expect(find.text('Home View'), findsOneWidget);
    });

    testWidgets('3. Role Isolation: Super Admin features are isolated from Vendor Admin', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.adminHome,
        routes: [
          GoRoute(
            path: AppRoutes.adminHome,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Admin View'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      // Super Admin specific elements MUST NOT exist for Vendor Admin
      expect(find.text('SEVO Platform'), findsNothing);
      expect(find.text('Superadmin Console'), findsNothing);
      expect(find.text('PLATFORM GOVERNANCE'), findsNothing);
      expect(find.text('Vendor Directory'), findsNothing);
      expect(find.text('Platform Treasury'), findsNothing);
    });

    testWidgets('4. Role Isolation: Super Admin sees Platform Governance and Console', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.superAdminDashboard,
        routes: [
          GoRoute(
            path: AppRoutes.superAdminDashboard,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Super Admin View'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockSuperAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      expect(find.text('SEVO Platform'), findsOneWidget);
      expect(find.text('Superadmin Console'), findsOneWidget);
      expect(find.text('PLATFORM GOVERNANCE'), findsOneWidget);
      expect(find.text('Vendor Directory'), findsOneWidget);
    });
  });

  group('Company Home: Workforce Operations Center Tests', () {
    Widget createHomeScreen() {
      return ProviderScope(
        overrides: [
          authControllerProvider
              .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
          adminDashboardDataProvider
              .overrideWith((ref) => testDashboardData),
        ],
        child: const MaterialApp(
          home: AdminHomeScreen(),
        ),
      );
    }

    testWidgets('renders title, actions, 4 action center cards, 5 overview stats, and operations feed', (tester) async {
      await tester.pumpWidget(createHomeScreen());
      await tester.pumpAndSettle();

      // Header
      expect(find.text('Workforce Operations Center'), findsOneWidget);
      expect(
        find.text('Real-time personnel monitoring, dossier verifications, and dynamic dispatch'),
        findsOneWidget,
      );
      expect(find.text('Refresh Data'), findsOneWidget);
      expect(find.text('Open Dispatch Console'), findsOneWidget);

      // Action Center Cards
      expect(find.text('ACTION CENTER'), findsOneWidget);
      expect(find.text('Pending Applications'), findsOneWidget);
      expect(find.text('Active Technicians'), findsOneWidget);
      expect(find.text('Jobs Awaiting Assignment'), findsOneWidget);
      expect(find.text('Corrections Pending Resubmission'), findsOneWidget);

      // Workforce Overview Stats
      expect(find.text('WORKFORCE OVERVIEW'), findsOneWidget);
      expect(find.text('Total Registered'), findsOneWidget);
      expect(find.text('Approved & Active'), findsOneWidget);
      expect(find.text('Online & Available'), findsOneWidget);
      expect(find.text('On Active Jobs'), findsOneWidget);
      expect(find.text('Pending Review'), findsOneWidget);

      // Recent Operations
      expect(find.textContaining('Recent Operations & Service Bookings (2)'), findsOneWidget);
      expect(find.text('View All Jobs'), findsOneWidget);
      expect(find.text('SR-801'), findsOneWidget);
      expect(find.text('SR-802'), findsOneWidget);
    });

    testWidgets('dynamic metric calculations are correct from live testDashboardData', (tester) async {
      // Pending Applications (submitted + under_review) = 2
      expect(testDashboardData.pendingApplicationsCount, 2);
      // Active Technicians (approved) = 2
      expect(testDashboardData.approvedAndActiveCount, 2);
      // Jobs Awaiting Assignment (new_request) = 1
      expect(testDashboardData.unassignedJobsCount, 1);
      // Corrections Pending Resubmission = 1
      expect(testDashboardData.correctionsPendingCount, 1);

      // Workforce Overview metrics
      expect(testDashboardData.totalRegisteredCount, 5);
      expect(testDashboardData.onlineAndAvailableCount, 1);
      expect(testDashboardData.onActiveJobsCount, 1);
      expect(testDashboardData.pendingReviewCount, 2);
    });

    testWidgets('renders empty state cleanly when zero jobs exist', (tester) async {
      final emptyDashboardData = AdminDashboardData(
        applications: mockApplications,
        jobs: const [],
        fleet: mockFleet,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
            adminDashboardDataProvider
                .overrideWith((ref) => emptyDashboardData),
          ],
          child: const MaterialApp(
            home: AdminHomeScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No Active Operations'), findsOneWidget);
      expect(find.text('No active customer service operations in queue.'), findsOneWidget);
    });
  });

  group('Multi-Screen Responsive Tests (320px - 412px)', () {
    const screenWidths = [
      ('Small Phone (320px)', 320.0, 640.0),
      ('Standard Phone (360px)', 360.0, 780.0),
      ('Modern Phone (390px)', 390.0, 844.0),
      ('Large Phone (412px)', 412.0, 915.0),
    ];

    for (final (name, width, height) in screenWidths) {
      testWidgets('HomeScreen on $name renders without RenderFlex overflow', (tester) async {
        tester.view.physicalSize = Size(width * 2, height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());
        addTearDown(() => tester.view.resetDevicePixelRatio());

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              authControllerProvider
                  .overrideWith((ref) => FakeAuthController(mockVendorAdminUser)),
              adminDashboardDataProvider
                  .overrideWith((ref) => testDashboardData),
            ],
            child: const MaterialApp(
              home: AdminHomeScreen(),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.text('Workforce Operations Center'), findsOneWidget);

        // Scroll full page
        await tester.drag(find.byType(ListView), const Offset(0, -500));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  });
}

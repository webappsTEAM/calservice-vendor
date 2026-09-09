import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_drawer.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/routing/app_routes.dart';

class FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const superAdminUser = AuthUser(
    id: 1,
    username: 'superadmin_test',
    email: 'superadmin@calservices.com',
    firstName: 'Platform',
    lastName: 'Superadmin',
    role: 'superadmin',
    companyId: 1,
    companyName: 'SEVO Platform Operations Ltd',
    isSuperuser: true,
    isPlatformAdmin: true,
    userType: 'platform_admin',
    employeeId: null,
    registrationStatus: 'approved',
  );

  const vendorAdminUser = AuthUser(
    id: 2,
    username: 'vendor_admin_test',
    email: 'vendor@coolcare.com',
    firstName: 'Vendor',
    lastName: 'Manager',
    role: 'admin',
    companyId: 10,
    companyName: 'CoolCare Services Ltd',
    isSuperuser: false,
    isPlatformAdmin: false,
    isVendorAdmin: true,
    userType: 'vendor_admin',
    employeeId: null,
    registrationStatus: 'approved',
  );

  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  group('Super Admin Drawer Tests', () {
    testWidgets('1. Displays SEVO Platform / Superadmin Console branding & all sections', (tester) async {
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
              body: Text('Super Admin Dashboard Content'),
            ),
          ),
          GoRoute(path: AppRoutes.superAdminVendors, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.superAdminWorkforce, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.superAdminApplications, builder: (c, s) => const Scaffold()),
          GoRoute(path: '/workforce/platform/providers', builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.estimates, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminQuotationApprovals, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminInvoices, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminJobs, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminDispatch, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminSkills, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminPricingApprovals, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.performance, builder: (c, s) => const Scaffold()),
          GoRoute(path: AppRoutes.adminSocialSecurity, builder: (c, s) => const Scaffold()),
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
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
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

      // 1. TOP Identity
      expect(find.text('SEVO Platform'), findsOneWidget);
      expect(find.text('Superadmin Console'), findsOneWidget);
      expect(find.text('Platform Superadmin'), findsOneWidget);
      expect(find.text('SUPERADMIN'), findsOneWidget);
      expect(find.text('Platform Dashboard'), findsOneWidget);

      // 2. PLATFORM GOVERNANCE
      expect(find.text('PLATFORM GOVERNANCE'), findsOneWidget);
      expect(find.text('Vendor Directory'), findsOneWidget);
      expect(find.text('Workforce Roster'), findsOneWidget);
      expect(find.text('Applications Approval'), findsOneWidget);
      expect(find.text('Service Providers'), findsOneWidget);

      // 3. OPERATIONS HUB (9 modules in exact order)
      expect(find.text('OPERATIONS HUB'), findsOneWidget);
      expect(find.text('AC Estimations'), findsOneWidget);
      expect(find.text('Quotation Approvals'), findsOneWidget);
      expect(find.text('Invoices'), findsOneWidget);
      expect(find.text('Field Jobs'), findsOneWidget);
      expect(find.text('Dispatch Radar'), findsOneWidget);
      expect(find.text('Skills Master'), findsOneWidget);
      expect(find.text('Pricing Approval'), findsOneWidget);
      expect(find.text('Scorecards'), findsOneWidget);
      expect(find.text('Social Security'), findsOneWidget);

      // Scroll to see remaining sections
      await tester.drag(find.byType(ListView), const Offset(0, -300));
      await tester.pumpAndSettle();

      // 4. FINANCE & TREASURY
      expect(find.text('FINANCE & TREASURY'), findsOneWidget);
      expect(find.text('Platform Treasury'), findsOneWidget);
      expect(find.text('Transactions'), findsOneWidget);
      expect(find.text('Withdrawals'), findsOneWidget);
      expect(find.text('Payout Accounts'), findsOneWidget);

      // 5. TELEMETRY & AUDITS
      expect(find.text('TELEMETRY & AUDITS'), findsOneWidget);
      expect(find.text('Database & Egress'), findsOneWidget);
      expect(find.text('Reports & Audits'), findsOneWidget);

      // 6. BOTTOM
      expect(find.text('System Settings'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);
    });

    testWidgets('2. Navigation to AC Estimations and other modules works from Super Admin drawer', (tester) async {
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
              body: Text('Dashboard View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.estimates,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('AC Estimations View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.superAdminVendors,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Vendors View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminQuotationApprovals,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Quotation Approvals View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminInvoices,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Invoices View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminPricingApprovals,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Pricing Approvals View'),
            ),
          ),
          GoRoute(
            path: AppRoutes.adminSocialSecurity,
            builder: (context, state) => const Scaffold(
              drawer: AdminDrawer(),
              body: Text('Social Security View'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open drawer & tap AC Estimations
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      await tester.tap(find.text('AC Estimations'));
      await tester.pumpAndSettle();

      expect(find.text('AC Estimations View'), findsOneWidget);

      // Open drawer & tap Quotation Approvals
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      await tester.tap(find.text('Quotation Approvals'));
      await tester.pumpAndSettle();

      expect(find.text('Quotation Approvals View'), findsOneWidget);

      // Open drawer & tap Invoices
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      await tester.tap(find.text('Invoices'));
      await tester.pumpAndSettle();

      expect(find.text('Invoices View'), findsOneWidget);

      // Open drawer & tap Pricing & Approvals
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      await tester.tap(find.text('Pricing Approval'));
      await tester.pumpAndSettle();

      expect(find.text('Pricing Approvals View'), findsOneWidget);

      // Open drawer & tap Social Security
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      await tester.tap(find.text('Social Security'));
      await tester.pumpAndSettle();

      expect(find.text('Social Security View'), findsOneWidget);
    });

    testWidgets('3. Collapsible section toggling works in Super Admin drawer', (tester) async {
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
              body: Text('Dashboard'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      expect(find.text('Vendor Directory'), findsOneWidget);

      // Collapse PLATFORM GOVERNANCE
      await tester.tap(find.text('PLATFORM GOVERNANCE'));
      await tester.pumpAndSettle();

      expect(find.text('Vendor Directory'), findsNothing);

      // Expand PLATFORM GOVERNANCE
      await tester.tap(find.text('PLATFORM GOVERNANCE'));
      await tester.pumpAndSettle();

      expect(find.text('Vendor Directory'), findsOneWidget);
    });

    testWidgets('4. System Settings is visible before Log Out and navigates to AppRoutes.adminSettings', (tester) async {
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
              body: Text('Dashboard View'),
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
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open drawer
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      // Scroll to bottom of drawer to see System Settings and Log Out
      await tester.drag(find.byType(ListView), const Offset(0, -500));
      await tester.pumpAndSettle();

      expect(find.text('System Settings'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);

      // Verify System Settings appears above Log Out
      final settingsTop = tester.getTopLeft(find.text('System Settings')).dy;
      final logOutTop = tester.getTopLeft(find.text('Log Out')).dy;
      expect(settingsTop < logOutTop, isTrue, reason: 'System Settings should appear before Log Out');

      // Tap System Settings
      await tester.tap(find.text('System Settings'));
      await tester.pumpAndSettle();

      expect(find.text('System Settings View'), findsOneWidget);
    });

    testWidgets('5. System Settings active route highlighting works when on /admin/settings', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.adminSettings,
        routes: [
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
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open drawer
      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      // Scroll to bottom of drawer
      await tester.drag(find.byType(ListView), const Offset(0, -500));
      await tester.pumpAndSettle();

      expect(find.text('System Settings'), findsOneWidget);
    });
  });

  group('Role-Based Isolation Tests', () {
    testWidgets('Vendor Admin does NOT see Super Admin platform governance modules', (tester) async {
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
              body: Text('Vendor Admin Home'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(vendorAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
      await tester.pumpAndSettle();

      // Vendor Admin branding
      expect(find.text('SEVO'), findsOneWidget);
      expect(find.text('WORKFORCE ADMIN'), findsOneWidget);
      expect(find.text('ADMIN'), findsOneWidget);

      // Vendor Admin navigation structure
      expect(find.text('Company Home'), findsOneWidget);
      expect(find.text('MY WORKFORCE'), findsOneWidget);
      expect(find.text('Tied Technicians'), findsOneWidget);
      expect(find.text('Send Invitations'), findsOneWidget);
      expect(find.text('Employee Roster'), findsOneWidget);
      expect(find.text('Applications'), findsOneWidget);
      expect(find.text('OPERATIONS'), findsOneWidget);
      expect(find.text('Field Jobs'), findsOneWidget);
      expect(find.text('Dispatch Radar'), findsOneWidget);
      expect(find.text('Company Profile'), findsOneWidget);
      expect(find.text('FINANCE & LEDGER'), findsOneWidget);
      expect(find.text('Company Wallet'), findsOneWidget);

      // Super Admin modules MUST NOT be visible to Vendor Admin
      expect(find.text('SEVO Platform'), findsNothing);
      expect(find.text('Superadmin Console'), findsNothing);
      expect(find.text('PLATFORM GOVERNANCE'), findsNothing);
      expect(find.text('Vendor Directory'), findsNothing);
      expect(find.text('Workforce Roster'), findsNothing);
      expect(find.text('Applications Approval'), findsNothing);
      expect(find.text('Platform Treasury'), findsNothing);
    });
  });

  group('Drawer Responsive Layout Tests (320px - 412px)', () {
    const phoneWidths = [
      ('Small Phone (320px)', 320.0, 640.0),
      ('Standard Phone (360px)', 360.0, 780.0),
      ('Modern Phone (390px)', 390.0, 844.0),
      ('Large Phone (412px)', 412.0, 915.0),
    ];

    for (final (name, width, height) in phoneWidths) {
      testWidgets('$name renders Super Admin drawer without overflow', (tester) async {
        tester.view.physicalSize = Size(width * 2, height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());

        FlutterErrorDetails? caughtDetails;
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (details) => caughtDetails = details;

        final router = GoRouter(
          initialLocation: AppRoutes.superAdminDashboard,
          routes: [
            GoRoute(
              path: AppRoutes.superAdminDashboard,
              builder: (context, state) => const Scaffold(
                drawer: AdminDrawer(),
                body: Text('Responsive Test'),
              ),
            ),
          ],
        );

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
            ],
            child: MaterialApp.router(
              routerConfig: router,
            ),
          ),
        );
        await tester.pumpAndSettle();

        tester.state<ScaffoldState>(find.byType(Scaffold)).openDrawer();
        await tester.pumpAndSettle();

        FlutterError.onError = originalOnError;
        expect(caughtDetails, isNull, reason: caughtDetails?.summary.toString());
        expect(find.text('SEVO Platform'), findsOneWidget);
        expect(find.text('Superadmin Console'), findsOneWidget);
      });
    }
  });

  group('AuthUser Role & System Settings Guard Tests', () {
    test('Superadmin JSON correctly marks isAdmin=true, isSuperAdmin=true, isEmployee=false', () {
      final user = AuthUser.fromJson({
        'id': 1,
        'username': 'superadmin',
        'email': 'superadmin@calservices.com',
        'first_name': 'Super',
        'last_name': 'Admin',
        'role': 'superadmin',
        'is_superuser': false,
        'is_platform_admin': false,
        'company': 1,
        'registration_status': 'approved',
      });

      expect(user.isSuperAdmin, isTrue);
      expect(user.isAdmin, isTrue);
      expect(user.isEmployee, isFalse);
    });

    test('Platform admin JSON correctly marks isAdmin=true, isSuperAdmin=true, isEmployee=false', () {
      final user = AuthUser.fromJson({
        'id': 2,
        'username': 'platform_admin',
        'email': 'admin@calservices.com',
        'first_name': 'Platform',
        'last_name': 'Admin',
        'user_type': 'platform_admin',
        'role': 'platform_admin',
        'company': null,
        'registration_status': 'approved',
      });

      expect(user.isSuperAdmin, isTrue);
      expect(user.isAdmin, isTrue);
      expect(user.isEmployee, isFalse);
    });

    test('Vendor admin JSON correctly marks isAdmin=true, isSuperAdmin=false, isEmployee=false', () {
      final user = AuthUser.fromJson({
        'id': 3,
        'username': 'vendor_admin',
        'email': 'vendor@coolcare.com',
        'first_name': 'Vendor',
        'last_name': 'Manager',
        'role': 'admin',
        'company': 10,
        'is_vendor_admin': true,
        'registration_status': 'approved',
      });

      expect(user.isSuperAdmin, isFalse);
      expect(user.isAdmin, isTrue);
      expect(user.isEmployee, isFalse);
    });

    test('Technician JSON correctly marks isAdmin=false, isSuperAdmin=false, isEmployee=true', () {
      final user = AuthUser.fromJson({
        'id': 4,
        'username': 'tech_user',
        'email': 'tech@coolcare.com',
        'first_name': 'John',
        'last_name': 'Tech',
        'role': 'employee',
        'company': 10,
        'is_technician': true,
        'registration_status': 'approved',
      });

      expect(user.isSuperAdmin, isFalse);
      expect(user.isAdmin, isFalse);
      expect(user.isEmployee, isTrue);
    });

    testWidgets('System Settings in Admin mode opens/redirects to Platform Dashboard', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final router = GoRouter(
        initialLocation: AppRoutes.adminSettings,
        routes: [
          GoRoute(
            path: AppRoutes.adminSettings,
            redirect: (context, state) => AppRoutes.superAdminDashboard,
          ),
          GoRoute(
            path: AppRoutes.superAdminDashboard,
            builder: (context, state) => const Scaffold(
              body: Text('Workforce Operations Center Dashboard'),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(superAdminUser)),
          ],
          child: MaterialApp.router(
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Workforce Operations Center Dashboard'), findsOneWidget);
    });
  });
}

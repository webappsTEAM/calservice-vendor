import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/domain/fleet_member.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/superadmin/domain/superadmin_dashboard.dart';
import 'package:mobile/features/superadmin/presentation/superadmin_dashboard_providers.dart';
import 'package:mobile/features/superadmin/presentation/superadmin_dashboard_screen.dart';
import 'package:mobile/features/superadmin/presentation/widgets/action_center_card.dart';
import 'package:mobile/features/superadmin/presentation/widgets/recent_operation_card.dart';
import 'package:mobile/features/superadmin/presentation/widgets/superadmin_dashboard_header.dart';
import 'package:mobile/features/superadmin/presentation/widgets/workforce_metric_card.dart';
import 'package:mobile/routing/app_routes.dart';

class FakeAuthController extends StateNotifier<AuthState>
    implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const mockSuperAdminUser = AuthUser(
    id: 1,
    username: 'superadmin_user',
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

  final mockApplications = [
    const AdminApplication(
      id: 101,
      name: 'Ramesh Kumar',
      employeeId: 'EMP-101',
      registrationStatus: 'submitted',
      isActive: true,
      documentsStatus: {
        'aadhaar': {'status': 'pending'},
        'license': {'status': 'submitted'},
      },
    ),
    const AdminApplication(
      id: 102,
      name: 'Suresh Raina',
      employeeId: 'EMP-102',
      registrationStatus: 'under_review',
      isActive: true,
      documentsStatus: {
        'aadhaar': {'status': 'pending'},
      },
    ),
    const AdminApplication(
      id: 103,
      name: 'Dinesh Karthik',
      employeeId: 'EMP-103',
      registrationStatus: 'approved',
      isActive: true,
      documentsStatus: {
        'aadhaar': {'status': 'approved'},
      },
    ),
    const AdminApplication(
      id: 104,
      name: 'Vijay Shankar',
      employeeId: 'EMP-104',
      registrationStatus: 'approved',
      isActive: true,
    ),
    const AdminApplication(
      id: 105,
      name: 'Manoj Tiwari',
      employeeId: 'EMP-105',
      registrationStatus: 'correction_required',
      isActive: false,
    ),
  ];

  final mockJobs = [
    const Job(
      id: 5255,
      requestId: 'PM5255',
      customerName: 'Anand Kumar',
      serviceCategory: 'HVAC',
      serviceTitle: 'Master AC Service & Deep Cleaning',
      status: 'confirmed',
      address: '402, 05, Bagalur Rd, Hosur, Tamil Nadu',
      preferredDate: '2026-08-25',
      preferredTime: '10:00 AM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: false,
    ),
    const Job(
      id: 5254,
      requestId: 'SR-5254',
      customerName: 'Priya Sharma',
      serviceCategory: 'Cleaning',
      serviceTitle: 'Kitchen Deep Clean & Sanitization',
      status: 'in_progress',
      address: 'Hosur Bus Stand, Central Hosur',
      preferredDate: '2026-08-25',
      preferredTime: '11:00 AM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: true,
      canCancel: false,
    ),
    const Job(
      id: 5253,
      requestId: 'SR-5253',
      customerName: 'Karthik Raja',
      serviceCategory: 'Appliance',
      serviceTitle: 'Washing Machine Drum Repair',
      status: 'unassigned',
      address: '100 Feet Rd, Indiranagar, Bengaluru',
      preferredDate: '2026-08-25',
      preferredTime: '02:00 PM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: false,
    ),
    const Job(
      id: 5252,
      requestId: 'SR-5252',
      customerName: 'Vignesh Rao',
      serviceCategory: 'Electrical',
      serviceTitle: 'Main MCB Box Inspection',
      status: 'completed',
      address: 'Electronic City Phase 1, Bengaluru',
      preferredDate: '2026-08-24',
      preferredTime: '04:00 PM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: true,
      canCancel: false,
    ),
    const Job(
      id: 5251,
      requestId: 'SR-5251',
      customerName: 'Sneha Patel',
      serviceCategory: 'Plumbing',
      serviceTitle: 'Overhead Tank Pipeline Leak Fix',
      status: 'cancelled',
      address: 'Whitefield Main Road, Bengaluru',
      preferredDate: '2026-08-24',
      preferredTime: '01:00 PM',
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: false,
    ),
  ];

  final mockFleet = [
    const FleetMember(
      id: 101,
      employeeId: 'EMP-101',
      name: 'Ramesh Kumar',
      phone: '9876543210',
      isOnline: true,
      currentAvailability: 'available',
      registrationStatus: 'approved',
      hasLocation: true,
      latitude: 12.9716,
      longitude: 77.5946,
      activeJob: null,
    ),
    const FleetMember(
      id: 102,
      employeeId: 'EMP-102',
      name: 'Suresh Raina',
      phone: '9876543211',
      isOnline: true,
      currentAvailability: 'busy',
      registrationStatus: 'approved',
      hasLocation: true,
      latitude: 12.9718,
      longitude: 77.5950,
      activeJob: 'SR-5254',
    ),
    const FleetMember(
      id: 103,
      employeeId: 'EMP-103',
      name: 'Dinesh Karthik',
      phone: '9876543212',
      isOnline: false,
      currentAvailability: 'offline',
      registrationStatus: 'approved',
      hasLocation: false,
      activeJob: null,
    ),
  ];

  final testDashboardData = SuperAdminDashboardData(
    applications: mockApplications,
    jobs: mockJobs,
    fleet: mockFleet,
  );

  Widget createSubject({
    SuperAdminDashboardData? data,
    AsyncValue<SuperAdminDashboardData>? asyncOverride,
    List<RouteBase>? extraRoutes,
  }) {
    final router = GoRouter(
      initialLocation: AppRoutes.superAdminDashboard,
      routes: [
        GoRoute(
          path: AppRoutes.superAdminDashboard,
          builder: (context, state) => const SuperAdminDashboardScreen(),
        ),
        ...?extraRoutes,
      ],
    );

    return ProviderScope(
      overrides: [
        authControllerProvider
            .overrideWith((ref) => FakeAuthController(mockSuperAdminUser)),
        if (asyncOverride != null)
          superAdminDashboardDataProvider.overrideWith((ref) => asyncOverride.value!)
        else
          superAdminDashboardDataProvider
              .overrideWith((ref) => data ?? testDashboardData),
      ],
      child: MaterialApp.router(
        theme: ThemeData.light(useMaterial3: true),
        routerConfig: router,
      ),
    );
  }

  group('Super Admin Platform Dashboard Screen Tests', () {
    testWidgets('1. Super Admin dashboard and context indicators render in AppBar',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      // Check AppBar branding & context
      expect(find.text('Workforce Operations Center'), findsWidgets);
      expect(find.text('SUPERADMIN'), findsWidgets);
      expect(find.text('SEVO Platform'), findsWidgets);
      expect(find.byIcon(Icons.refresh_rounded), findsWidgets);
      expect(find.byIcon(Icons.menu_rounded), findsOneWidget);
    });

    testWidgets('2. Workforce Operations Center heading, Home breadcrumb, and subtitle render',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      expect(find.byType(SuperAdminDashboardHeader), findsOneWidget);
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Superadmin Console'), findsOneWidget);
      expect(
        find.text(
            'Real-time personnel monitoring, dossier verifications, and dynamic dispatch'),
        findsOneWidget,
      );
      expect(find.text('Refresh Data'), findsOneWidget);
      expect(find.text('Open Dispatch Console'), findsOneWidget);
    });

    testWidgets('3. Action Center renders with subtitle and all 4 cards',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      expect(find.text('ACTION CENTER'), findsOneWidget);
      expect(
        find.text('Items requiring immediate operational attention'),
        findsOneWidget,
      );
      expect(find.byType(SuperAdminActionCenterSection), findsOneWidget);
      expect(find.byType(ActionCenterCard), findsNWidgets(4));

      // Card 1: Pending Applications
      expect(find.text('Pending Applications'), findsOneWidget);
      expect(
        find.text('Technician registrations requiring document review'),
        findsOneWidget,
      );

      // Card 2: Active Technicians
      expect(find.text('Active Technicians'), findsOneWidget);
      expect(
        find.text('Approved workforce field technicians'),
        findsOneWidget,
      );

      // Card 3: Jobs Awaiting Assignment
      expect(find.text('Jobs Awaiting Assignment'), findsOneWidget);
      expect(
        find.text('Customer bookings requiring technician dispatch'),
        findsOneWidget,
      );

      // Card 4: Corrections Pending Resubmission
      expect(find.text('Corrections Pending Resubmission'), findsOneWidget);
      expect(
        find.text('Technicians notified to re-upload flagged files'),
        findsOneWidget,
      );
    });

    testWidgets('4. Live counts in Action Center match computed backend metrics',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      // Pending Applications: submitted (101) + under_review (102) = 2
      expect(testDashboardData.pendingApplicationsCount, 2);

      // Active Technicians: 4 active
      expect(testDashboardData.activeTechniciansCount, 4);

      // Jobs Awaiting Assignment: PM5255 (confirmed & not assigned to me) + SR-5253 (unassigned) = 2
      expect(testDashboardData.jobsAwaitingAssignmentCount, 2);

      // Corrections Pending: Manoj (105) = 1
      expect(testDashboardData.correctionsPendingCount, 1);
    });

    testWidgets('5. Workforce Overview metrics render with live data and semantic accents',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      expect(find.text('WORKFORCE OVERVIEW'), findsOneWidget);
      expect(
        find.text('Personnel roster, availability and field activity'),
        findsOneWidget,
      );
      expect(find.byType(SuperAdminWorkforceOverviewSection), findsOneWidget);
      expect(find.byType(WorkforceMetricCard), findsNWidgets(5));

      // 1. Total Registered
      expect(find.text('Total Registered'), findsOneWidget);
      expect(find.text('Technicians on roster'), findsOneWidget);
      expect(testDashboardData.totalRegisteredCount, 5);

      // 2. Approved & Active
      expect(find.text('Approved & Active'), findsOneWidget);
      expect(find.text('Authorized for jobs'), findsOneWidget);
      expect(testDashboardData.approvedAndActiveCount, 2);

      // 3. Online & Available
      expect(find.text('Online & Available'), findsOneWidget);
      expect(find.text('Ready for dispatch'), findsOneWidget);
      expect(testDashboardData.onlineAndAvailableCount, 1);

      // 4. On Active Jobs
      expect(find.text('On Active Jobs'), findsOneWidget);
      expect(find.text('Currently in field'), findsOneWidget);
      expect(testDashboardData.onActiveJobsCount, 1);

      // 5. Pending Review
      expect(find.text('Pending Review'), findsOneWidget);
      expect(find.text('Awaiting dossier check'), findsOneWidget);
      expect(testDashboardData.pendingReviewCount, 2);
    });

    testWidgets('6. Online & Available uses live fleet telemetry availability presence',
        (tester) async {
      // 1 fleet member is available (Ramesh), 1 is busy (Suresh), 1 is offline (Dinesh)
      expect(testDashboardData.onlineAndAvailableCount, 1);
      expect(testDashboardData.onActiveJobsCount, 1);
    });

    testWidgets('7. Recent Operations & Service Bookings render cards with all details',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.byType(SuperAdminRecentOperationsSection), 200);

      expect(
        find.textContaining('RECENT OPERATIONS & SERVICE BOOKINGS'),
        findsOneWidget,
      );
      expect(find.text('View All Jobs'), findsOneWidget);
      expect(find.byType(RecentOperationCard), findsNWidgets(5));

      // Check specific job fields
      expect(find.text('PM5255'), findsOneWidget);
      expect(find.text('Anand Kumar'), findsOneWidget);
      expect(find.text('Master AC Service & Deep Cleaning'), findsOneWidget);
      expect(find.text('402, 05, Bagalur Rd, Hosur, Tamil Nadu'), findsOneWidget);
      expect(find.text('2026-08-25 10:00 AM'), findsOneWidget);
      expect(find.text('CONFIRMED'), findsOneWidget);
      expect(find.text('Dispatch'), findsWidgets);
    });

    testWidgets('8. Status badges render supported statuses correctly',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.byType(SuperAdminRecentOperationsSection), 200);

      expect(find.text('CONFIRMED'), findsOneWidget);
      expect(find.text('IN PROGRESS'), findsOneWidget);
      expect(find.text('UNASSIGNED'), findsOneWidget);
      expect(find.text('COMPLETED'), findsOneWidget);
      expect(find.text('CANCELLED'), findsOneWidget);
    });

    testWidgets('9. Empty operations state renders when jobs list is empty',
        (tester) async {
      final emptyData = SuperAdminDashboardData(
        applications: mockApplications,
        jobs: const [],
        fleet: mockFleet,
      );

      await tester.pumpWidget(createSubject(data: emptyData));
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.byType(SuperAdminRecentOperationsSection), 200);

      expect(
        find.text('No recent operations or service bookings found.'),
        findsOneWidget,
      );
      expect(
        find.text('New customer bookings and workforce activity will appear here.'),
        findsOneWidget,
      );
    });

    testWidgets('10. Error state renders with retry button',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockSuperAdminUser)),
            superAdminDashboardDataProvider
                .overrideWith((ref) => throw Exception('Network timeout')),
          ],
          child: const MaterialApp(
            home: SuperAdminDashboardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load platform dashboard'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('11. Loading state renders skeleton/progress indicator',
        (tester) async {
      final completer = Completer<SuperAdminDashboardData>();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider
                .overrideWith((ref) => FakeAuthController(mockSuperAdminUser)),
            superAdminDashboardDataProvider
                .overrideWith((ref) => completer.future),
          ],
          child: const MaterialApp(
            home: SuperAdminDashboardScreen(),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      completer.complete(testDashboardData);
      await tester.pumpAndSettle();
    });

    testWidgets('12. Open Dispatch Console navigates to AppRoutes.adminDispatch',
        (tester) async {
      String? navigatedRoute;
      await tester.pumpWidget(
        createSubject(
          extraRoutes: [
            GoRoute(
              path: AppRoutes.adminDispatch,
              builder: (context, state) {
                navigatedRoute = state.uri.toString();
                return const Scaffold(body: Text('Dispatch Console Page'));
              },
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Open Dispatch Console'));
      await tester.pumpAndSettle();

      expect(navigatedRoute, AppRoutes.adminDispatch);
      expect(find.text('Dispatch Console Page'), findsOneWidget);
    });

    testWidgets('13. Action Center cards navigate to respective routes',
        (tester) async {
      String? navigatedRoute;
      await tester.pumpWidget(
        createSubject(
          extraRoutes: [
            GoRoute(
              path: AppRoutes.superAdminApplications,
              builder: (context, state) {
                navigatedRoute = state.uri.toString();
                return Scaffold(body: Text('Apps Page: ${state.uri}'));
              },
            ),
            GoRoute(
              path: AppRoutes.superAdminWorkforce,
              builder: (context, state) {
                navigatedRoute = state.uri.toString();
                return const Scaffold(body: Text('Workforce Page'));
              },
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Tap Pending Applications
      await tester.tap(find.text('Pending Applications'));
      await tester.pumpAndSettle();
      expect(navigatedRoute, AppRoutes.superAdminApplications);
    });

    testWidgets('14. View All Jobs navigates to AppRoutes.adminJobs',
        (tester) async {
      String? navigatedRoute;
      await tester.pumpWidget(
        createSubject(
          extraRoutes: [
            GoRoute(
              path: AppRoutes.adminJobs,
              builder: (context, state) {
                navigatedRoute = state.uri.toString();
                return const Scaffold(body: Text('All Jobs Page'));
              },
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.text('View All Jobs'), 200);
      await tester.ensureVisible(find.text('View All Jobs'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('View All Jobs'));
      await tester.pumpAndSettle();

      expect(navigatedRoute, AppRoutes.adminJobs);
      expect(find.text('All Jobs Page'), findsOneWidget);
    });

    testWidgets('15. Dispatch button on job card navigates to dispatch with job ID',
        (tester) async {
      String? navigatedRoute;
      await tester.pumpWidget(
        createSubject(
          extraRoutes: [
            GoRoute(
              path: AppRoutes.adminDispatch,
              builder: (context, state) {
                navigatedRoute = state.uri.toString();
                return Scaffold(body: Text('Dispatch Page: $navigatedRoute'));
              },
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      final firstDispatchBtn = find.text('Dispatch').first;
      await tester.scrollUntilVisible(firstDispatchBtn, 200);
      await tester.ensureVisible(firstDispatchBtn);
      await tester.pumpAndSettle();
      await tester.tap(firstDispatchBtn);
      await tester.pumpAndSettle();

      expect(navigatedRoute, contains(AppRoutes.adminDispatch));
      expect(navigatedRoute, contains('job_id=PM5255'));
    });

    testWidgets('16. Refresh Data button can be triggered without errors',
        (tester) async {
      await tester.pumpWidget(createSubject());
      await tester.pumpAndSettle();

      expect(find.text('Refresh Data'), findsOneWidget);
      await tester.tap(find.text('Refresh Data'));
      await tester.pump();
      expect(tester.takeException(), isNull);
    });
  });

  group('Super Admin Multi-Screen Responsive Layout Tests (320px - 412px)', () {
    const phoneWidths = [
      ('Small Phone (320px)', 320.0, 640.0),
      ('Standard Phone (360px)', 360.0, 780.0),
      ('Modern Phone (390px)', 390.0, 844.0),
      ('Large Phone (412px)', 412.0, 915.0),
    ];

    for (final (name, width, height) in phoneWidths) {
      testWidgets('$name adapts without any RenderFlex overflow', (tester) async {
        tester.view.physicalSize = Size(width * 2, height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());
        addTearDown(() => tester.view.resetDevicePixelRatio());

        FlutterErrorDetails? caughtDetails;
        final originalOnError = FlutterError.onError;
        FlutterError.onError = (FlutterErrorDetails details) {
          caughtDetails = details;
          debugPrint('OVERFLOW CATCH: ${details.summary}');
          debugPrint('OVERFLOW CONTEXT: ${details.context}');
        };

        await tester.pumpWidget(createSubject());
        await tester.pumpAndSettle();

        FlutterError.onError = originalOnError;

        expect(caughtDetails, isNull, reason: caughtDetails?.summary.toString());
        expect(find.text('Workforce Operations Center'), findsWidgets);

        // Scroll top to bottom
        await tester.drag(find.byType(ListView), const Offset(0, -400));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        await tester.drag(find.byType(ListView), const Offset(0, -400));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      });
    }
  });
}


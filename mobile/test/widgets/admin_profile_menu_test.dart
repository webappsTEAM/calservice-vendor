import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/admin/presentation/widgets/admin_title_section.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';
import 'package:mobile/routing/app_routes.dart';
import 'package:mobile/shared/widgets/workforce_app_bar.dart';

class _FakeAuthController extends StateNotifier<AuthState>
    implements AuthController {
  _FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const adminUser = AuthUser(
    id: 1,
    username: 'admin_user',
    email: 'admin@calservices.com',
    firstName: 'John',
    lastName: 'Doe',
    role: 'admin',
    companyId: 1,
    companyName: 'CalServices Enterprise',
    isSuperuser: true,
    employeeId: null,
    registrationStatus: 'approved',
  );

  const technicianUser = AuthUser(
    id: 2,
    username: 'mani_tech',
    email: 'mani@calservices.com',
    firstName: 'Mani',
    lastName: 'S',
    role: 'employee',
    companyId: 1,
    companyName: 'CalServices Enterprise',
    isSuperuser: false,
    employeeId: 'EMP-002',
    registrationStatus: 'approved',
  );

  Widget createSubject({
    required AuthUser user,
    required Widget child,
    List<GoRoute>? routes,
  }) {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => child,
        ),
        GoRoute(
          path: AppRoutes.moreProfile,
          builder: (context, state) => const Scaffold(body: Text('Profile Screen Target')),
        ),
        GoRoute(
          path: AppRoutes.moreSettings,
          builder: (context, state) => const Scaffold(body: Text('Settings Screen Target')),
        ),
        GoRoute(
          path: AppRoutes.adminMonitoringDatabaseEgress,
          builder: (context, state) => const Scaffold(body: Text('Database Egress Target')),
        ),
        GoRoute(
          path: AppRoutes.adminDispatch,
          builder: (context, state) => const Scaffold(body: Text('Dispatch Console Target')),
        ),
        ...?routes,
      ],
    );

    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith((ref) => _FakeAuthController(user)),
        unreadNotificationsCountProvider.overrideWithValue(0),
      ],
      child: MaterialApp.router(
        routerConfig: router,
      ),
    );
  }

  group('Task 1: Profile Icon Dropdown / Menu Tests', () {
    testWidgets('Admin user sees dynamic name, ADMIN badge, and Database Egress option', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: adminUser,
          child: const Scaffold(
            appBar: WorkforceAppBar(
              titleText: 'Workforce Operations',
            ),
            body: Center(child: Text('Admin Dashboard Content')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Profile avatar in header
      final avatarFinder = find.byType(InkWell).last;
      await tester.tap(avatarFinder);
      await tester.pumpAndSettle();

      // Verify Menu Header
      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('ADMIN'), findsOneWidget);
      expect(find.text('admin@calservices.com'), findsOneWidget);

      // Verify Menu Options
      expect(find.text('My Profile'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
      expect(find.text('Database Egress'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);

      // Verify Database Egress navigation
      await tester.tap(find.text('Database Egress'));
      await tester.pumpAndSettle();
      expect(find.text('Database Egress Target'), findsOneWidget);
    });

    testWidgets('Admin user can navigate to My Profile from popup menu', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: adminUser,
          child: const Scaffold(
            appBar: WorkforceAppBar(
              titleText: 'Workforce Operations',
            ),
            body: Center(child: Text('Admin Dashboard Content')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final avatarFinder = find.byType(InkWell).last;
      await tester.tap(avatarFinder);
      await tester.pumpAndSettle();

      await tester.tap(find.text('My Profile'));
      await tester.pumpAndSettle();
      expect(find.text('Profile Screen Target'), findsOneWidget);
    });

    testWidgets('Admin user can navigate to Settings from popup menu', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: adminUser,
          child: const Scaffold(
            appBar: WorkforceAppBar(
              titleText: 'Workforce Operations',
            ),
            body: Center(child: Text('Admin Dashboard Content')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final avatarFinder = find.byType(InkWell).last;
      await tester.tap(avatarFinder);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.text('Settings Screen Target'), findsOneWidget);
    });

    testWidgets('Technician user sees TECHNICIAN badge and does NOT see Database Egress', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: technicianUser,
          child: const Scaffold(
            appBar: WorkforceAppBar(
              titleText: 'Technician Home',
            ),
            body: Center(child: Text('Technician Dashboard Content')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Profile avatar in header
      final avatarFinder = find.byType(InkWell).last;
      await tester.tap(avatarFinder);
      await tester.pumpAndSettle();

      // Verify Menu Header
      expect(find.text('Mani S'), findsOneWidget);
      expect(find.text('TECHNICIAN'), findsOneWidget);
      expect(find.text('mani@calservices.com'), findsOneWidget);

      // Verify Menu Options
      expect(find.text('My Profile'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);

      // STRICT RULE: Database Egress MUST NOT be visible for technician
      expect(find.text('Database Egress'), findsNothing);
    });
  });

  group('Task 2: Admin Home Page Database Egress Button Tests', () {
    testWidgets('Renders Database Egress button for Admin user and navigates on tap', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: adminUser,
          child: Scaffold(
            body: AdminTitleSection(
              onRefresh: () {},
              isRefreshing: false,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify buttons
      expect(find.text('Refresh Data'), findsOneWidget);
      expect(find.text('Database Egress'), findsOneWidget);
      expect(find.text('Open Dispatch Console'), findsOneWidget);

      // Tap Database Egress button
      await tester.tap(find.text('Database Egress'));
      await tester.pumpAndSettle();

      expect(find.text('Database Egress Target'), findsOneWidget);
    });

    testWidgets('Does not render Database Egress button in AdminTitleSection if non-admin', (tester) async {
      await tester.pumpWidget(
        createSubject(
          user: technicianUser,
          child: Scaffold(
            body: AdminTitleSection(
              onRefresh: () {},
              isRefreshing: false,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Refresh Data'), findsOneWidget);
      expect(find.text('Database Egress'), findsNothing);
      expect(find.text('Open Dispatch Console'), findsOneWidget);
    });
  });
}

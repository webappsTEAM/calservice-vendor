import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/more/presentation/more_screen.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/shared/widgets/workforce_avatar.dart';

void main() {
  const testUser = AuthUser(
    id: 101,
    username: 'karthik_r',
    email: 'karthik@technicians.com',
    role: 'employee',
    registrationStatus: 'approved',
    firstName: 'Karthik',
    lastName: 'Raman',
    companyId: 5,
    companyName: 'Apex Air Conditioning Services',
    isSuperuser: false,
    employeeId: 'EMP-101',
  );

  final testProfile = EmployeeProfile(
    employeeId: 'EMP-101',
    firstName: 'Karthik',
    lastName: 'Raman',
    email: 'karthik@technicians.com',
    mobileNumber: '+91 98765 11223',
    title: 'Senior HVAC Specialist',
    companyName: 'Apex Air Conditioning Services',
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
      authControllerProvider.overrideWith((ref) => _FakeAuthController(testUser)),
      employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
      activeJobsProvider.overrideWith((ref) => Future.value(<Job>[])),
      completedJobsProvider.overrideWith((ref) => Future.value(<Job>[])),
    ];
  }

  group('MoreScreen Widget Tests', () {
    testWidgets('renders Employee Profile Header with avatar, name, role, presence, company, and View My Profile', (tester) async {
      tester.view.physicalSize = const Size(1080, 3600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: const MaterialApp(
            home: MoreScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // WorkforceAvatar rendered
      expect(find.byType(WorkforceAvatar), findsAtLeastNWidgets(1));

      // Name, Role & Company rendered
      expect(find.text('Karthik Raman'), findsOneWidget);
      expect(find.text('Senior HVAC Specialist'), findsOneWidget);
      expect(find.text('Apex Air Conditioning Services'), findsOneWidget);

      // Presence Badge
      expect(find.text('AVAILABLE'), findsOneWidget);

      // "View My Profile" Action Button
      expect(find.text('View My Profile'), findsOneWidget);
    });

    testWidgets('renders all 4 grouped navigation sections matching Web IA', (tester) async {
      tester.view.physicalSize = const Size(1080, 3600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: const MaterialApp(
            home: MoreScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Section Headers
      expect(find.text('MY WORK'), findsOneWidget);
      expect(find.text('CREDENTIALS'), findsOneWidget);
      expect(find.text('EARNINGS & WALLET'), findsOneWidget);
      expect(find.text('APP'), findsOneWidget);

      // MY WORK Items
      expect(find.text('Jobs'), findsOneWidget);
      expect(find.text('Estimates'), findsOneWidget);
      expect(find.text('Performance'), findsOneWidget);
      expect(find.text('Vendor Invitations'), findsOneWidget);

      // CREDENTIALS Items
      expect(find.text('My Profile'), findsOneWidget);
      expect(find.text('Documents'), findsOneWidget);
      expect(find.text('Services & Skills'), findsOneWidget);
      expect(find.text('Locations'), findsOneWidget);

      // EARNINGS & WALLET Items
      expect(find.text('Wallet'), findsOneWidget);
      expect(find.text('Transactions'), findsOneWidget);
      expect(find.text('Withdrawals'), findsOneWidget);
      expect(find.text('Bank Accounts'), findsOneWidget);

      // APP Items
      expect(find.text('Settings'), findsOneWidget);
      expect(find.text('Log Out'), findsOneWidget);
    });

    testWidgets('tapping Logout shows confirmation dialog', (tester) async {
      tester.view.physicalSize = const Size(1080, 3600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(),
          child: const MaterialApp(
            home: MoreScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Logout
      await tester.tap(find.text('Log Out'));
      await tester.pumpAndSettle();

      // Dialog is shown
      expect(find.text('Are you sure you want to log out of SEVO Workforce?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
    });
  });
}

class _FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  _FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/location/location_service.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/dashboard/presentation/home_screen.dart';
import 'package:mobile/features/dashboard/presentation/widgets/authorized_services_card.dart';
import 'package:mobile/features/dashboard/presentation/widgets/dashboard_live_map.dart';
import 'package:mobile/features/dashboard/presentation/widgets/dashboard_status_card.dart';
import 'package:mobile/features/dashboard/presentation/widgets/greeting_header.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/domain/shift_status.dart';
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
    approvedServices: const [
      ApprovedService(
        id: 1,
        name: 'AC Deep Cleaning & Sanitization',
      ),
      ApprovedService(
        id: 2,
        name: 'Copper Pipe Replacement',
      ),
    ],
    allRequestedServices: const [
      RequestedService(
        id: 1,
        name: 'AC Deep Cleaning & Sanitization',
        status: 'approved',
      ),
      RequestedService(
        id: 2,
        name: 'Copper Pipe Replacement',
        status: 'approved',
      ),
    ],
    documents: const [],
    controlledFields: const ControlledFieldsConfig(
      isLocked: false,
      lockedFields: [],
    ),
  );

  final sampleCompletedJob = Job(
    id: 42,
    requestId: 'SR-2026-0042',
    serviceTitle: 'AC Coil Repair',
    status: 'COMPLETED',
    customerName: 'Ananya Roy',
    phone: '+91 98765 00000',
    address: '12 Brigade Road, Bangalore',
    latitude: 12.9716,
    longitude: 77.5946,
    totalAmount: 1800.0,
    isOffer: false,
    isAcceptedByCurrentEmployee: true,
    isAssignedToCurrentEmployee: true,
    canCancel: false,
  );

  List<Override> buildOverrides({bool isOnline = true, bool isClockedIn = false}) {
    final profile = testProfile.copyWith(isOnline: isOnline);
    return [
      locationServiceProvider.overrideWithValue(_FakeLocationService()),
      authControllerProvider.overrideWith((ref) => _FakeAuthController(testUser)),
      employeeProfileProvider.overrideWith((ref) => Future.value(profile)),
      shiftStatusProvider.overrideWith((ref) => Future.value(ShiftStatus(
            isClockedIn: isClockedIn,
            shiftStatus: isClockedIn ? 'clocked_in' : 'standby',
            hasActiveJob: false,
          ))),
      activeJobsProvider.overrideWith((ref) => Future.value(<Job>[])),
      completedJobsProvider.overrideWith((ref) => Future.value(<Job>[sampleCompletedJob])),
    ];
  }

  group('Dashboard / HomeScreen Widget Tests', () {
    testWidgets('renders all 7 required Dashboard sections', (tester) async {
      tester.view.physicalSize = const Size(1080, 4200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(isOnline: true, isClockedIn: false),
          child: const MaterialApp(
            home: HomeScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. Employee Greeting / Header with WorkforceAvatar
      expect(find.byType(GreetingHeader), findsOneWidget);
      expect(find.byType(WorkforceAvatar), findsAtLeastNWidgets(1));
      expect(find.text('Karthik Raman'), findsOneWidget);
      expect(find.text('Apex Air Conditioning Services'), findsOneWidget);

      // 2. Technician Online/Offline status card & toggle
      expect(find.byType(DashboardStatusCard), findsOneWidget);
      expect(find.text('ONLINE • READY FOR DISPATCH'), findsOneWidget);
      expect(find.text('Online — Available for Jobs'), findsOneWidget);

      // 3. Mobile-friendly Map & Radar section
      expect(find.byType(DashboardLiveMap), findsOneWidget);
      expect(find.text('GPS RADAR ACTIVE'), findsOneWidget);
      expect(find.text('Locate Me'), findsOneWidget);

      // 4. Shift Standby Card
      expect(find.text('Shift Standby'), findsOneWidget);
      expect(find.text('Starts automatically upon Customer OTP verification'), findsOneWidget);

      // 5. Current Availability Card
      expect(find.text('Availability State'), findsOneWidget);
      expect(find.text('AVAILABLE'), findsAtLeastNWidgets(1));

      // 6. GPS Accuracy + Completed Today Stats
      expect(find.text('GPS ACCURACY'), findsOneWidget);
      expect(find.text('COMPLETED TODAY'), findsOneWidget);
      expect(find.text('1 Job'), findsOneWidget);

      // 7. Authorized Service Capabilities Card
      expect(find.byType(AuthorizedServicesCard), findsOneWidget);
      expect(find.text('Authorized Service Capabilities'), findsOneWidget);
      expect(find.text('2 Approved'), findsOneWidget);
      expect(find.text('AC Deep Cleaning & Sanitization'), findsOneWidget);
      expect(find.text('Copper Pipe Replacement'), findsOneWidget);
      expect(find.text('Manage Services & Skills'), findsOneWidget);
    });

    testWidgets('renders Offline status when technician is offline', (tester) async {
      tester.view.physicalSize = const Size(1080, 4200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      await tester.pumpWidget(
        ProviderScope(
          overrides: buildOverrides(isOnline: false, isClockedIn: false),
          child: const MaterialApp(
            home: HomeScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('OFFLINE'), findsAtLeastNWidgets(1));
      expect(find.text('Offline — Currently Unavailable'), findsOneWidget);
      expect(find.text('LOCATION PAUSED'), findsOneWidget);
    });
  });
}

class _FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  _FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeLocationService implements LocationService {
  @override
  Future<LocationResult> getCurrentPosition() async {
    return LocationResult(
      latitude: 12.9716,
      longitude: 77.5946,
      accuracy: 12.0,
      timestamp: DateTime.now(),
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

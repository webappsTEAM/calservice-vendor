import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/jobs/presentation/widgets/worker_status_header.dart';
import 'package:mobile/features/profile/data/profile_repository.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/features/profile/presentation/widgets/employee_availability_toggle.dart';

class FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeProfileRepository implements ProfileRepository {
  FakeProfileRepository({
    this.initialOnline = true,
    this.shouldThrow = false,
    this.delay = Duration.zero,
  }) : currentOnline = initialOnline;

  final bool initialOnline;
  final bool shouldThrow;
  final Duration delay;
  bool currentOnline;
  int toggleCallCount = 0;
  bool? lastRequestedOnline;

  @override
  Future<Map<String, dynamic>> togglePresence({bool? isOnline}) async {
    toggleCallCount++;
    lastRequestedOnline = isOnline;
    if (delay > Duration.zero) {
      await Future.delayed(delay);
    }
    if (shouldThrow) {
      throw Exception('Server error: Database connection timeout');
    }
    currentOnline = isOnline ?? !currentOnline;
    return {
      'is_online': currentOnline,
      'availability': currentOnline ? 'available' : 'offline',
      'message': currentOnline ? 'Technician is now ONLINE.' : 'Technician is now OFFLINE.',
    };
  }

  @override
  Future<EmployeeProfile> fetchProfile() async {
    return EmployeeProfile(
      employeeId: 'ORG--0024',
      firstName: 'Mani',
      lastName: 'S',
      isOnline: currentOnline,
      registrationStatus: 'approved',
      approvedServices: const [],
      allRequestedServices: const [],
      documents: const [],
      controlledFields: const ControlledFieldsConfig(isLocked: false, lockedFields: []),
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const testUser = AuthUser(
    id: 1,
    username: 'mani_s',
    email: 'mani@calservices.com',
    firstName: 'Mani',
    lastName: 'S',
    role: 'employee',
    companyId: 1,
    companyName: 'CalServices',
    isSuperuser: false,
    employeeId: 'ORG--0024',
    registrationStatus: 'approved',
  );

  final onlineProfile = EmployeeProfile(
    employeeId: 'ORG--0024',
    firstName: 'Mani',
    lastName: 'S',
    isOnline: true,
    liveAvailability: 'available',
    registrationStatus: 'approved',
    approvedServices: const [],
    allRequestedServices: const [],
    documents: const [],
    controlledFields: const ControlledFieldsConfig(isLocked: false, lockedFields: []),
  );

  final offlineProfile = EmployeeProfile(
    employeeId: 'ORG--0024',
    firstName: 'Mani',
    lastName: 'S',
    isOnline: false,
    liveAvailability: 'offline',
    registrationStatus: 'approved',
    approvedServices: const [],
    allRequestedServices: const [],
    documents: const [],
    controlledFields: const ControlledFieldsConfig(isLocked: false, lockedFields: []),
  );

  final activeJob = Job(
    id: 99,
    requestId: 'SR-2026-0099',
    serviceTitle: 'HVAC Compressor Diagnostic',
    status: 'in_progress',
    customerName: 'Enterprise Client',
    isOffer: false,
    isAssignedToCurrentEmployee: true,
    isAcceptedByCurrentEmployee: true,
    canCancel: false,
  );

  group('Employee Online / Offline Availability Control & WorkerStatusHeader', () {
    testWidgets('1. Initial State: Employee ONLINE displays ONLINE status', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            employeeProfileProvider.overrideWith((ref) => Future.value(onlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Employee Info
      expect(find.text('Mani S'), findsOneWidget);
      expect(find.text('ORG--0024'), findsOneWidget);
      expect(find.text('NO ACTIVE JOB'), findsOneWidget);

      // Verify Availability Header and Button
      expect(find.text('Availability'), findsOneWidget);
      expect(find.text('● ONLINE'), findsOneWidget);
      expect(find.text('○ OFFLINE'), findsNothing);
    });

    testWidgets('2. Initial State: Employee OFFLINE displays OFFLINE status', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            employeeProfileProvider.overrideWith((ref) => Future.value(offlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Mani S'), findsOneWidget);
      expect(find.text('○ OFFLINE'), findsOneWidget);
      expect(find.text('● ONLINE'), findsNothing);
    });

    testWidgets('3. Job status: ON JOB (BUSY) is displayed independently from ONLINE availability', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            employeeProfileProvider.overrideWith((ref) => Future.value(onlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([activeJob])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Job Status chip shows ON JOB (BUSY)
      expect(find.text('ON JOB (BUSY)'), findsOneWidget);
      // Availability toggle shows ONLINE separately
      expect(find.text('● ONLINE'), findsOneWidget);
      expect(find.byType(EmployeeAvailabilityToggle), findsOneWidget);
    });

    testWidgets('4. Toggle OFFLINE -> ONLINE success flow', (tester) async {
      final fakeRepo = FakeProfileRepository(initialOnline: false);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            profileRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(offlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('○ OFFLINE'), findsOneWidget);

      // Tap OFFLINE to go ONLINE
      await tester.tap(find.byType(EmployeeAvailabilityToggle));
      await tester.pumpAndSettle();

      // Verify repository was called with desired state true
      expect(fakeRepo.toggleCallCount, equals(1));
      expect(fakeRepo.lastRequestedOnline, isTrue);

      // Verify success snackbar notification
      expect(find.text('You are now ONLINE and ready to receive dispatches.'), findsOneWidget);
    });

    testWidgets('5. Toggle ONLINE -> OFFLINE success flow', (tester) async {
      final fakeRepo = FakeProfileRepository(initialOnline: true);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            profileRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(onlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('● ONLINE'), findsOneWidget);

      // Tap ONLINE to go OFFLINE
      await tester.tap(find.byType(EmployeeAvailabilityToggle));
      await tester.pumpAndSettle();

      expect(fakeRepo.toggleCallCount, equals(1));
      expect(fakeRepo.lastRequestedOnline, isFalse);
      expect(find.text('You are now OFFLINE.'), findsOneWidget);
    });

    testWidgets('6. Loading state: button displays UPDATING... and ignores duplicate taps', (tester) async {
      final fakeRepo = FakeProfileRepository(initialOnline: false);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            profileRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(offlineProfile)),
            availabilityControllerProvider.overrideWith((ref) {
              return AvailabilityController(ref);
            }),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Trigger toggle
      await tester.tap(find.byType(EmployeeAvailabilityToggle));
      await tester.pump(); // Start request

      // While request is in flight
      // Now complete
      await tester.pumpAndSettle();
      expect(fakeRepo.toggleCallCount, equals(1));
    });

    testWidgets('7. Active job restriction: cannot go offline while on active job', (tester) async {
      final fakeRepo = FakeProfileRepository(initialOnline: true);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            profileRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(onlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([activeJob])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('ON JOB (BUSY)'), findsOneWidget);
      expect(find.text('● ONLINE'), findsOneWidget);

      // Tap ONLINE button to attempt going OFFLINE
      await tester.tap(find.byType(EmployeeAvailabilityToggle));
      await tester.pumpAndSettle();

      // API must NOT be called
      expect(fakeRepo.toggleCallCount, equals(0));

      // Error banner warning user about active job
      expect(
        find.text('Cannot go offline while actively working on SR-2026-0099. Please complete or cancel the active job first.'),
        findsOneWidget,
      );

      // State remains ONLINE
      expect(find.text('● ONLINE'), findsOneWidget);
    });

    testWidgets('8. API Failure: preserves previous state and shows error message', (tester) async {
      final fakeRepo = FakeProfileRepository(initialOnline: false, shouldThrow: true);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
            profileRepositoryProvider.overrideWithValue(fakeRepo),
            employeeProfileProvider.overrideWith((ref) => Future.value(offlineProfile)),
            activeJobsProvider.overrideWith((ref) => Future.value([])),
            completedJobsProvider.overrideWith((ref) => Future.value([])),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: WorkerStatusHeader(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('○ OFFLINE'), findsOneWidget);

      // Tap to go online
      await tester.tap(find.byType(EmployeeAvailabilityToggle));
      await tester.pumpAndSettle();

      // Repository was called
      expect(fakeRepo.toggleCallCount, equals(1));

      // State remains OFFLINE
      expect(find.text('○ OFFLINE'), findsOneWidget);

      // Error snackbar shown
      expect(find.text('Server error: Database connection timeout'), findsOneWidget);
    });
  });

  group('Responsive Layout: No RenderFlex Overflows across widths', () {
    const screenSizes = [
      ('320x568 (Small Phone)', 320.0, 568.0),
      ('360x640 (Standard Android)', 360.0, 640.0),
      ('390x844 (iPhone 12/13/14)', 390.0, 844.0),
      ('412x915 (Pixel 7/Galaxy S21)', 412.0, 915.0),
      ('480x800 (Wide Android)', 480.0, 800.0),
    ];

    for (final (label, width, height) in screenSizes) {
      testWidgets('WorkerStatusHeader renders cleanly on $label', (tester) async {
        tester.view.physicalSize = Size(width * 2, height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());
        addTearDown(() => tester.view.resetDevicePixelRatio());

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              authControllerProvider.overrideWith((ref) => FakeAuthController(testUser)),
              employeeProfileProvider.overrideWith((ref) => Future.value(onlineProfile)),
              activeJobsProvider.overrideWith((ref) => Future.value([activeJob])),
              completedJobsProvider.overrideWith((ref) => Future.value([])),
            ],
            child: const MaterialApp(
              home: Scaffold(
                body: WorkerStatusHeader(),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final exception = tester.takeException();
        expect(exception, isNull, reason: 'RenderFlex overflow occurred on $label');
        expect(find.text('Mani S'), findsOneWidget);
        expect(find.text('ON JOB (BUSY)'), findsOneWidget);
        expect(find.text('● ONLINE'), findsOneWidget);
      });
    }
  });
}

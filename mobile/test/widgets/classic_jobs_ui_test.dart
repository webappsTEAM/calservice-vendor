import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';
import 'package:mobile/features/jobs/presentation/jobs_screen.dart';
import 'package:mobile/features/jobs/presentation/widgets/job_card.dart';
import 'package:mobile/features/jobs/presentation/widgets/job_category_filter_bar.dart';
import 'package:mobile/features/jobs/presentation/widgets/job_customer_row.dart';
import 'package:mobile/features/jobs/presentation/widgets/job_status_badge.dart';
import 'package:mobile/features/jobs/presentation/widgets/job_status_filter_bar.dart';
import 'package:mobile/features/jobs/presentation/widgets/new_offer_banner.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';

class FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

const mockUser = AuthUser(
  id: 1,
  username: 'tech_dharani',
  email: 'dharani@calservices.example.com',
  firstName: 'Dharani',
  lastName: 'Tech',
  role: 'employee',
  companyId: 1,
  companyName: 'CalServices',
  isSuperuser: false,
  employeeId: 'TECH-0042',
  registrationStatus: 'approved',
);

const mockProfile = EmployeeProfile(
  employeeId: 'TECH-0042',
  firstName: 'Dharani',
  lastName: 'Tech',
  phone: '+91 9876543210',
  isOnline: true,
  registrationStatus: 'approved',
  approvedServices: [],
  allRequestedServices: [],
  documents: [],
  controlledFields: ControlledFieldsConfig(isLocked: false, lockedFields: []),
);

final mockOfferJob = Job(
  id: 101,
  requestId: '#MS4942',
  serviceCategory: 'Locks & Carpentry',
  serviceTitle: 'Block Wall Construction (Site Consultation)',
  status: 'offered',
  totalAmount: 98.0,
  customerName: 'Dharani',
  phone: '+91 9876543210',
  address: '05 Bagalur Rd, KCC Nagar, Nallur',
  preferredDate: '02 Sep 2026',
  preferredTime: '10:00 AM',
  isOffer: true,
  isAcceptedByCurrentEmployee: false,
  isAssignedToCurrentEmployee: false,
  canCancel: false,
  activeOffer: JobOffer(
    status: 'OFFERED',
    isExpired: false,
    offeredAt: DateTime(2026, 9, 2, 10, 0),
    expiresAt: DateTime(2026, 9, 2, 10, 15),
  ),
  cartData: const [
    JobCartItem(name: 'Block Wall Construction', quantity: 1),
    JobCartItem(name: 'Site Inspection Extra', quantity: 1),
  ],
);

final mockInProgressJob = Job(
  id: 102,
  requestId: '#MS4943',
  serviceCategory: 'Electrical',
  serviceTitle: 'Main Switchboard Repair & Fuse Upgrade',
  status: 'in_progress',
  totalAmount: 2672.95,
  customerName: 'Rajesh Kumar',
  phone: '+91 9123456780',
  address: '12 Electronic City Phase 1, Bangalore',
  preferredDate: '03 Sep 2026',
  preferredTime: '02:30 PM',
  isOffer: false,
  isAcceptedByCurrentEmployee: true,
  isAssignedToCurrentEmployee: true,
  canCancel: false,
);

final mockCompletedJob = Job(
  id: 103,
  requestId: '#MS4944',
  serviceCategory: 'Plumbing',
  serviceTitle: 'Water Heater Pipe Leak Repair',
  status: 'completed',
  totalAmount: 1450.0,
  customerName: 'Ananya Sharma',
  phone: '+91 9988776655',
  address: '44 Indiranagar 100ft Road, Bangalore',
  preferredDate: '01 Sep 2026',
  preferredTime: '11:00 AM',
  isOffer: false,
  isAcceptedByCurrentEmployee: true,
  isAssignedToCurrentEmployee: true,
  canCancel: false,
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget buildJobsScreenTestWidget({
    List<Job>? activeJobs,
    List<Job>? completedJobs,
  }) {
    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith((ref) => FakeAuthController(mockUser)),
        employeeProfileProvider.overrideWith((ref) => Future.value(mockProfile)),
        activeJobsProvider.overrideWith(
          (ref) => Future.value(activeJobs ?? [mockOfferJob, mockInProgressJob]),
        ),
        completedJobsProvider.overrideWith(
          (ref) => Future.value(completedJobs ?? [mockCompletedJob]),
        ),
      ],
      child: MaterialApp(
        theme: ThemeData.light(useMaterial3: true),
        home: const JobsScreen(),
      ),
    );
  }

  group('Classic Premium Jobs UI - Component Tests', () {
    testWidgets('JobStatusBadge renders correct label and palette for each status', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                JobStatusBadge(status: 'offered', label: 'AVAILABLE'),
                JobStatusBadge(status: 'in_progress', label: 'IN PROGRESS'),
                JobStatusBadge(status: 'completed', label: 'COMPLETED'),
                JobStatusBadge(status: 'cancelled', label: 'CANCELLED'),
              ],
            ),
          ),
        ),
      );

      expect(find.text('AVAILABLE'), findsOneWidget);
      expect(find.text('IN PROGRESS'), findsOneWidget);
      expect(find.text('COMPLETED'), findsOneWidget);
      expect(find.text('CANCELLED'), findsOneWidget);
    });

    testWidgets('NewOfferBanner renders count and triggers callback when tapped', (tester) async {
      bool tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: NewOfferBanner(
              offerCount: 1,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      expect(find.text('1 New Service Offer Available'), findsOneWidget);
      await tester.tap(find.byType(NewOfferBanner));
      expect(tapped, isTrue);
    });

    testWidgets('JobCustomerRow renders avatar, name, and action buttons', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: JobCustomerRow(job: mockOfferJob),
          ),
        ),
      );

      expect(find.text('Dharani'), findsOneWidget);
      expect(find.byIcon(Icons.phone_rounded), findsOneWidget);
      expect(find.byIcon(Icons.directions_rounded), findsOneWidget);
    });

    testWidgets('JobCard renders complete visual hierarchy for an offer', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: JobCard(job: mockOfferJob),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Locks & Carpentry'), findsOneWidget);
      expect(find.text('#MS4942'), findsOneWidget);
      expect(find.text('₹98'), findsOneWidget);
      expect(find.text('Earn on finish'), findsOneWidget);
      expect(find.textContaining('Block Wall Construction (Site Consultation)'), findsOneWidget);
      expect(find.textContaining('(+1 other item)'), findsOneWidget);
      expect(find.textContaining('02 Sep 2026 • 10:00 AM'), findsOneWidget);
      expect(find.textContaining('05 Bagalur Rd, KCC Nagar, Nallur'), findsOneWidget);
      expect(find.text('Dharani'), findsOneWidget);
      expect(find.text('Decline'), findsOneWidget);
      expect(find.text('Accept • ₹98'), findsOneWidget);
    });

    testWidgets('JobCard renders complete visual hierarchy for in-progress job', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: JobCard(job: mockInProgressJob),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Electrical'), findsOneWidget);
      expect(find.text('#MS4943'), findsOneWidget);
      expect(find.text('₹2672.95'), findsOneWidget);
      expect(find.text('Earn on finish'), findsOneWidget);
      expect(find.textContaining('Main Switchboard Repair & Fuse Upgrade'), findsOneWidget);
      expect(find.text('Rajesh Kumar'), findsOneWidget);
      expect(find.text('View Details'), findsOneWidget);
      expect(find.text('Continue Job'), findsOneWidget);
    });

    testWidgets('JobCard renders complete visual hierarchy for completed job', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: JobCard(job: mockCompletedJob),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Plumbing'), findsOneWidget);
      expect(find.text('#MS4944'), findsOneWidget);
      expect(find.text('₹1450.00'), findsOneWidget);
      expect(find.text('Completed'), findsWidgets);
      expect(find.text('View Details'), findsOneWidget);
    });
  });

  group('JobsScreen Integration & Filter Tests', () {
    testWidgets('JobsScreen renders AppBar title, counts, offer banner, and job cards', (tester) async {
      await tester.pumpWidget(buildJobsScreenTestWidget());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('My Orders & Jobs'), findsOneWidget);
      expect(find.textContaining('3 Jobs Available & Assigned'), findsOneWidget);
      expect(find.text('1 New Service Offer Available'), findsOneWidget);
      expect(find.byType(JobStatusFilterBar), findsOneWidget);
      expect(find.byType(JobCategoryFilterBar), findsOneWidget);
      expect(find.byType(JobCard), findsWidgets);
    });

    testWidgets('JobsScreen switches status filters and updates rendered cards', (tester) async {
      await tester.pumpWidget(buildJobsScreenTestWidget());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      // Filter: Completed
      await tester.tap(find.textContaining('Completed (1)'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('#MS4944'), findsOneWidget);
      expect(find.text('#MS4942'), findsNothing);
      expect(find.text('#MS4943'), findsNothing);

      // Filter: In Progress
      await tester.tap(find.textContaining('In Progress (1)'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('#MS4943'), findsOneWidget);
      expect(find.text('#MS4944'), findsNothing);
      expect(find.text('#MS4942'), findsNothing);

      // Filter: New Offers
      await tester.tap(find.textContaining('New Offers (1)'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('#MS4942'), findsOneWidget);
      expect(find.text('#MS4943'), findsNothing);
    });

    testWidgets('JobsScreen category filter chips filter job list', (tester) async {
      await tester.pumpWidget(buildJobsScreenTestWidget());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      // Tap Electrical category chip inside JobCategoryFilterBar
      final electricalChip = find.descendant(
        of: find.byType(JobCategoryFilterBar),
        matching: find.text('Electrical'),
      );
      await tester.tap(electricalChip);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('#MS4943'), findsOneWidget);
      expect(find.text('#MS4942'), findsNothing);
      expect(find.text('#MS4944'), findsNothing);
    });

    testWidgets('JobsScreen search toggles and filters by search query', (tester) async {
      await tester.pumpWidget(buildJobsScreenTestWidget());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      // Tap search icon
      await tester.tap(find.byTooltip('Search Jobs'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.byType(TextField), findsOneWidget);

      // Enter search query
      await tester.enterText(find.byType(TextField), 'Rajesh');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('#MS4943'), findsOneWidget);
      expect(find.text('#MS4942'), findsNothing);
      expect(find.text('#MS4944'), findsNothing);
    });
  });

  group('JobsScreen Responsive Layout Tests', () {
    for (final size in [
      const Size(320, 600), // Narrow 320px Android / iPhone SE
      const Size(360, 800), // Standard Android
      const Size(412, 915), // Large Android Phone
    ]) {
      testWidgets('JobsScreen renders without layout overflow at width ${size.width}', (tester) async {
        tester.view.physicalSize = Size(size.width * 2, size.height * 2);
        tester.view.devicePixelRatio = 2.0;
        addTearDown(() => tester.view.resetPhysicalSize());
        addTearDown(() => tester.view.resetDevicePixelRatio());

        await tester.pumpWidget(buildJobsScreenTestWidget());
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 200));

        final exc = tester.takeException();
        expect(exc, isNull);
        expect(find.byType(JobCard), findsWidgets);
      });
    }
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/superadmin/workforce/data/superadmin_workforce_repository.dart';
import 'package:mobile/features/superadmin/workforce/domain/platform_relieving_request.dart';
import 'package:mobile/features/superadmin/workforce/domain/platform_worker.dart';
import 'package:mobile/features/superadmin/workforce/presentation/superadmin_workforce_providers.dart';
import 'package:mobile/features/superadmin/workforce/presentation/superadmin_workforce_roster_screen.dart';
import 'package:mobile/features/superadmin/workforce/presentation/widgets/approve_relieving_bottom_sheet.dart';
import 'package:mobile/features/superadmin/workforce/presentation/widgets/relieving_audit_card.dart';
import 'package:mobile/features/superadmin/workforce/presentation/widgets/tie_vendor_bottom_sheet.dart';
import 'package:mobile/features/superadmin/workforce/presentation/widgets/worker_card.dart';
import 'package:mobile/features/superadmin/workforce/presentation/widgets/workforce_summary_metrics.dart';

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

  final mockWorkers = [
    const PlatformWorker(
      id: 101,
      employeeId: 'EMP-1001',
      name: 'Ramesh Kumar',
      email: 'ramesh@example.com',
      phone: '9876543210',
      city: 'Hosur, Tamil Nadu',
      skills: ['AC Repair', 'Electrical', 'HVAC'],
      isOnline: true,
      currentAvailability: 'AVAILABLE',
      workforceType: 'SOLO',
      registrationStatus: 'approved',
      hourlyRate: 350.0,
    ),
    const PlatformWorker(
      id: 102,
      employeeId: 'EMP-1002',
      name: 'Suresh Raina',
      email: 'suresh@example.com',
      phone: '9876543211',
      city: 'Bangalore, Karnataka',
      skills: ['Plumbing', 'Pipe Fitting'],
      isOnline: false,
      currentAvailability: 'OFFLINE',
      workforceType: 'TIED',
      tiedVendor: PlatformTiedVendorInfo(
        id: 12,
        companyName: 'Apex Engineering Ltd',
        startedAt: '2026-01-15T00:00:00Z',
        relationshipId: 4,
      ),
      registrationStatus: 'approved',
      hourlyRate: 400.0,
    ),
    const PlatformWorker(
      id: 103,
      employeeId: 'EMP-1003',
      name: 'Dinesh Karthik',
      email: 'dinesh@example.com',
      phone: '9876543212',
      city: 'Chennai, Tamil Nadu',
      skills: ['Carpentry'],
      isOnline: true,
      currentAvailability: 'AVAILABLE',
      workforceType: 'SOLO',
      registrationStatus: 'pending',
      hourlyRate: 300.0,
    ),
  ];

  final mockRelievingRequests = [
    const PlatformRelievingRequest(
      id: 1,
      relationshipId: 4,
      technicianId: 101,
      technicianName: 'Ramesh Kumar',
      technicianEmail: 'ramesh@example.com',
      technicianPhone: '9876543210',
      vendorId: 12,
      vendorName: 'Apex Engineering Ltd',
      status: 'VENDOR_APPROVED',
      reasonCategory: 'TRANSITION_TO_SOLO',
      reasonDisplay: 'Transitioning to Solo Independent Worker',
      resignationNotes: 'Transitioning to independent solo work on SEVO Platform.',
      desiredRelievingDate: '2026-09-30',
      vendorSettlementNotes: 'All toolkits returned and customer dues settled.',
      vendorApprovedAt: '2026-09-01T10:00:00Z',
      workerSignoffAck: true,
      vendorSignoffAck: true,
    ),
    const PlatformRelievingRequest(
      id: 2,
      relationshipId: 5,
      technicianId: 104,
      technicianName: 'Manikandan Sundaram',
      technicianEmail: 'mani@example.com',
      technicianPhone: '9876543215',
      vendorId: 15,
      vendorName: 'Pioneer Works',
      status: 'COMPLETED',
      reasonCategory: 'RELOCATION',
      reasonDisplay: 'Relocation to another state',
      desiredRelievingDate: '2026-08-15',
      vendorSettlementNotes: 'Clearance verified.',
      workerSignoffAck: true,
      vendorSignoffAck: true,
    ),
  ];

  final mockVendors = [
    const PlatformVendorSummary(
      id: 12,
      companyName: 'Apex Engineering Ltd',
      city: 'Bangalore',
      tiedWorkersCount: 1,
    ),
    const PlatformVendorSummary(
      id: 15,
      companyName: 'Pioneer Works',
      city: 'Chennai',
      tiedWorkersCount: 4,
    ),
  ];

  final mockOverviewData = PlatformWorkforceOverviewData(
    workers: mockWorkers,
    counts: const PlatformWorkforceCounts(all: 3, solo: 2, tied: 1),
    relievingRequests: mockRelievingRequests,
    pendingSevoAuditCount: 1,
    vendors: mockVendors,
  );

  Widget createTestWidget({
    PlatformWorkforceOverviewData? overviewData,
    AsyncValue<PlatformWorkforceOverviewData>? customAsync,
  }) {
    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(
          (ref) => FakeAuthController(mockSuperAdminUser),
        ),
        if (customAsync != null)
          platformWorkforceDataProvider.overrideWith((ref) => customAsync.value!)
        else
          platformWorkforceDataProvider.overrideWith(
            (ref) async => overviewData ?? mockOverviewData,
          ),
      ],
      child: const MaterialApp(
        home: SuperAdminWorkforceRosterScreen(),
      ),
    );
  }

  group('SuperAdminWorkforceRosterScreen Widget Tests', () {
    testWidgets('renders header, title, and live metrics correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Platform Governance context tag
      expect(find.text('PLATFORM GOVERNANCE'), findsOneWidget);

      // Title & Subtitle
      expect(find.text('Workforce Oversight (Solo & Tied Workers)'), findsOneWidget);
      expect(
        find.text(
          'SEVO Platform Admin: Manage all technicians, directly tie solo workers to any vendor, audit resignations, and relieve workers.',
        ),
        findsOneWidget,
      );

      // Manage Vendor Companies button
      expect(find.text('Manage Vendor Companies'), findsOneWidget);

      // Summary Metric Cards
      expect(find.text('TOTAL TECHNICIANS'), findsOneWidget);
      expect(find.text('3'), findsNWidgets(2)); // Total Technicians count & tab badge
      expect(find.text('SOLO WORKERS'), findsOneWidget);
      expect(find.text('2'), findsNWidgets(2)); // Solo count & tab badge
      expect(find.text('TIED WORKERS'), findsOneWidget);
      expect(find.text('1'), findsNWidgets(4)); // Tied count, pending audit count, and badges
      expect(find.text('RELIEVING AUDITS'), findsOneWidget);
      expect(find.text('AUDIT'), findsOneWidget);
    });

    testWidgets('renders filter tabs with live count badges', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('All Workforce'), findsOneWidget);
      expect(find.text('Solo Workers'), findsOneWidget);
      expect(find.text('Tied Workers'), findsOneWidget);
      expect(find.text('Resignation Audits'), findsOneWidget);
    });

    testWidgets('renders worker cards with complete information and badges', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Worker 1 (SOLO)
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('EMP-1001'), findsOneWidget);
      expect(find.text('9876543210'), findsOneWidget);
      expect(find.text('AC Repair'), findsOneWidget);
      expect(find.text('Tie to Vendor'), findsNWidgets(2)); // Ramesh & Dinesh are solo

      // Worker 2 (TIED)
      expect(find.text('Suresh Raina'), findsOneWidget);
      expect(find.text('EMP-1002'), findsOneWidget);
      expect(find.text('Apex Engineering Ltd'), findsOneWidget);
      expect(find.text('Plumbing'), findsOneWidget);
      expect(find.text('Reassign / Untie'), findsOneWidget);

      // Worker 3 (SOLO, pending)
      expect(find.text('Dinesh Karthik'), findsOneWidget);
      expect(find.text('PENDING'), findsOneWidget);
    });

    testWidgets('switching to Resignation Audits tab displays audit requests', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Tap on Relieving Audits metric box
      final auditsCard = find.text('RELIEVING AUDITS');
      expect(auditsCard, findsOneWidget);
      await tester.tap(auditsCard);
      await tester.pumpAndSettle();

      // Verify audit cards are shown
      expect(find.byType(RelievingAuditCard), findsWidgets);
      expect(find.text('Audit & Clear'), findsOneWidget);
      expect(find.text('Transitioning to Solo Independent Worker'), findsOneWidget);
    });

    testWidgets('tapping Tie to Vendor opens TieVendorBottomSheet modal', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Tap on first "Tie to Vendor" button
      final tieButton = find.text('Tie to Vendor').first;
      await tester.tap(tieButton);
      await tester.pumpAndSettle();

      // Verify modal sheet is open
      expect(find.byType(TieVendorBottomSheet), findsOneWidget);
      expect(find.text('Tie Solo Worker to Vendor'), findsOneWidget);
      expect(find.text('Target Vendor Company *'), findsOneWidget);
      expect(find.text('Engagement Model'), findsOneWidget);
    });

    testWidgets('tapping Audit & Clear opens ApproveRelievingBottomSheet modal', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Switch to Resignation Audits via summary metric box
      await tester.tap(find.text('RELIEVING AUDITS'));
      await tester.pumpAndSettle();

      // Tap Audit & Clear
      final auditBtn = find.text('Audit & Clear');
      expect(auditBtn, findsOneWidget);
      await tester.tap(auditBtn);
      await tester.pumpAndSettle();

      // Verify modal is open
      expect(find.byType(ApproveRelievingBottomSheet), findsOneWidget);
      expect(find.text('SEVO Platform Relieving Audit'), findsOneWidget);
      expect(find.text('Approve SEVO Audit & Relieve'), findsOneWidget);
      expect(find.text('Platform Audit & Settlement Notes *'), findsOneWidget);
    });

    testWidgets('renders empty state when no workers match criteria', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final emptyData = PlatformWorkforceOverviewData(
        workers: const [],
        counts: const PlatformWorkforceCounts(all: 0, solo: 0, tied: 0),
        relievingRequests: const [],
        pendingSevoAuditCount: 0,
        vendors: mockVendors,
      );

      await tester.pumpWidget(createTestWidget(overviewData: emptyData));
      await tester.pumpAndSettle();

      expect(find.text('No technicians found'), findsOneWidget);
      expect(
        find.text('No workers match your selected filter or search criteria.'),
        findsOneWidget,
      );
    });

    testWidgets('renders empty state when no resignation audits exist', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final emptyData = PlatformWorkforceOverviewData(
        workers: mockWorkers,
        counts: const PlatformWorkforceCounts(all: 3, solo: 2, tied: 1),
        relievingRequests: const [],
        pendingSevoAuditCount: 0,
        vendors: mockVendors,
      );

      await tester.pumpWidget(createTestWidget(overviewData: emptyData));
      await tester.pumpAndSettle();

      // Switch to Resignation Audits
      await tester.tap(find.text('RELIEVING AUDITS'));
      await tester.pumpAndSettle();

      expect(find.text('No Pending Relieving Audits'), findsOneWidget);
    });

    testWidgets('search input field updates query and clears correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final searchField = find.byType(TextField);
      expect(searchField, findsOneWidget);

      await tester.enterText(searchField, 'Ramesh');
      await tester.pumpAndSettle();

      expect(find.text('Ramesh'), findsOneWidget); // in search field
      expect(find.text('Ramesh Kumar'), findsOneWidget); // in worker card
      expect(find.byIcon(Icons.clear_rounded), findsOneWidget);

      await tester.tap(find.byIcon(Icons.clear_rounded));
      await tester.pumpAndSettle();

      expect(find.text('Ramesh Kumar'), findsOneWidget);
    });

    testWidgets('renders error state with retry button on failure', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => FakeAuthController(mockSuperAdminUser),
            ),
            platformWorkforceDataProvider.overrideWith(
              (ref) => Future.error(Exception('Network timeout')),
            ),
          ],
          child: const MaterialApp(
            home: SuperAdminWorkforceRosterScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load platform workforce roster'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('initialVendorId: null initializes with All Workforce and no vendor filter',
        (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => FakeAuthController(mockSuperAdminUser),
            ),
            platformWorkforceDataProvider.overrideWith(
              (ref) async => mockOverviewData,
            ),
          ],
          child: const MaterialApp(
            home: SuperAdminWorkforceRosterScreen(initialVendorId: null),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // All Workforce is rendered
      expect(find.text('All Workforce'), findsOneWidget);

      // All 3 workers (both Solo and Tied) are rendered
      expect(find.text('Ramesh Kumar'), findsOneWidget); // Solo
      expect(find.text('Suresh Raina'), findsOneWidget); // Tied
      expect(find.text('Dinesh Karthik'), findsOneWidget); // Solo

      // Dropdown selected item shows 'All Vendors'
      expect(find.text('All Vendors'), findsOneWidget);
    });

    testWidgets('initialVendorId: 12 pre-selects vendor in dropdown and displays tied worker',
        (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => FakeAuthController(mockSuperAdminUser),
            ),
            platformWorkforceDataProvider.overrideWith(
              (ref) async => mockOverviewData,
            ),
          ],
          child: const MaterialApp(
            home: SuperAdminWorkforceRosterScreen(initialVendorId: 12),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Selected vendor item in dropdown is displayed
      expect(find.text('Apex Engineering Ltd (1 tied)'), findsOneWidget);
    });

    testWidgets('responsive layout renders cleanly without overflow at various mobile widths',
        (tester) async {
      final screenWidths = [320.0, 360.0, 390.0, 412.0];

      for (final width in screenWidths) {
        tester.view.physicalSize = Size(width * 3, 1200 * 3);
        tester.view.devicePixelRatio = 3.0;

        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        // Verify key components exist and render without overflow exception
        expect(find.text('Workforce Oversight (Solo & Tied Workers)'), findsOneWidget);
        expect(find.byType(WorkforceSummaryMetrics), findsOneWidget);
        expect(find.byType(WorkerCard), findsWidgets);

        // Reset view for next iteration
        addTearDown(() => tester.view.resetPhysicalSize());
      }
    });
  });
}

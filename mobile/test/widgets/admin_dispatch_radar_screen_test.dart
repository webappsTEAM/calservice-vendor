import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_dashboard_metrics.dart';
import 'package:mobile/features/admin/domain/eligible_technician.dart';
import 'package:mobile/features/admin/domain/fleet_member.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/dispatch/admin_dispatch_screen.dart';
import 'package:mobile/features/jobs/domain/job.dart';

void main() {
  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  final sampleFleet = [
    const FleetMember(
      id: 1,
      name: 'Ramesh Kumar',
      employeeId: 'CALS-0001',
      phone: '9876543210',
      isOnline: true,
      currentAvailability: 'available',
      registrationStatus: 'approved',
      hasLocation: true,
      latitude: 12.9716,
      longitude: 77.5946,
      locationStatus: 'LIVE',
    ),
    const FleetMember(
      id: 2,
      name: 'Suresh Raina',
      employeeId: 'CALS-0002',
      phone: '9876543211',
      isOnline: false,
      currentAvailability: 'off_duty',
      registrationStatus: 'approved',
      hasLocation: false,
    ),
  ];

  final sampleJobs = [
    Job(
      id: 5259,
      requestId: 'PA5259',
      customerName: 'Priya Rajan',
      serviceTitle: 'AC Inspection & Gas Charge',
      status: 'unassigned',
      address: '123 MG Road, Bengaluru',
      latitude: 12.9720,
      longitude: 77.5950,
      totalAmount: 3650.0,
      paymentMethod: 'ONLINE',
      paymentStatus: 'pending',
      preferredDate: '2026-09-09',
      preferredTime: '10:00 AM',
      createdAt: DateTime(2026, 9, 9, 10, 0),
      isOffer: false,
      isAcceptedByCurrentEmployee: false,
      isAssignedToCurrentEmployee: false,
      canCancel: true,
    ),
  ];

  const sampleCandidates = [
    EligibleTechnician(
      id: 1,
      name: 'Ramesh Kumar',
      employeeId: 'CALS-0001',
      phone: '9876543210',
      isOnline: true,
      currentAvailability: 'available',
      registrationStatus: 'approved',
      distanceKm: 2.4,
      distanceBand: '2-5km',
      score: 50.0,
      isDispatchReady: true,
      gpsFreshness: 'LIVE',
      gateAudit: [
        GateAuditItem(gate: '1', name: 'Account Active', passed: true),
        GateAuditItem(gate: '2', name: 'Registration Approved', passed: true),
        GateAuditItem(gate: '3', name: 'Required Documents Approved', passed: true),
        GateAuditItem(gate: '4', name: 'Mandatory Compliance Valid', passed: true),
        GateAuditItem(gate: '5', name: 'Working Schedule Active', passed: true),
        GateAuditItem(gate: '6', name: 'Service / Skill Match', passed: true),
        GateAuditItem(gate: '7', name: 'Online & Available Presence', passed: true),
        GateAuditItem(gate: '8', name: 'Not On Leave', passed: true),
        GateAuditItem(gate: '9', name: 'Single-Job Concurrency Free', passed: true),
      ],
    ),
  ];

  Widget buildTestWidget({
    List<Job>? jobs,
    List<FleetMember>? fleet,
    List<EligibleTechnician>? candidates,
  }) {
    final dashboardData = AdminDashboardData(
      fleet: fleet ?? sampleFleet,
      jobs: jobs ?? sampleJobs,
    );

    return ProviderScope(
      overrides: [
        adminDashboardDataProvider.overrideWith((ref) => Future.value(dashboardData)),
        adminFleetListProvider.overrideWith((ref) => Future.value(fleet ?? sampleFleet)),
        adminPendingExtensionsProvider.overrideWith((ref) => Future.value([])),
        adminPendingServicesProvider.overrideWith((ref) => Future.value([])),
        adminLocationsProvider.overrideWith((ref) => Future.value([])),
        adminEligibleTechniciansProvider(5259).overrideWith(
          (ref) => Future.value(candidates ?? sampleCandidates),
        ),
      ],
      child: const MaterialApp(
        home: AdminDispatchScreen(),
      ),
    );
  }

  group('AdminDispatchRadarScreen Widget Tests', () {
    testWidgets('renders header title, subtitle, refresh fleet data, and live metric cards', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Main header
      expect(find.text('Dynamic Dispatch & Fleet Operations'), findsOneWidget);
      expect(
        find.text('Skill-based technician matching and real-time GPS telemetry radar'),
        findsOneWidget,
      );
      expect(find.text('Refresh Fleet Data'), findsOneWidget);

      // Metrics
      expect(find.text('Total Fleet'), findsOneWidget);
      expect(find.text('Total technicians/workforce tracked by dispatch.'), findsOneWidget);
      expect(find.text('Online & Ready'), findsOneWidget);
      expect(find.text('Available for work'), findsOneWidget);
      expect(find.text('Offline Fleet'), findsOneWidget);
      expect(find.text('Off duty / break'), findsOneWidget);
      expect(find.text('Active Bookings'), findsOneWidget);
      expect(find.text('In queue / assigned'), findsOneWidget);
    });

    testWidgets('renders Customer Service Requests section and request card details', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('1. Customer Service Requests (1)'), findsOneWidget);
      expect(find.text('PA5259'), findsOneWidget);
      expect(find.text('Priya Rajan'), findsOneWidget);
      expect(find.text('AC Inspection & Gas Charge'), findsOneWidget);
      expect(find.text('123 MG Road, Bengaluru'), findsOneWidget);
      expect(find.text('Auto-Dispatch Active'), findsWidgets);
    });

    testWidgets('renders Geo-Dispatch monitor, inspecting job, timeline, re-evaluate, banner, and candidate cards', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Geo-Dispatch monitor header
      expect(find.text('2. Live Automated Geo-Dispatch Engine Monitor'), findsOneWidget);
      expect(find.textContaining('Inspecting Job: PA5259'), findsOneWidget);
      expect(find.text('Timeline'), findsOneWidget);
      expect(find.text('Re-evaluate Auto-Dispatch'), findsOneWidget);

      // Banner
      expect(
        find.textContaining('Autonomous Dispatch Active: Jobs are automatically assigned to nearest eligible technicians using the 9-Gate Employee Eligibility Engine'),
        findsOneWidget,
      );

      // Candidate Card
      expect(find.text('Ramesh Kumar'), findsWidgets);
      expect(find.text('CALS-0001 • 9876543210'), findsOneWidget);
      expect(find.text('GPS: LIVE'), findsOneWidget);
      expect(find.text('Match Score: 50'), findsOneWidget);
      expect(find.text('2.4 km away'), findsOneWidget);
      expect(find.text('✓ Qualified Candidate'), findsOneWidget);

      // 9 Gates
      expect(find.textContaining('Account Active'), findsOneWidget);
      expect(find.textContaining('Registration Approved'), findsOneWidget);
      expect(find.textContaining('Required Documents Approved'), findsOneWidget);
      expect(find.textContaining('Mandatory Compliance Valid'), findsOneWidget);
      expect(find.textContaining('Working Schedule Active'), findsOneWidget);
      expect(find.textContaining('Service / Skill Match'), findsOneWidget);
      expect(find.textContaining('Online & Available Presence'), findsOneWidget);
      expect(find.textContaining('Not On Leave'), findsOneWidget);
      expect(find.textContaining('Single-Job Concurrency Free'), findsOneWidget);
    });
  });

  group('Admin Dispatch Radar Responsive Layout Tests', () {
    for (final width in [320.0, 360.0, 390.0, 412.0]) {
      testWidgets('renders without overflow at ${width}px width', (
        WidgetTester tester,
      ) async {
        tester.view.physicalSize = Size(width, 1000);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(buildTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Dynamic Dispatch & Fleet Operations'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

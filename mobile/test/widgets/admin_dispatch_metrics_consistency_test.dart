import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/core/theme/app_theme.dart';
import 'package:mobile/features/admin/domain/admin_dashboard_metrics.dart';
import 'package:mobile/features/admin/domain/fleet_member.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/dispatch/admin_dispatch_screen.dart';
import 'package:mobile/features/jobs/domain/job.dart';

void main() {
  setUp(() {
    AppColors.configure(brightness: Brightness.light, highContrast: false);
  });

  Widget buildTestWidget(Widget child, {List<dynamic> overrides = const []}) {
    return ProviderScope(
      overrides: overrides.cast(),
      child: MaterialApp(
        home: child,
      ),
    );
  }

  group('Admin Dispatch Metrics & Active Queue Consistency Tests', () {
    testWidgets('Online & Ready counts all isOnline == true and Offline Fleet counts isOnline == false', (tester) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      // 4 fleet members:
      // 2 online (1 available, 1 busy on active job)
      // 2 offline (1 off_duty, 1 unavailable)
      const fleetList = [
        FleetMember(
          id: 1,
          name: 'Online Available Tech',
          isOnline: true,
          currentAvailability: 'available',
          registrationStatus: 'approved',
          hasLocation: true,
        ),
        FleetMember(
          id: 2,
          name: 'Online Busy Tech',
          isOnline: true,
          currentAvailability: 'busy',
          activeJob: 'PA-101',
          registrationStatus: 'approved',
          hasLocation: true,
        ),
        FleetMember(
          id: 3,
          name: 'Offline Tech 1',
          isOnline: false,
          currentAvailability: 'off_duty',
          registrationStatus: 'approved',
          hasLocation: false,
        ),
        FleetMember(
          id: 4,
          name: 'Offline Tech 2',
          isOnline: false,
          currentAvailability: 'offline',
          registrationStatus: 'approved',
          hasLocation: false,
        ),
      ];

      const testDashboardData = AdminDashboardData(
        fleet: fleetList,
        jobs: [],
      );

      await tester.pumpWidget(
        buildTestWidget(
          const AdminDispatchScreen(),
          overrides: [
            adminDashboardDataProvider.overrideWith((ref) => Future.value(testDashboardData)),
            adminFleetListProvider.overrideWith((ref) => Future.value(fleetList)),
            adminPendingExtensionsProvider.overrideWith((ref) => Future.value([])),
            adminPendingServicesProvider.overrideWith((ref) => Future.value([])),
            adminLocationsProvider.overrideWith((ref) => Future.value([])),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Total Fleet = 4
      expect(find.text('Total Fleet'), findsOneWidget);
      expect(find.text('4'), findsOneWidget);

      // Online & Ready = 2 (all technicians where isOnline == true, including busy ones)
      expect(find.text('Online & Ready'), findsOneWidget);
      expect(find.text('2'), findsNWidgets(2)); // 2 online, 2 offline

      // Offline Fleet = 2 (all technicians where isOnline == false)
      expect(find.text('Offline Fleet'), findsOneWidget);

      // Active Bookings = 0
      expect(find.text('Active Bookings'), findsOneWidget);
      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('Renders empty state when 0 active jobs exist and no job is auto-selected', (tester) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      // Only historical / completed jobs in dataset
      final historicalJobs = [
        Job(
          id: 9001,
          requestId: 'COMPLETED-1',
          serviceTitle: 'AC Repair',
          status: 'completed',
          totalAmount: 500.0,
          paymentMethod: 'ONLINE',
          paymentStatus: 'completed',
          createdAt: DateTime.now(),
          isOffer: false,
          isAcceptedByCurrentEmployee: false,
          isAssignedToCurrentEmployee: true,
          canCancel: false,
        ),
        Job(
          id: 9002,
          requestId: 'CANCELLED-1',
          serviceTitle: 'Plumbing',
          status: 'cancelled',
          totalAmount: 300.0,
          paymentMethod: 'COD',
          paymentStatus: 'pending',
          createdAt: DateTime.now(),
          isOffer: false,
          isAcceptedByCurrentEmployee: false,
          isAssignedToCurrentEmployee: false,
          canCancel: false,
        ),
      ];

      final testDashboardData = AdminDashboardData(
        fleet: const [],
        jobs: historicalJobs,
      );

      await tester.pumpWidget(
        buildTestWidget(
          const AdminDispatchScreen(),
          overrides: [
            adminDashboardDataProvider.overrideWith((ref) => Future.value(testDashboardData)),
            adminFleetListProvider.overrideWith((ref) => Future.value([])),
            adminPendingExtensionsProvider.overrideWith((ref) => Future.value([])),
            adminPendingServicesProvider.overrideWith((ref) => Future.value([])),
            adminLocationsProvider.overrideWith((ref) => Future.value([])),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Active Bookings metric must be 0
      expect(find.text('Active Bookings'), findsOneWidget);
      expect(find.text('0'), findsWidgets);

      // Automated Dispatch Monitor must show 0 service requests and empty state
      expect(find.text('1. Customer Service Requests (0)'), findsOneWidget);
      expect(find.text('No Active Bookings'), findsOneWidget);
      expect(find.text('No active service bookings in queue.'), findsOneWidget);

      // Section 2: Live Automated Geo-Dispatch Engine Monitor
      expect(find.text('2. Live Automated Geo-Dispatch Engine Monitor'), findsOneWidget);
      expect(find.text('Autonomous Dispatch Active'), findsOneWidget);
      expect(find.textContaining('Inspecting Job: None Selected'), findsOneWidget);
      expect(find.textContaining('20 KM Geographic Dispatch Active: Fallback search evaluates candidates across a true 20 km circular radius in all 360° directions using authoritative geodesic Haversine calculation and 9-Gate qualification.'), findsOneWidget);

      // Distance Rings
      expect(find.text('Distance Rings:'), findsOneWidget);
      expect(find.text('All 20km (0)'), findsOneWidget);
      expect(find.text('0–1 km'), findsOneWidget);
      expect(find.text('1–2 km'), findsOneWidget);
      expect(find.text('2–5 km'), findsOneWidget);
      expect(find.text('5–10 km'), findsOneWidget);
      expect(find.text('10–15 km'), findsOneWidget);
      expect(find.text('15–20 km'), findsOneWidget);

      // Empty State for candidates
      expect(find.text('No qualified technicians currently found within the 20 km operational radius for this service request.'), findsOneWidget);

      // Completed jobs must NOT appear in the dispatch monitor
      expect(find.text('COMPLETED-1'), findsNothing);
      expect(find.text('CANCELLED-1'), findsNothing);
    });

    testWidgets('Renders active jobs in dispatch queue while filtering out completed jobs', (tester) async {
      tester.view.physicalSize = const Size(800, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final mixedJobs = [
        Job(
          id: 1001,
          requestId: 'ACTIVE-UNASSIGNED',
          customerName: 'John Doe',
          serviceTitle: 'Carpentry Work',
          status: 'unassigned',
          totalAmount: 850.0,
          paymentMethod: 'COD',
          paymentStatus: 'pending',
          createdAt: DateTime.now(),
          isOffer: false,
          isAcceptedByCurrentEmployee: false,
          isAssignedToCurrentEmployee: false,
          canCancel: true,
        ),
        Job(
          id: 1002,
          requestId: 'COMPLETED-HISTORICAL',
          customerName: 'Jane Doe',
          serviceTitle: 'Cleaning Work',
          status: 'completed',
          totalAmount: 1200.0,
          paymentMethod: 'ONLINE',
          paymentStatus: 'completed',
          createdAt: DateTime.now(),
          isOffer: false,
          isAcceptedByCurrentEmployee: false,
          isAssignedToCurrentEmployee: true,
          canCancel: false,
        ),
      ];

      final testDashboardData = AdminDashboardData(
        fleet: const [],
        jobs: mixedJobs,
      );

      await tester.pumpWidget(
        buildTestWidget(
          const AdminDispatchScreen(),
          overrides: [
            adminDashboardDataProvider.overrideWith((ref) => Future.value(testDashboardData)),
            adminFleetListProvider.overrideWith((ref) => Future.value([])),
            adminEligibleTechniciansProvider(1001).overrideWith((ref) => Future.value([])),
            adminPendingExtensionsProvider.overrideWith((ref) => Future.value([])),
            adminPendingServicesProvider.overrideWith((ref) => Future.value([])),
            adminLocationsProvider.overrideWith((ref) => Future.value([])),
          ],
        ),
      );
      await tester.pumpAndSettle();

      // Only 1 active booking
      expect(find.text('1. Customer Service Requests (1)'), findsOneWidget);
      expect(find.text('ACTIVE-UNASSIGNED'), findsOneWidget);
      expect(find.text('COMPLETED-HISTORICAL'), findsNothing);
      expect(find.textContaining('Inspecting Job: ACTIVE-UNASSIGNED'), findsOneWidget);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/jobs/domain/job.dart';
import 'package:mobile/features/jobs/presentation/job_detail_screen.dart';
import 'package:mobile/features/jobs/presentation/jobs_providers.dart';

class _FakeAuthController extends StateNotifier<AuthState> implements AuthController {
  _FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

const mockAdminUser = AuthUser(
  id: 1,
  username: 'admin_user',
  email: 'admin@caldimengg.in',
  firstName: 'Admin',
  lastName: 'User',
  role: 'admin',
  companyId: 1,
  companyName: 'Caldim Engineering',
  isSuperuser: false,
  employeeId: 'ADM-001',
  registrationStatus: 'approved',
);

void main() {
  Widget createWidgetUnderTest({
    required Job job,
  }) {
    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith((ref) => _FakeAuthController(mockAdminUser)),
        activeJobsProvider.overrideWith((ref) async => [job]),
        completedJobsProvider.overrideWith((ref) async => []),
      ],
      child: MaterialApp(
        theme: ThemeData.light(),
        home: JobDetailScreen(jobId: job.id),
      ),
    );
  }

  group('JobDetailScreen - Dynamic Assigned Technician Display', () {
    testWidgets('renders Assigned Technician section with Gokul details', (tester) async {
      final job = Job(
        id: 201,
        requestId: 'SR-201',
        customerName: 'Thejjaa',
        serviceCategory: 'Electrical',
        serviceTitle: 'Main Power Distribution Box Installation',
        status: 'assigned',
        address: '05 Bagalur Rd, KCC Nagar, Hosur',
        technicianName: 'Gokul',
        technicianPhone: '9876543210',
        technicianEmail: 'gokul.m@caldimengg.in',
        technicianId: 42,
        isOffer: false,
        isAcceptedByCurrentEmployee: false,
        isAssignedToCurrentEmployee: false,
        canCancel: false,
      );

      await tester.pumpWidget(createWidgetUnderTest(job: job));
      await tester.pumpAndSettle();

      // Assert "Assigned Technician" card title
      expect(find.text('Assigned Technician'), findsOneWidget);
      // Assert technician name dynamically rendered
      expect(find.text('Gokul'), findsOneWidget);
      // Assert technician phone
      expect(find.text('9876543210'), findsOneWidget);
      // Assert technician email
      expect(find.text('gokul.m@caldimengg.in'), findsOneWidget);
    });

    testWidgets('renders dynamic technician details for other technicians', (tester) async {
      final job = Job(
        id: 202,
        requestId: 'SR-202',
        customerName: 'John Doe',
        serviceCategory: 'HVAC',
        serviceTitle: 'AC Coil Replacement',
        status: 'in_progress',
        address: '100 Outer Ring Road, Bangalore',
        technicianName: 'Priya Kumar',
        technicianPhone: '9123456780',
        technicianEmail: 'priya.k@example.com',
        technicianId: 88,
        isOffer: false,
        isAcceptedByCurrentEmployee: true,
        isAssignedToCurrentEmployee: true,
        canCancel: false,
      );

      await tester.pumpWidget(createWidgetUnderTest(job: job));
      await tester.pumpAndSettle();

      // Assert dynamic technician details
      expect(find.text('Assigned Technician'), findsOneWidget);
      expect(find.text('Priya Kumar'), findsOneWidget);
      expect(find.text('9123456780'), findsOneWidget);
      expect(find.text('priya.k@example.com'), findsOneWidget);
      // Gokul should NOT be present
      expect(find.text('Gokul'), findsNothing);
    });

    testWidgets('does not render Assigned Technician section when unassigned', (tester) async {
      final job = Job(
        id: 203,
        requestId: 'SR-203',
        customerName: 'Sarah Jenkins',
        serviceCategory: 'Plumbing',
        serviceTitle: 'Pipe Leakage Repair',
        status: 'unassigned',
        address: '42 MG Road, Bangalore',
        technicianName: null,
        technicianPhone: null,
        technicianEmail: null,
        isOffer: false,
        isAcceptedByCurrentEmployee: false,
        isAssignedToCurrentEmployee: false,
        canCancel: true,
      );

      await tester.pumpWidget(createWidgetUnderTest(job: job));
      await tester.pumpAndSettle();

      // Assert "Assigned Technician" card title is not rendered
      expect(find.text('Assigned Technician'), findsNothing);
      expect(find.text('Gokul'), findsNothing);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/superadmin/applications/data/superadmin_applications_repository.dart';
import 'package:mobile/features/superadmin/applications/domain/platform_application.dart';
import 'package:mobile/features/superadmin/applications/presentation/superadmin_applications_providers.dart';
import 'package:mobile/features/superadmin/applications/presentation/superadmin_applications_screen.dart';
import 'package:mobile/features/superadmin/applications/presentation/widgets/application_card.dart';
import 'package:mobile/features/superadmin/applications/presentation/widgets/application_detail_sheet.dart';
import 'package:mobile/features/superadmin/applications/presentation/widgets/application_metrics.dart';
import 'package:mobile/features/superadmin/applications/presentation/widgets/profile_change_request_card.dart';

class FakeAuthController extends StateNotifier<AuthState>
    implements AuthController {
  FakeAuthController(AuthUser user) : super(AuthState.authenticated(user));

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeSuperAdminApplicationsRepository
    implements SuperAdminApplicationsRepository {
  FakeSuperAdminApplicationsRepository({
    required this.applications,
    this.changeRequests = const [],
  });

  List<AdminApplication> applications;
  List<AdminChangeRequest> changeRequests;

  int approveCalls = 0;
  int rejectCalls = 0;
  int correctionCalls = 0;
  String? lastRejectionReason;
  String? lastCorrectionNotes;

  int decideChangeRequestCalls = 0;
  int? lastDecidedCrId;
  String? lastDecideAction;
  String? lastDecideNotes;

  @override
  Future<List<AdminApplication>> fetchApplications({String? statusFilter}) async {
    return applications;
  }

  @override
  Future<AdminApplication> fetchApplicationDetail(int id) async {
    return applications.firstWhere((a) => a.id == id);
  }

  @override
  Future<Map<String, dynamic>> approveApplication(int id) async {
    approveCalls++;
    return {'message': 'Technician approved for platform onboarding.'};
  }

  @override
  Future<Map<String, dynamic>> rejectApplication(int id, {required String reason}) async {
    rejectCalls++;
    lastRejectionReason = reason;
    return {'message': 'Candidate application rejected.'};
  }

  @override
  Future<Map<String, dynamic>> requestCorrection(int id, {required String notes}) async {
    correctionCalls++;
    lastCorrectionNotes = notes;
    return {'message': 'Correction request sent.'};
  }

  @override
  Future<List<AdminChangeRequest>> fetchChangeRequests() async {
    return changeRequests;
  }

  int decideServiceCalls = 0;
  int? lastDecidedServiceId;
  String? lastDecidedServiceAction;

  int bulkDecideServicesCalls = 0;
  String? lastBulkServiceAction;

  int verifyDocCalls = 0;
  String? lastVerifiedDocCategory;
  String? lastVerifiedDocAction;

  int bulkVerifyDocsCalls = 0;
  String? lastBulkDocAction;

  @override
  Future<Map<String, dynamic>> decideService({
    required int employeeId,
    required int serviceId,
    required String action,
    String reason = '',
  }) async {
    decideServiceCalls++;
    lastDecidedServiceId = serviceId;
    lastDecidedServiceAction = action;
    return {'message': 'Service authorization decided successfully.'};
  }

  @override
  Future<Map<String, dynamic>> bulkDecideServices({
    required int applicationId,
    required List<int> serviceIds,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    bulkDecideServicesCalls++;
    lastBulkServiceAction = action;
    return {'message': 'Bulk services decided successfully.', 'updated_count': 2};
  }

  @override
  Future<Map<String, dynamic>> verifyDocument({
    required int applicationId,
    required String docCategory,
    required String action,
    String reason = '',
  }) async {
    verifyDocCalls++;
    lastVerifiedDocCategory = docCategory;
    lastVerifiedDocAction = action;
    return {'message': 'Document verified successfully.'};
  }

  @override
  Future<Map<String, dynamic>> bulkVerifyDocuments({
    required int applicationId,
    required List<String> categories,
    required String action,
    String reason = '',
    bool allPending = false,
  }) async {
    bulkVerifyDocsCalls++;
    lastBulkDocAction = action;
    return {'message': 'Bulk documents verified successfully.', 'updated_count': 2};
  }

  @override
  Future<Map<String, dynamic>> decideChangeRequest({
    required int crId,
    required String action,
    String notes = '',
  }) async {
    decideChangeRequestCalls++;
    lastDecidedCrId = crId;
    lastDecideAction = action;
    lastDecideNotes = notes;
    return {'message': 'Change request decided successfully.'};
  }

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
    AdminApplication(
      id: 101,
      employeeId: 'EMP-1001',
      name: 'Ramesh Kumar',
      firstName: 'Ramesh',
      lastName: 'Kumar',
      email: 'ramesh@example.com',
      phone: '9876543210',
      registrationStatus: 'submitted',
      companyId: 10,
      companyName: 'Apex Services',
      createdAt: DateTime(2026, 9, 1),
      allRequestedServices: const [
        AdminServiceItem(id: 1, name: 'AC Repair', category: 'HVAC', status: 'pending'),
        AdminServiceItem(id: 2, name: 'Electrical Wiring', category: 'Electrical', status: 'approved'),
      ],
      documentsList: const [
        AdminDocumentItem(category: 'aadhaar_card', title: 'Aadhaar Card', status: 'approved', fileUrl: 'https://example.com/aadhaar.pdf'),
        AdminDocumentItem(category: 'trade_cert', title: 'HVAC License', status: 'approved', fileUrl: 'https://example.com/hvac.pdf'),
      ],
    ),
    AdminApplication(
      id: 102,
      employeeId: 'EMP-1002',
      name: 'Suresh Raina',
      firstName: 'Suresh',
      lastName: 'Raina',
      email: 'suresh@example.com',
      phone: '9876543211',
      registrationStatus: 'under_review',
      companyId: 12,
      companyName: 'Pioneer Works',
      createdAt: DateTime(2026, 9, 2),
      allRequestedServices: const [
        AdminServiceItem(id: 3, name: 'Plumbing', category: 'Plumbing', status: 'pending'),
      ],
      documentsList: const [
        AdminDocumentItem(category: 'driver_license', title: 'Driving License', status: 'approved'),
      ],
    ),
    AdminApplication(
      id: 103,
      employeeId: 'EMP-1003',
      name: 'Dinesh Karthik',
      firstName: 'Dinesh',
      lastName: 'Karthik',
      email: 'dinesh@example.com',
      phone: '9876543212',
      registrationStatus: 'approved',
      companyId: 10,
      companyName: 'Apex Services',
      createdAt: DateTime(2026, 8, 28),
      allRequestedServices: const [
        AdminServiceItem(id: 4, name: 'Carpentry', category: 'Woodwork', status: 'approved'),
      ],
      documentsList: const [
        AdminDocumentItem(category: 'id_proof', title: 'Passport', status: 'approved'),
      ],
    ),
    AdminApplication(
      id: 104,
      employeeId: 'EMP-1004',
      name: 'Manikandan Sundaram',
      firstName: 'Manikandan',
      lastName: 'Sundaram',
      email: 'mani@example.com',
      phone: '9876543213',
      registrationStatus: 'correction_required',
      companyId: null,
      createdAt: DateTime(2026, 8, 25),
      onboardingData: const {
        'correction_notes': 'Please re-upload clear Aadhaar photos.',
      },
    ),
    AdminApplication(
      id: 105,
      employeeId: 'EMP-1005',
      name: 'Kavitha Nathan',
      firstName: 'Kavitha',
      lastName: 'Nathan',
      email: 'kavitha@example.com',
      phone: '9876543214',
      registrationStatus: 'rejected',
      companyId: null,
      createdAt: DateTime(2026, 8, 20),
      onboardingData: const {
        'rejection_reason': 'Failed police verification.',
      },
    ),
  ];

  final mockChangeRequests = [
    AdminChangeRequest(
      id: 201,
      employeeId: 'EMP-1001',
      employeeName: 'Ramesh Kumar',
      fieldName: 'first_name',
      fieldLabel: 'Legal First Name',
      oldValue: 'Ramesh',
      newValue: 'Rameshkumar',
      reason: 'Passport correction',
      status: 'pending',
      requestedAt: DateTime(2026, 9, 3),
    ),
    AdminChangeRequest(
      id: 202,
      employeeId: 'EMP-1002',
      employeeName: 'Suresh Raina',
      fieldName: 'phone',
      fieldLabel: 'Mobile Number',
      oldValue: '9876543211',
      newValue: '9123456780',
      reason: 'Updated SIM card',
      status: 'pending',
      requestedAt: DateTime(2026, 9, 4),
    ),
    AdminChangeRequest(
      id: 203,
      employeeId: 'EMP-1003',
      employeeName: 'Dinesh Karthik',
      fieldName: 'date_of_birth',
      fieldLabel: 'Date of Birth',
      oldValue: '1990-01-01',
      newValue: '1989-12-31',
      reason: 'Birth certificate adjustment',
      status: 'approved',
      requestedAt: DateTime(2026, 8, 30),
      decidedAt: DateTime(2026, 9, 1),
      adminNotes: 'Verified against certificate',
    ),
  ];

  Widget createTestWidget({
    List<AdminApplication>? applications,
    List<AdminChangeRequest>? changeRequests,
    FakeSuperAdminApplicationsRepository? customRepo,
    String? initialStatusFilter,
  }) {
    final repo = customRepo ??
        FakeSuperAdminApplicationsRepository(
          applications: applications ?? mockApplications,
          changeRequests: changeRequests ?? mockChangeRequests,
        );

    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(
          (ref) => FakeAuthController(mockSuperAdminUser),
        ),
        superAdminSelectedSectionProvider.overrideWith(
          (ref) => SuperAdminApplicationsSection.onboardingApplications,
        ),
        applicationStatusFilterProvider.overrideWith(
          (ref) => PlatformApplicationStatusFilter.all,
        ),
        applicationSearchQueryProvider.overrideWith((ref) => ''),
        superAdminApplicationsRepositoryProvider.overrideWithValue(repo),
        superAdminApplicationsListProvider.overrideWith(
          (ref) async => repo.fetchApplications(),
        ),
        superAdminChangeRequestsListProvider.overrideWith(
          (ref) async => repo.fetchChangeRequests(),
        ),
      ],
      child: MaterialApp(
        home: SuperAdminApplicationsScreen(
          initialStatusFilter: initialStatusFilter,
        ),
      ),
    );
  }

  group('SuperAdminApplicationsScreen Widget Tests', () {
    testWidgets('1. Screen title, header badge, and subtitle render correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('PLATFORM GOVERNANCE'), findsOneWidget);
      expect(find.text('Applications Approval'), findsOneWidget);
      expect(
        find.text(
          'SEVO Platform Admin: Review technician onboarding applications, verify submitted documents, and manage approval decisions across the platform.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('2. Top-level section tabs render with dynamic counts', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Onboarding Applications (5)'), findsOneWidget);
      expect(find.text('🔒 Profile Change Requests (2 Pending)'), findsOneWidget);
    });

    testWidgets('3. Sidebar drawer opens and shows Applications Approval as active', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final drawerIcon = find.byIcon(Icons.menu_rounded);
      expect(drawerIcon, findsOneWidget);
      await tester.tap(drawerIcon);
      await tester.pumpAndSettle();

      expect(find.text('Applications Approval'), findsWidgets);
    });

    testWidgets('4. Switching tabs displays Profile Change Requests and back', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Initially on Onboarding Applications
      expect(find.byType(ApplicationMetrics), findsOneWidget);
      expect(find.byType(ProfileChangeRequestCard), findsNothing);

      // Tap Profile Change Requests tab
      final pcrTab = find.text('🔒 Profile Change Requests (2 Pending)');
      expect(pcrTab, findsOneWidget);
      await tester.tap(pcrTab);
      await tester.pumpAndSettle();

      // Verify Profile Change Requests section is visible
      expect(find.byType(ApplicationMetrics), findsNothing);
      expect(find.byType(ProfileChangeRequestCard), findsNWidgets(3));
      expect(find.text('REQUEST #201'), findsOneWidget);
      expect(find.text('REQUEST #202'), findsOneWidget);
      expect(find.text('REQUEST #203'), findsOneWidget);

      // Switch back to Onboarding Applications
      final onboardingTab = find.text('Onboarding Applications (5)');
      await tester.tap(onboardingTab);
      await tester.pumpAndSettle();

      expect(find.byType(ApplicationMetrics), findsOneWidget);
      expect(find.byType(ProfileChangeRequestCard), findsNothing);
    });

    testWidgets('5. Application metrics render with live data counts', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(ApplicationMetrics), findsOneWidget);
      expect(find.text('Pending Applications'), findsOneWidget);
      expect(find.text('Under Review'), findsWidgets);
      expect(find.text('Approved'), findsWidgets);
      expect(find.text('Corrections Required'), findsWidgets);
      expect(find.text('Rejected'), findsWidgets);
    });

    testWidgets('6. Application list renders real provider data cards', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 2000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(ApplicationCard), findsNWidgets(5));
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Raina'), findsOneWidget);
      expect(find.text('Dinesh Karthik'), findsOneWidget);
      expect(find.text('Manikandan Sundaram'), findsOneWidget);
      expect(find.text('Kavitha Nathan'), findsOneWidget);
      expect(find.text('View Application'), findsNWidgets(5));
    });

    testWidgets('7. Search filtering filters list by name, employeeId, and phone', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final searchField = find.byType(TextField);
      expect(searchField, findsOneWidget);

      await tester.enterText(searchField, 'Ramesh');
      await tester.pumpAndSettle();

      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Raina'), findsNothing);

      final clearBtn = find.byIcon(Icons.clear_rounded);
      expect(clearBtn, findsOneWidget);
      await tester.tap(clearBtn);
      await tester.pumpAndSettle();

      expect(find.text('Suresh Raina'), findsOneWidget);
    });

    testWidgets('8. Status filtering switches visible applications', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final pendingChip = find.widgetWithText(Material, 'Pending').first;
      await tester.tap(pendingChip);
      await tester.pumpAndSettle();

      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Suresh Raina'), findsNothing);
      expect(find.text('Dinesh Karthik'), findsNothing);

      final approvedChip = find.widgetWithText(Material, 'Approved').first;
      await tester.tap(approvedChip);
      await tester.pumpAndSettle();

      expect(find.text('Dinesh Karthik'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsNothing);
    });

    testWidgets('9. Tapping View Application opens ApplicationDetailSheet', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final viewBtn = find.text('View Application').first;
      await tester.tap(viewBtn);
      await tester.pumpAndSettle();

      expect(find.byType(ApplicationDetailSheet), findsOneWidget);
      expect(find.text('PERSONAL INFORMATION'), findsOneWidget);
      expect(find.text('ADDRESS & SERVICE TERRITORY'), findsOneWidget);
      expect(find.text('PROFESSIONAL INFORMATION'), findsOneWidget);
      expect(find.text('REQUESTED SERVICES (2)'), findsOneWidget);
      expect(find.text('SUBMITTED DOCUMENTS (2)'), findsOneWidget);
      expect(find.text('Approve Application'), findsOneWidget);
    });

    testWidgets('10. Approve application flow shows confirmation dialog and calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final readyApp = AdminApplication(
        id: 101,
        name: 'Ramesh Kumar',
        registrationStatus: 'under_review',
        allRequestedServices: const [
          AdminServiceItem(id: 1, name: 'AC Repair & Service', status: 'approved'),
        ],
        documentsList: const [
          AdminDocumentItem(category: 'aadhaar_front', title: 'Aadhaar Card', status: 'approved'),
        ],
      );

      final repo = FakeSuperAdminApplicationsRepository(
        applications: [readyApp],
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo, applications: [readyApp]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final approveBtn = find.text('Approve Application');
      expect(approveBtn, findsOneWidget);
      await tester.tap(approveBtn);
      await tester.pumpAndSettle();

      expect(find.text('Approve Application?'), findsOneWidget);
      expect(
        find.text('This technician (Ramesh Kumar) will be approved for platform onboarding.'),
        findsOneWidget,
      );

      final confirmApproveBtn = find.widgetWithText(FilledButton, 'Approve');
      await tester.tap(confirmApproveBtn);
      await tester.pumpAndSettle();

      expect(repo.approveCalls, 1);
    });

    testWidgets('11. Reject application flow shows reason dialog and calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final rejectBtn = find.text('Reject');
      expect(rejectBtn, findsOneWidget);
      await tester.tap(rejectBtn);
      await tester.pumpAndSettle();

      expect(find.text('Reject Application'), findsOneWidget);
      expect(find.text('Reason for rejection *'), findsOneWidget);

      final reasonInput = find.byType(TextFormField);
      await tester.enterText(reasonInput, 'Ineligible trade certification');
      await tester.pumpAndSettle();

      final submitReject = find.widgetWithText(FilledButton, 'Reject');
      await tester.tap(submitReject);
      await tester.pumpAndSettle();

      expect(repo.rejectCalls, 1);
      expect(repo.lastRejectionReason, 'Ineligible trade certification');
    });

    testWidgets('12. Request correction flow shows notes dialog and calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final correctionBtn = find.text('Corrections');
      expect(correctionBtn, findsOneWidget);
      await tester.tap(correctionBtn);
      await tester.pumpAndSettle();

      expect(find.text('Request Corrections'), findsOneWidget);
      expect(find.text('Correction Notes *'), findsOneWidget);

      final notesInput = find.byType(TextFormField);
      await tester.enterText(notesInput, 'Please re-upload clear government ID photo.');
      await tester.pumpAndSettle();

      final sendRequestBtn = find.widgetWithText(FilledButton, 'Send Request');
      await tester.tap(sendRequestBtn);
      await tester.pumpAndSettle();

      expect(repo.correctionCalls, 1);
      expect(repo.lastCorrectionNotes, 'Please re-upload clear government ID photo.');
    });

    testWidgets('13. Profile change requests render fields and reason correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Switch to Profile Change Requests
      await tester.tap(find.text('🔒 Profile Change Requests (2 Pending)'));
      await tester.pumpAndSettle();

      expect(find.text('Legal First Name'), findsOneWidget);
      expect(find.text('Ramesh Kumar (EMP-1001)'), findsOneWidget);
      expect(find.text('Passport correction'), findsOneWidget);
      expect(find.text('Review / Decide'), findsNWidgets(2));
    });

    testWidgets('14. Profile change request approve decision calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      // Switch to Profile Change Requests
      await tester.tap(find.text('🔒 Profile Change Requests (2 Pending)'));
      await tester.pumpAndSettle();

      // Tap Review / Decide on first CR
      await tester.tap(find.text('Review / Decide').first);
      await tester.pumpAndSettle();

      expect(find.text('Review: Legal First Name'), findsOneWidget);
      expect(find.text('Current Value: '), findsOneWidget);
      expect(find.text('Requested Value: '), findsOneWidget);

      // Enter optional admin notes
      final notesField = find.widgetWithText(TextField, '');
      if (notesField.evaluate().isNotEmpty) {
        await tester.enterText(notesField.first, 'Passport verified.');
      }

      // Tap Approve
      final approveBtn = find.widgetWithText(FilledButton, 'Approve');
      await tester.tap(approveBtn);
      await tester.pumpAndSettle();

      expect(repo.decideChangeRequestCalls, 1);
      expect(repo.lastDecidedCrId, 201);
      expect(repo.lastDecideAction, 'APPROVE');
    });

    testWidgets('15. Profile change request reject decision calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      // Switch to Profile Change Requests
      await tester.tap(find.text('🔒 Profile Change Requests (2 Pending)'));
      await tester.pumpAndSettle();

      // Tap Review / Decide on second CR
      await tester.tap(find.text('Review / Decide').at(1));
      await tester.pumpAndSettle();

      expect(find.text('Review: Mobile Number'), findsOneWidget);

      // Tap Reject
      final rejectBtn = find.widgetWithText(OutlinedButton, 'Reject');
      await tester.tap(rejectBtn);
      await tester.pumpAndSettle();

      expect(repo.decideChangeRequestCalls, 1);
      expect(repo.lastDecidedCrId, 202);
      expect(repo.lastDecideAction, 'REJECT');
    });

    testWidgets('16. Profile change requests empty state renders correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget(changeRequests: const []));
      await tester.pumpAndSettle();

      // Check tab badge says 0 Pending
      expect(find.text('🔒 Profile Change Requests (0 Pending)'), findsOneWidget);

      // Switch to Profile Change Requests
      await tester.tap(find.text('🔒 Profile Change Requests (0 Pending)'));
      await tester.pumpAndSettle();

      expect(
        find.text('No employee profile change requests pending review.'),
        findsOneWidget,
      );
    });

    testWidgets('17. Empty state renders when no onboarding applications exist', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget(applications: const []));
      await tester.pumpAndSettle();

      expect(find.text('Onboarding Applications (0)'), findsOneWidget);
      expect(find.text('No applications registered'), findsOneWidget);
      expect(find.text('No technician applications have been registered on the platform.'), findsOneWidget);
    });

    testWidgets('18. Error state renders with Retry button on failure', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => FakeAuthController(mockSuperAdminUser),
            ),
            superAdminApplicationsListProvider.overrideWith(
              (ref) => Future.error(Exception('Connection timed out')),
            ),
            superAdminChangeRequestsListProvider.overrideWith(
              (ref) async => const [],
            ),
          ],
          child: const MaterialApp(
            home: SuperAdminApplicationsScreen(),
          ),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('Unable to load technician applications'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('19. Initial status filter parameter initializes filter correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget(initialStatusFilter: 'correction_required'));
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('Manikandan Sundaram'), findsOneWidget);
      expect(find.text('Ramesh Kumar'), findsNothing);
      expect(find.text('Suresh Raina'), findsNothing);
    });

    testWidgets('20. Responsive layout renders cleanly at 320px, 360px, 390px, 412px without overflow',
        (tester) async {
      final screenWidths = [320.0, 360.0, 390.0, 412.0];

      for (final width in screenWidths) {
        tester.view.physicalSize = Size(width * 3, 1400 * 3);
        tester.view.devicePixelRatio = 3.0;

        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Applications Approval'), findsOneWidget);
        expect(find.text('Onboarding Applications (5)'), findsOneWidget);
        expect(find.text('🔒 Profile Change Requests (2 Pending)'), findsOneWidget);
        expect(find.byType(ApplicationMetrics), findsOneWidget);
        expect(find.byType(ApplicationCard), findsWidgets);

        // Switch to Profile Change Requests tab on this screen width
        await tester.tap(find.text('🔒 Profile Change Requests (2 Pending)'));
        await tester.pumpAndSettle();

        expect(find.byType(ProfileChangeRequestCard), findsWidgets);

        // Switch back
        await tester.tap(find.text('Onboarding Applications (5)'));
        await tester.pumpAndSettle();

        addTearDown(() => tester.view.resetPhysicalSize());
      }
    });

    testWidgets('21. Approving individual service from application detail sheet calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      expect(find.text('Approve Service'), findsOneWidget);
      await tester.tap(find.text('Approve Service'));
      await tester.pumpAndSettle();

      expect(repo.decideServiceCalls, 1);
      expect(repo.lastDecidedServiceId, 1);
      expect(repo.lastDecidedServiceAction, 'approve');
    });

    testWidgets('22. Bulk approving services from application detail sheet calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final repo = FakeSuperAdminApplicationsRepository(
        applications: mockApplications,
        changeRequests: mockChangeRequests,
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final bulkApproveBtn = find.text('Approve All (1)');
      expect(bulkApproveBtn, findsOneWidget);
      await tester.tap(bulkApproveBtn);
      await tester.pumpAndSettle();

      expect(repo.bulkDecideServicesCalls, 1);
      expect(repo.lastBulkServiceAction, 'approve');
    });

    testWidgets('23. Approving individual document from application detail sheet calls backend', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final appWithPendingDoc = AdminApplication(
        id: 201,
        name: 'Kiran Patel',
        registrationStatus: 'submitted',
        allRequestedServices: const [
          AdminServiceItem(id: 10, name: 'Carpentry', status: 'approved'),
        ],
        documentsList: const [
          AdminDocumentItem(category: 'aadhaar_card', title: 'Aadhaar Card', status: 'pending'),
        ],
      );

      final repo = FakeSuperAdminApplicationsRepository(
        applications: [appWithPendingDoc],
        changeRequests: const [],
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo, applications: [appWithPendingDoc]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final approveDocBtn = find.widgetWithText(FilledButton, 'Approve Doc');
      expect(approveDocBtn, findsOneWidget);
      await tester.tap(approveDocBtn);
      await tester.pumpAndSettle();

      expect(repo.verifyDocCalls, 1);
      expect(repo.lastVerifiedDocCategory, 'aadhaar_card');
      expect(repo.lastVerifiedDocAction, 'approve');
    });

    testWidgets('24. Quick approve all prerequisites button triggers bulk operations', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final appWithPendingItems = AdminApplication(
        id: 202,
        name: 'Vijay Kumar',
        registrationStatus: 'submitted',
        allRequestedServices: const [
          AdminServiceItem(id: 11, name: 'Plumbing', status: 'pending'),
        ],
        documentsList: const [
          AdminDocumentItem(category: 'pan_card', title: 'PAN Card', status: 'pending'),
        ],
      );

      final repo = FakeSuperAdminApplicationsRepository(
        applications: [appWithPendingItems],
        changeRequests: const [],
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo, applications: [appWithPendingItems]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final quickApproveBtn = find.text('Quick Approve All Prerequisites');
      expect(quickApproveBtn, findsOneWidget);
      await tester.tap(quickApproveBtn);
      await tester.pumpAndSettle();

      expect(repo.bulkVerifyDocsCalls, 1);
      expect(repo.bulkDecideServicesCalls, 1);
    });

    testWidgets('25. Missing prerequisite warning shows when attempting to approve without prerequisites', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1400 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final appMissingService = AdminApplication(
        id: 203,
        name: 'Anil Roy',
        registrationStatus: 'submitted',
        allRequestedServices: const [
          AdminServiceItem(id: 12, name: 'Electrician', status: 'pending'),
        ],
        documentsList: const [
          AdminDocumentItem(category: 'aadhaar_card', title: 'Aadhaar Card', status: 'approved'),
        ],
      );

      final repo = FakeSuperAdminApplicationsRepository(
        applications: [appMissingService],
        changeRequests: const [],
      );
      await tester.pumpWidget(createTestWidget(customRepo: repo, applications: [appMissingService]));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Application').first);
      await tester.pumpAndSettle();

      final approveBtn = find.text('Approve Application');
      await tester.tap(approveBtn);
      await tester.pumpAndSettle();

      expect(find.text('Prerequisites Required'), findsOneWidget);
      expect(find.text('Approve Prerequisites First'), findsOneWidget);

      await tester.tap(find.text('Approve Prerequisites First'));
      await tester.pumpAndSettle();

      expect(repo.bulkDecideServicesCalls, 1);
    });
  });
}

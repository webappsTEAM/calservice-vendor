import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/profile/domain/employee_profile.dart';
import 'package:mobile/features/profile/presentation/profile_providers.dart';
import 'package:mobile/features/profile/presentation/profile_screen.dart';
import 'package:mobile/shared/widgets/workforce_avatar.dart';

void main() {
  group('ProfileScreen Widget Tests', () {
    final testProfile = EmployeeProfile(
      employeeId: 'ORG--0024',
      firstName: 'Mani',
      lastName: 'S',
      email: 'mani@gmail.com',
      mobileNumber: '1234597890',
      phone: '1234597890',
      bio: 'Certified Air Conditioning Specialist',
      timezone: 'Asia/Kolkata',
      language: 'en',
      avatar: null,
      title: 'Technician Candidate',
      companyName: 'CalServices',
      department: 'Field Services',
      state: 'Tamil Nadu',
      country: 'India',
      dateOfBirth: '1992-05-15',
      isOnline: true,
      liveAvailability: 'online',
      registrationStatus: 'approved',
      approvedServices: const [],
      allRequestedServices: const [],
      documents: const [],
      controlledFields: const ControlledFieldsConfig(
        isLocked: true,
        lockedFields: ['first_name', 'last_name', 'date_of_birth', 'mobile_number', 'department', 'state'],
      ),
    );

    final testChangeRequests = [
      EmployeeChangeRequest(
        id: 26,
        fieldName: 'state',
        fieldLabel: 'State / Territory',
        oldValue: '—',
        newValue: 'TamilNadu',
        reason: 'Relocated to Chennai headquarters',
        status: 'APPROVED',
        adminNotes: null,
        createdAt: DateTime.parse('2026-08-13T10:00:00Z'),
      ),
      EmployeeChangeRequest(
        id: 27,
        fieldName: 'mobile_number',
        fieldLabel: 'Registered Mobile Number',
        oldValue: '1234597890',
        newValue: '9876543210',
        reason: 'Updated primary contact SIM',
        status: 'PENDING',
        adminNotes: null,
        createdAt: DateTime.parse('2026-08-14T12:00:00Z'),
      ),
    ];

    testWidgets('1. Renders profile hero section with avatar, name, title, status badges, and metadata', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify Header & Hero
      expect(find.text('My Profile'), findsOneWidget);
      expect(find.byType(WorkforceAvatar), findsWidgets);
      expect(find.text('Mani S'), findsOneWidget);
      expect(find.text('Technician Candidate • CalServices'), findsOneWidget);
      expect(find.text('APPROVED'), findsWidgets);
      expect(find.text('ONLINE'), findsOneWidget);
      expect(find.text('ID: ORG--0024'), findsOneWidget);
      expect(find.text('mani@gmail.com'), findsOneWidget);
      expect(find.text('1234597890'), findsWidgets);
    });

    testWidgets('2. Renders personal preferences with editable fields, helper text, timezones, and languages', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('PERSONAL PREFERENCES'), findsOneWidget);
      expect(find.text('Directly Editable'), findsOneWidget);
      expect(find.text('Contact Phone'), findsOneWidget);
      expect(find.text('Used for dispatch communications.'), findsOneWidget);
      expect(find.text('Professional Bio / Notes'), findsOneWidget);
      expect(find.text('Timezone'), findsOneWidget);
      expect(find.text('Language'), findsOneWidget);
      expect(find.text('Save Preferences'), findsOneWidget);
    });

    testWidgets('3. Renders verified identity & employment information with policy banner and read-only fields', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('VERIFIED IDENTITY & EMPLOYMENT'), findsOneWidget);
      expect(find.text('Admin Approved / Verified'), findsOneWidget);
      expect(find.text('Verified Data Governance Policy'), findsOneWidget);
      expect(
        find.text('Legal identity, date of birth, company assignment, and bank details require an Employee Change Request with Admin verification before updating.'),
        findsOneWidget,
      );

      // Verify all 6 read-only verified field labels
      expect(find.text('LEGAL FIRST NAME'), findsOneWidget);
      expect(find.text('LEGAL LAST NAME'), findsOneWidget);
      expect(find.text('DATE OF BIRTH'), findsOneWidget);
      expect(find.text('REGISTERED MOBILE'), findsOneWidget);
      expect(find.text('DEPARTMENT'), findsOneWidget);
      expect(find.text('STATE / TERRITORY'), findsOneWidget);

      // Verify values
      expect(find.text('Mani'), findsWidgets);
      expect(find.text('S'), findsWidgets);
      expect(find.text('1992-05-15'), findsOneWidget);
      expect(find.text('Field Services'), findsOneWidget);
      expect(find.text('Tamil Nadu'), findsOneWidget);

      // Verify 6 "Request Edit" buttons
      expect(find.text('Request Edit'), findsNWidgets(6));
    });

    testWidgets('4. Tapping Request Edit on a field opens bottom sheet with field and current value preloaded', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap first "Request Edit" button (Legal First Name)
      await tester.tap(find.text('Request Edit').first);
      await tester.pumpAndSettle();

      expect(find.text('Submit Profile Change Request'), findsOneWidget);
      expect(find.text('Target Controlled Field'), findsOneWidget);
      expect(find.text('Legal First Name'), findsWidgets);
      expect(find.text('Current Value: '), findsOneWidget);
      expect(find.text('Mani'), findsWidgets);
      expect(find.text('New Requested Value'), findsOneWidget);
      expect(find.text('Reason for Change & Supporting Reference'), findsOneWidget);
      expect(find.text('Submit for Admin Review'), findsOneWidget);
    });

    testWidgets('5. Renders change requests history section with request count and cards', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Scroll down to reveal Change Requests section
      await tester.drag(find.byType(ListView).first, const Offset(0, -800));
      await tester.pumpAndSettle();

      expect(find.text('Employee Change Requests History (2)'), findsOneWidget);
      expect(find.text('+ Submit New Change Request'), findsOneWidget);

      // Verify Card #26
      expect(find.text('Request #26'), findsOneWidget);
      expect(find.text('State / Territory'), findsWidgets);
      expect(find.text('TamilNadu'), findsOneWidget);
      expect(find.text('Relocated to Chennai headquarters'), findsOneWidget);
      expect(find.text('13/08/2026'), findsOneWidget);
      expect(find.text('APPROVED'), findsOneWidget);

      // Verify Card #27
      expect(find.text('Request #27'), findsOneWidget);
      expect(find.text('Registered Mobile Number'), findsWidgets);
      expect(find.text('9876543210'), findsOneWidget);
      expect(find.text('14/08/2026'), findsOneWidget);
      expect(find.text('PENDING'), findsOneWidget);
    });

    testWidgets('6. Renders empty state when change requests list is empty', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(const [])),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await tester.drag(find.byType(ListView).first, const Offset(0, -800));
      await tester.pumpAndSettle();

      expect(find.text('Employee Change Requests History (0)'), findsOneWidget);
      expect(find.text('No change requests submitted'), findsOneWidget);
      expect(find.text('All controlled records match your verified registration dossier.'), findsOneWidget);
    });

    testWidgets('7. Responsive Layout: Renders cleanly on small 320px screen width without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320 * 2.0, 640 * 2.0);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: const MaterialApp(
            home: ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('My Profile'), findsOneWidget);
      expect(find.text('Mani S'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await tester.drag(find.byType(ListView).first, const Offset(0, -500));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    testWidgets('8. Responsive Layout: Works with 1.5x font scale without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(360 * 2.0, 740 * 2.0);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            employeeProfileProvider.overrideWith((ref) => Future.value(testProfile)),
            changeRequestsProvider.overrideWith((ref) => Future.value(testChangeRequests)),
          ],
          child: MaterialApp(
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context).copyWith(textScaler: const TextScaler.linear(1.5)),
              child: child!,
            ),
            home: const ProfileScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('My Profile'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/admin/domain/admin_application.dart';
import 'package:mobile/features/admin/presentation/admin_dashboard_providers.dart';
import 'package:mobile/features/admin/presentation/employees/admin_employees_screen.dart';
import 'package:mobile/features/notifications/presentation/notifications_providers.dart';

void main() {
  final mockTechs = [
    const AdminApplication(
      id: 1,
      employeeId: 'TECH-001',
      name: 'Suresh Kumar',
      email: 'suresh@caldim.in',
      phone: '+91 98765 43210',
      registrationStatus: 'approved',
      isActive: true,
      isOnline: true,
      liveAvailability: 'online',
    ),
    const AdminApplication(
      id: 2,
      employeeId: 'TECH-002',
      name: 'Ramesh Patel',
      email: 'ramesh@caldim.in',
      phone: '+91 98765 43211',
      registrationStatus: 'approved',
      isActive: true,
      isOnline: false,
      liveAvailability: 'offline',
    ),
    const AdminApplication(
      id: 3,
      employeeId: 'TECH-003',
      name: 'Priya Sharma',
      email: 'priya@caldim.in',
      phone: '+91 98765 43212',
      registrationStatus: 'submitted',
      isActive: false,
      isOnline: false,
      liveAvailability: 'offline',
    ),
    const AdminApplication(
      id: 4,
      employeeId: 'TECH-004',
      name: 'Vikram Singh',
      email: 'vikram@caldim.in',
      phone: '+91 98765 43213',
      registrationStatus: 'approved',
      isActive: true,
      isOnline: true,
      liveAvailability: 'busy',
    ),
    const AdminApplication(
      id: 5,
      employeeId: 'TECH-005',
      name: 'Anita Roy',
      email: 'anita@caldim.in',
      phone: '+91 98765 43214',
      registrationStatus: 'correction_required',
      isActive: false,
      isOnline: false,
      liveAvailability: 'offline',
    ),
    const AdminApplication(
      id: 6,
      employeeId: 'TECH-006',
      name: 'Manoj Gupta',
      email: 'manoj@caldim.in',
      phone: '+91 98765 43215',
      registrationStatus: 'rejected',
      isActive: false,
      isOnline: false,
      liveAvailability: 'offline',
    ),
    const AdminApplication(
      id: 7,
      employeeId: 'TECH-007',
      name: 'Deepak Joshi',
      email: 'deepak@caldim.in',
      phone: '+91 98765 43216',
      registrationStatus: 'not_started',
      isActive: false,
      isOnline: false,
      liveAvailability: 'offline',
    ),
  ];

  Future<void> pumpScreen(
    WidgetTester tester, {
    List<AdminApplication>? techs,
    double width = 390,
    double height = 2400,
    double textScale = 1.0,
  }) async {
    tester.view.physicalSize = Size(width, height);
    tester.view.devicePixelRatio = 1.0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          adminApplicationsListProvider(null).overrideWith((ref) => Future.value(techs ?? mockTechs)),
          unreadNotificationsCountProvider.overrideWithValue(0),
        ],
        child: MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(
              size: Size(width, height),
              textScaler: TextScaler.linear(textScale),
            ),
            child: const AdminEmployeesScreen(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> selectStatus(WidgetTester tester, String itemText) async {
    await tester.tap(find.byKey(const Key('admin_status_filter_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(DropdownMenuItem<String>, itemText).last);
    await tester.pumpAndSettle();
  }

  Future<void> selectPresence(WidgetTester tester, String itemText) async {
    await tester.tap(find.byKey(const Key('admin_presence_filter_dropdown')));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(DropdownMenuItem<String>, itemText).last);
    await tester.pumpAndSettle();
  }

  group('Admin Employees Screen Filter Dropdowns Tests', () {
    testWidgets('1. Renders default All Status and All Presence dropdowns with full employee roster', (tester) async {
      await pumpScreen(tester);

      expect(find.text('Workforce Employee Roster'), findsOneWidget);
      expect(find.byKey(const Key('admin_status_filter_dropdown')), findsOneWidget);
      expect(find.byKey(const Key('admin_presence_filter_dropdown')), findsOneWidget);

      // Verify all employees are rendered initially
      expect(find.text('Suresh Kumar'), findsOneWidget);
      expect(find.text('Ramesh Patel'), findsOneWidget);
      expect(find.text('Priya Sharma'), findsOneWidget);
      expect(find.text('Vikram Singh'), findsOneWidget);
      expect(find.text('Anita Roy'), findsOneWidget);
      expect(find.text('Manoj Gupta'), findsOneWidget);
      expect(find.text('Deepak Joshi'), findsOneWidget);
    });

    testWidgets('2. Status Dropdown: Filters Active employees', (tester) async {
      await pumpScreen(tester);

      await selectStatus(tester, 'Active');

      // Approved/active techs
      expect(find.text('Suresh Kumar'), findsOneWidget);
      expect(find.text('Ramesh Patel'), findsOneWidget);
      expect(find.text('Vikram Singh'), findsOneWidget);

      // Non-active techs should NOT be shown
      expect(find.text('Priya Sharma'), findsNothing);
      expect(find.text('Anita Roy'), findsNothing);
      expect(find.text('Manoj Gupta'), findsNothing);
      expect(find.text('Deepak Joshi'), findsNothing);
    });

    testWidgets('3. Status Dropdown: Filters Pending employees', (tester) async {
      await pumpScreen(tester);

      await selectStatus(tester, 'Pending');

      expect(find.text('Priya Sharma'), findsOneWidget);
      expect(find.text('Suresh Kumar'), findsNothing);
      expect(find.text('Ramesh Patel'), findsNothing);
      expect(find.text('Deepak Joshi'), findsNothing);
    });

    testWidgets('4. Status Dropdown: Filters Inactive, Correction Required, and Rejected employees', (tester) async {
      await pumpScreen(tester);

      // Inactive
      await selectStatus(tester, 'Inactive');
      expect(find.text('Deepak Joshi'), findsOneWidget);
      expect(find.text('Suresh Kumar'), findsNothing);

      // Correction Required
      await selectStatus(tester, 'Correction Required');
      expect(find.text('Anita Roy'), findsOneWidget);
      expect(find.text('Deepak Joshi'), findsNothing);

      // Rejected
      await selectStatus(tester, 'Rejected');
      expect(find.text('Manoj Gupta'), findsOneWidget);
      expect(find.text('Anita Roy'), findsNothing);
    });

    testWidgets('5. Presence Dropdown: Filters Online, Offline, and Busy employees', (tester) async {
      await pumpScreen(tester);

      // Filter Online
      await selectPresence(tester, 'Online');
      expect(find.text('Suresh Kumar'), findsOneWidget);
      expect(find.text('Ramesh Patel'), findsNothing);
      expect(find.text('Vikram Singh'), findsNothing); // Busy

      // Filter Offline
      await selectPresence(tester, 'Offline');
      expect(find.text('Ramesh Patel'), findsOneWidget);
      expect(find.text('Priya Sharma'), findsOneWidget);
      expect(find.text('Suresh Kumar'), findsNothing);

      // Filter Busy
      await selectPresence(tester, 'Busy (On Job)');
      expect(find.text('Vikram Singh'), findsOneWidget);
      expect(find.text('Suresh Kumar'), findsNothing);
      expect(find.text('Ramesh Patel'), findsNothing);
    });

    testWidgets('6. Combined Filtering: Search + Status + Presence work seamlessly together', (tester) async {
      await pumpScreen(tester);

      // Select Status -> Active
      await selectStatus(tester, 'Active');

      // Select Presence -> Online
      await selectPresence(tester, 'Online');

      // Active & Online -> Suresh Kumar
      expect(find.text('Suresh Kumar'), findsOneWidget);
      expect(find.text('Ramesh Patel'), findsNothing);

      // Add Search term matching Suresh
      await tester.enterText(find.byType(TextField), 'suresh');
      await tester.pumpAndSettle();
      expect(find.text('Suresh Kumar'), findsOneWidget);

      // Add Search term NOT matching Suresh
      await tester.enterText(find.byType(TextField), 'nonexistent');
      await tester.pumpAndSettle();
      expect(find.text('Suresh Kumar'), findsNothing);
      expect(find.text('No Technicians Found'), findsOneWidget);

      // Clear search
      await tester.tap(find.byIcon(Icons.clear_rounded));
      await tester.pumpAndSettle();
      expect(find.text('Suresh Kumar'), findsOneWidget);

      // Reset dropdowns to ALL
      await selectStatus(tester, 'All Status');
      await selectPresence(tester, 'All Presence');

      expect(find.text('Suresh Kumar'), findsOneWidget);
      expect(find.text('Ramesh Patel'), findsOneWidget);
      expect(find.text('Priya Sharma'), findsOneWidget);
      expect(find.text('Vikram Singh'), findsOneWidget);
    });

    testWidgets('7. Responsive layout: Zero overflow on small screens (320px) and large font scale (1.5x)', (tester) async {
      // 320px width (Compact stacked layout)
      await pumpScreen(tester, width: 320);
      expect(tester.takeException(), isNull);
      expect(find.byKey(const Key('admin_status_filter_dropdown')), findsOneWidget);
      expect(find.byKey(const Key('admin_presence_filter_dropdown')), findsOneWidget);

      // 360px width (Side-by-side row)
      await pumpScreen(tester, width: 360);
      expect(tester.takeException(), isNull);

      // 480px width
      await pumpScreen(tester, width: 480);
      expect(tester.takeException(), isNull);

      // 1.5x font scale on 320px width
      await pumpScreen(tester, width: 320, textScale: 1.5);
      expect(tester.takeException(), isNull);
    });
  });
}

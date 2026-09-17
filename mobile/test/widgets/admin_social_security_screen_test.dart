import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_social_security_registration.dart';
import 'package:mobile/features/admin/presentation/social_security/admin_social_security_providers.dart';
import 'package:mobile/features/admin/presentation/social_security/admin_social_security_screen.dart';

void main() {
  final sampleRegistrations = [
    AdminSocialSecurityRegistration(
      registrationId: 1,
      employeeId: 101,
      employeeName: 'Ramesh Kumar',
      daysWorkedCurrentFy: 94,
      status: 'REGISTERED',
      registeredAt: DateTime(2026, 8, 15),
      registeredBy: 'Admin User',
      portalReferenceId: 'SS-2026-004921',
    ),
    const AdminSocialSecurityRegistration(
      registrationId: 2,
      employeeId: 102,
      employeeName: 'Karthik S',
      daysWorkedCurrentFy: 91,
      status: 'ELIGIBLE_PENDING',
    ),
    const AdminSocialSecurityRegistration(
      registrationId: 3,
      employeeId: 103,
      employeeName: 'Deepak V',
      daysWorkedCurrentFy: 45,
      status: 'NOT_YET_ELIGIBLE',
    ),
  ];

  Widget buildTestWidget({
    List<AdminSocialSecurityRegistration>? registrations,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null)
          adminSocialSecurityListProvider
              .overrideWith((ref) => Future.error(error))
        else
          adminSocialSecurityListProvider.overrideWith(
              (ref) => Future.value(registrations ?? sampleRegistrations)),
      ],
      child: const MaterialApp(
        home: AdminSocialSecurityScreen(),
      ),
    );
  }

  group('AdminSocialSecurityScreen Widget Tests', () {
    testWidgets('renders header, banner, count, filter chips, and cards', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Header
      expect(find.text('Social Security'), findsOneWidget);
      expect(
        find.text(
          'Compliance tracking under the Code on Social Security, 2020.',
        ),
        findsOneWidget,
      );
      expect(find.text('Refresh'), findsOneWidget);

      // Information Banner
      expect(
        find.textContaining(
          'Individual workers only -- SEVO is the "aggregator" under the Code on Social Security, 2020',
        ),
        findsOneWidget,
      );
      expect(
        find.textContaining(
          'This page tracks eligibility (90+ days worked this financial year)',
        ),
        findsOneWidget,
      );

      // Count & Filter chips
      expect(
        find.text('Social Security Code Registrations (3)'),
        findsOneWidget,
      );
      expect(find.text('All statuses'), findsOneWidget);
      expect(find.text('Not Yet Eligible'), findsWidgets);
      expect(find.text('Eligible — Pending'), findsWidgets);
      expect(find.text('Registered'), findsWidgets);

      // Cards
      expect(find.text('Ramesh Kumar'), findsOneWidget);
      expect(find.text('Worker ID: #101 · Reg #1'), findsOneWidget);
      expect(find.text('94 / 90 days'), findsOneWidget);
      expect(
        find.text('Portal Reference: SS-2026-004921'),
        findsOneWidget,
      );

      expect(find.text('Karthik S'), findsOneWidget);
      expect(find.text('91 / 90 days'), findsOneWidget);
      expect(find.text('Mark as Registered'), findsOneWidget);

      expect(find.text('Deepak V'), findsOneWidget);
      expect(find.text('45 / 90 days'), findsOneWidget);
    });

    testWidgets('tapping record portal submission opens dialog', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('Mark as Registered'),
        100,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Mark as Registered'));
      await tester.pumpAndSettle();

      expect(
        find.text('Record Portal Submission for Karthik S'),
        findsOneWidget,
      );
      expect(find.text('Portal Reference ID'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Record Submission'), findsOneWidget);
    });

    testWidgets('shows exact empty state when no registrations match', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget(registrations: []));
      await tester.pumpAndSettle();

      expect(
        find.text('Social Security Code Registrations (0)'),
        findsOneWidget,
      );
      expect(
        find.text('No individual worker registrations to show.'),
        findsOneWidget,
      );
    });

    testWidgets('shows error state with retry on failure', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        buildTestWidget(error: Exception('Social security API error')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load registrations'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Admin Social Security Responsive Layout Tests', () {
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

        expect(find.text('Social Security'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

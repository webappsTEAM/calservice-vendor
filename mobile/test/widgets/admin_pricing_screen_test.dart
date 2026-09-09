import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/features/admin/domain/admin_pricing_policy.dart';
import 'package:mobile/features/admin/presentation/pricing/admin_pricing_providers.dart';
import 'package:mobile/features/admin/presentation/pricing/admin_pricing_screen.dart';

void main() {
  final samplePolicies = [
    const AdminPricingPolicy(
      id: 1,
      serviceCategory: 'AC Services',
      displayName: 'AC Services',
      consultationFeeMode: 'FLAT',
      consultationFeeModeDisplay: 'Flat fee',
      consultationFeeAmount: 249.0,
      freeRadiusKm: 15.0,
      beyondRadiusAmount: 300.0,
      highValueReviewThreshold: 5000.0,
      requiresAdminApproval: true,
      advancePercent: 100.0,
      allowCustomerSuppliedMaterials: false,
      isActive: true,
    ),
    const AdminPricingPolicy(
      id: 2,
      serviceCategory: 'mason',
      displayName: 'Masonry & Civil',
      consultationFeeMode: 'DISTANCE_BAND',
      consultationFeeModeDisplay: 'Free within radius, fee beyond',
      consultationFeeAmount: 0.0,
      freeRadiusKm: 15.0,
      beyondRadiusAmount: 300.0,
      highValueReviewThreshold: 10000.0,
      requiresAdminApproval: true,
      advancePercent: 50.0,
      allowCustomerSuppliedMaterials: false,
      isActive: true,
    ),
  ];

  Widget buildTestWidget({
    List<AdminPricingPolicy>? policies,
    Object? error,
  }) {
    return ProviderScope(
      overrides: [
        if (error != null)
          adminPricingPoliciesProvider
              .overrideWith((ref) => Future.error(error))
        else
          adminPricingPoliciesProvider
              .overrideWith((ref) => Future.value(policies ?? samplePolicies)),
      ],
      child: const MaterialApp(
        home: AdminPricingApprovalsScreen(),
      ),
    );
  }

  group('AdminPricingApprovalsScreen Widget Tests', () {
    testWidgets('renders screen header, description, refresh, and category cards', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Screen Header
      expect(find.text('Pricing & Approval Rules'), findsOneWidget);
      expect(
        find.text(
          'Applies to new quotations and bookings. Invoices already issued keep the figures they were issued with.',
        ),
        findsOneWidget,
      );
      expect(find.text('Refresh'), findsOneWidget);

      // Reusable policy cards
      expect(find.text('AC Services'), findsWidgets);
      expect(find.text('Masonry & Civil'), findsOneWidget);
      expect(find.text('Policy active'), findsNWidgets(2));

      // Card Fields
      expect(find.text('Consultation Fee'), findsNWidgets(2));
      expect(find.text('Flat fee'), findsOneWidget);
      expect(find.text('Free within radius, fee beyond'), findsOneWidget);
      expect(
        find.text('SEVO approves accepted quotes before work is scheduled'),
        findsNWidgets(2),
      );
      expect(
        find.text('Allow customer-supplied materials'),
        findsNWidgets(2),
      );
      expect(find.text('Save'), findsNWidgets(2));
    });

    testWidgets('shows empty state when no pricing policies exist', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(buildTestWidget(policies: []));
      await tester.pumpAndSettle();

      expect(find.text('No pricing policies found.'), findsOneWidget);
      expect(
        find.text('No service category pricing policies configured.'),
        findsOneWidget,
      );
    });

    testWidgets('shows error state with retry on failure', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        buildTestWidget(error: Exception('Failed to connect to pricing service')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Unable to load pricing policies'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
    });
  });

  group('Admin Pricing Screen Responsive Layout Tests', () {
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

        expect(find.text('Pricing & Approval Rules'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}

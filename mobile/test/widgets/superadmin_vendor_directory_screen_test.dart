import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/domain/auth_user.dart';
import 'package:mobile/features/auth/presentation/auth_controller.dart';
import 'package:mobile/features/superadmin/vendors/domain/platform_vendor.dart';
import 'package:mobile/features/superadmin/vendors/presentation/superadmin_vendor_directory_screen.dart';
import 'package:mobile/features/superadmin/vendors/presentation/superadmin_vendor_providers.dart';
import 'package:mobile/features/superadmin/vendors/presentation/widgets/vendor_card.dart';
import 'package:mobile/features/superadmin/vendors/presentation/widgets/vendor_directory_metrics.dart';

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

  final mockVendors = [
    PlatformVendor(
      id: 12,
      companyName: 'Apex Engineering Ltd',
      slug: 'apex-eng',
      city: 'Bangalore',
      address: '100 Industrial Area',
      ownerName: 'John Doe',
      ownerEmail: 'john@apex.com',
      ownerPhone: '9876543210',
      tiedWorkersCount: 1,
      pendingInvitationsCount: 2,
      createdAt: DateTime(2026, 1, 1),
    ),
    PlatformVendor(
      id: 15,
      companyName: 'Pioneer Works',
      slug: 'pioneer-chennai',
      city: 'Chennai',
      address: '25 GST Road',
      ownerName: 'Priya Sharma',
      ownerEmail: 'priya@pioneer.com',
      ownerPhone: '9876543215',
      tiedWorkersCount: 4,
      pendingInvitationsCount: 0,
      createdAt: DateTime(2026, 2, 1),
    ),
  ];

  Widget createTestWidget({
    List<PlatformVendor>? vendors,
    AsyncValue<PlatformVendorsResponse>? customAsync,
  }) {
    final defaultResponse = PlatformVendorsResponse(
      vendors: vendors ?? mockVendors,
      totalCount: (vendors ?? mockVendors).length,
    );

    return ProviderScope(
      overrides: [
        authControllerProvider.overrideWith(
          (ref) => FakeAuthController(mockSuperAdminUser),
        ),
        if (customAsync != null)
          platformVendorsDataProvider.overrideWith((ref) => customAsync.value!)
        else
          platformVendorsDataProvider.overrideWith((ref) async => defaultResponse),
      ],
      child: const MaterialApp(
        home: SuperAdminVendorDirectoryScreen(),
      ),
    );
  }

  group('SuperAdminVendorDirectoryScreen Widget Tests', () {
    testWidgets('renders screen header, title, and subtitle correctly', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Platform Governance context pill
      expect(find.text('PLATFORM GOVERNANCE'), findsOneWidget);

      // Title & Subtitle
      expect(find.text('Vendor Companies Management'), findsOneWidget);
      expect(
        find.text(
          'SEVO Platform Admin: Complete oversight of service vendor organizations and their tied workforce.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('renders overview metrics and primary workforce action', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Manage All Workforce button
      expect(find.text('Manage All Workforce (Solo & Tied)'), findsOneWidget);

      // Metrics
      expect(find.text('REGISTERED VENDORS'), findsOneWidget);
      expect(find.text('2'), findsOneWidget); // 2 registered vendors

      expect(find.text('TOTAL TIED WORKFORCE'), findsOneWidget);
      expect(find.text('5'), findsOneWidget); // 1 + 4 = 5 tied workers

      // Platform operations banner
      expect(find.text('PLATFORM OPERATIONS'), findsOneWidget);
      expect(find.text('Multi-Tenant Architecture Active'), findsOneWidget);
      expect(find.text('LIVE'), findsOneWidget);
    });

    testWidgets('renders vendor cards with complete business, contact, location & metrics',
        (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Vendor 1
      expect(find.text('Apex Engineering Ltd'), findsOneWidget);
      expect(find.text('ID: #12 • apex-eng'), findsOneWidget);
      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('john@apex.com'), findsOneWidget);
      expect(find.text('9876543210'), findsOneWidget);
      expect(find.text('Bangalore'), findsOneWidget);
      expect(find.text('1 active'), findsOneWidget);
      expect(find.text('2 invites'), findsOneWidget);

      // Vendor 2
      expect(find.text('Pioneer Works'), findsOneWidget);
      expect(find.text('ID: #15 • pioneer-chennai'), findsOneWidget);
      expect(find.text('Priya Sharma'), findsOneWidget);
      expect(find.text('priya@pioneer.com'), findsOneWidget);
      expect(find.text('Chennai'), findsOneWidget);
      expect(find.text('4 active'), findsOneWidget);

      // Action Buttons
      expect(find.text('View Workers'), findsNWidgets(2));
    });

    testWidgets('search functionality filters vendor cards dynamically', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1200 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      // Initial count
      expect(find.text('Showing 2 of 2 vendors'), findsOneWidget);

      // Search by vendor name
      final searchInput = find.byType(TextField);
      await tester.enterText(searchInput, 'Apex');
      await tester.pumpAndSettle();

      expect(find.text('Showing 1 of 2 vendors'), findsOneWidget);
      expect(find.text('Apex Engineering Ltd'), findsOneWidget);
      expect(find.text('Pioneer Works'), findsNothing);

      // Search by owner email
      await tester.enterText(searchInput, 'priya@pioneer.com');
      await tester.pumpAndSettle();

      expect(find.text('Showing 1 of 2 vendors'), findsOneWidget);
      expect(find.text('Pioneer Works'), findsOneWidget);
      expect(find.text('Apex Engineering Ltd'), findsNothing);

      // Search by city
      await tester.enterText(searchInput, 'Bangalore');
      await tester.pumpAndSettle();

      expect(find.text('Showing 1 of 2 vendors'), findsOneWidget);
      expect(find.text('Apex Engineering Ltd'), findsOneWidget);

      // Clear search
      final clearBtn = find.byIcon(Icons.clear_rounded);
      expect(clearBtn, findsOneWidget);
      await tester.tap(clearBtn);
      await tester.pumpAndSettle();

      expect(find.text('Showing 2 of 2 vendors'), findsOneWidget);
      expect(find.text('Apex Engineering Ltd'), findsOneWidget);
      expect(find.text('Pioneer Works'), findsOneWidget);
    });

    testWidgets('renders empty search state when no vendors match search query', (tester) async {
      tester.view.physicalSize = const Size(400 * 3, 1000 * 3);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(createTestWidget());
      await tester.pumpAndSettle();

      final searchInput = find.byType(TextField);
      await tester.enterText(searchInput, 'NonExistentVendorNameXYZ');
      await tester.pumpAndSettle();

      expect(find.text('Showing 0 of 2 vendors'), findsOneWidget);
      expect(find.text('No vendor businesses found'), findsOneWidget);
      expect(find.text('No vendors match your search criteria.'), findsOneWidget);
    });

    testWidgets('renders empty registered state when no vendors exist on platform',
        (tester) async {
      await tester.pumpWidget(createTestWidget(vendors: []));
      await tester.pumpAndSettle();

      expect(find.text('Showing 0 of 0 vendors'), findsOneWidget);
      expect(find.text('No Vendors Registered'), findsOneWidget);
      expect(
        find.text(
          'No service vendor organizations have registered on the platform yet.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('renders error state with retry button on failure', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith(
              (ref) => FakeAuthController(mockSuperAdminUser),
            ),
            platformVendorsDataProvider.overrideWith(
              (ref) => Future.error(Exception('Server unreachable')),
            ),
          ],
          child: const MaterialApp(
            home: SuperAdminVendorDirectoryScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Unable to load platform vendor businesses'),
        findsOneWidget,
      );
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('responsive layout renders cleanly without overflow on various mobile screen widths',
        (tester) async {
      final screenWidths = [320.0, 360.0, 390.0, 412.0];

      for (final width in screenWidths) {
        tester.view.physicalSize = Size(width * 3, 1200 * 3);
        tester.view.devicePixelRatio = 3.0;

        await tester.pumpWidget(createTestWidget());
        await tester.pumpAndSettle();

        expect(find.text('Vendor Companies Management'), findsOneWidget);
        expect(find.byType(VendorDirectoryMetricsCards), findsOneWidget);
        expect(find.byType(VendorCard), findsWidgets);

        addTearDown(() => tester.view.resetPhysicalSize());
      }
    });
  });
}
